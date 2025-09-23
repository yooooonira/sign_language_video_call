from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .state import hub
import asyncio, json, logging
import numpy as np

logger = logging.getLogger(__name__)
router = APIRouter()

# ------------------- 공통 헬퍼: 포인트/프레임 정규화 -----------------------
def _is_point(p):
    if isinstance(p, dict):
        return ("x" in p and "y" in p)
    if isinstance(p, (list, tuple)) and len(p) >= 2:
        return isinstance(p[0], (int, float)) or isinstance(p[0], (np.floating, np.integer))
    return False

def _to_xy21(frame):
    """frame: 21개의 dict{x,y(,z)} 또는 [x,y] → [[x,y]*21]"""
    if not frame:
        return [[0.0, 0.0] for _ in range(21)]
    first = frame[0]
    if isinstance(first, dict):
        xy = [[float(p.get("x", 0.0)), float(p.get("y", 0.0))] for p in frame]
    else:
        xy = [[float(p[0]), float(p[1])] for p in frame]
    if len(xy) < 21:
        xy += [[0.0, 0.0]] * (21 - len(xy))
    return xy[:21]

def _ensure_10_frames(frames):
    """
    frames: List[Frame]; Frame = 21개의 포인트
    길이 10으로 보정:
      - >10: 균등 샘플링
      - <10: 마지막 프레임 반복
    """
    if not isinstance(frames, list):
        return [[0.0, 0.0] for _ in range(21)] * 10

    T = len(frames)
    if T == 10:
        return [_to_xy21(f) for f in frames]

    if T > 10:
        idxs = np.linspace(0, T - 1, 10).round().astype(int).tolist()
        return [_to_xy21(frames[i]) for i in idxs]

    base = [_to_xy21(f) for f in frames]
    last = base[-1] if base else [[0.0, 0.0] for _ in range(21)]
    base += [last] * (10 - len(base))
    return base

def _select_primary_hand(hands):
    """
    hands: List[Hand]; Hand = 21 포인트
    '화면 왼쪽(평균 x 작음)' 손을 대표로 선택
    """
    if not hands:
        return [[0.0, 0.0] for _ in range(21)]
    hands_xy = [_to_xy21(h) for h in hands]
    avg_x = [float(np.mean([p[0] for p in h])) for h in hands_xy]
    idx = int(np.argmin(avg_x))
    return hands_xy[idx]
# ------------------------------------------------------------------------


@router.websocket("/ai")
async def websocket_endpoint(
    websocket: WebSocket,
    role: str = Query(...),
    room: str = Query(default="")
):
    await websocket.accept()
    await hub.add(websocket, role=role, room=room)
    logger.info("연결됨 role=%s room=%s", role, room or "(없음)")

    try:
        while True:
            message = await websocket.receive_text()
            logger.info("프런트에서 수신(raw): %s", message[:200])

            # JSON 파싱 실패 → 동일 방 브로드캐스트(기존 유지)
            try:
                data = json.loads(message)
                if isinstance(data, list):
                    data = {"type": "hand_landmarks", "landmarks": data}
            except Exception:
                room_id = hub.room_of(websocket)
                for client in list(hub.in_room(room_id)):
                    if client is not websocket:
                        await client.send_text(message)
                continue

            mtype = data.get("type")
            room_id = data.get("room_id") or hub.room_of(websocket)

            # --- 좌표 수신 ACK/디버그 캡션 -----------------------------------
            if mtype == "coords":
                hands = data.get("hands", [])
                corr_id = data.get("corr_id")
                try:
                    points_count = sum(len(h) for h in hands) if isinstance(hands, list) else 0
                except Exception:
                    points_count = 0

                ack = {
                    "type": "coords_ack",
                    "corr_id": corr_id,
                    "hands": len(hands) if isinstance(hands, list) else 0,
                    "count": points_count,
                }
                await websocket.send_text(json.dumps(ack, ensure_ascii=False))

                caption = {
                    "type": "caption",
                    "text": f"좌표 수신: hands={ack['hands']}, points={ack['count']}",
                    "corr_id": corr_id
                }
                for client in list(hub.by_role_in_room("client", room_id)):
                    await client.send_text(json.dumps(caption, ensure_ascii=False))
                continue
            # ----------------------------------------------------------------

            # --- 단일 프레임 ------------------------------------------------
            if mtype == "hand_landmarks":
                try:
                    from . import main
                    lm = data.get("landmarks")

                    # lm이 "하나의 손"인지, "여러 손"인지 판별
                    primary_21x2 = None
                    if isinstance(lm, list) and lm:
                        if _is_point(lm[0]):
                            # 예: [ {x,y}, ... x21 ] 형태
                            primary_21x2 = _to_xy21(lm)
                        else:
                            # 예: [ [ {x,y}x21 ], [ {x,y}x21 ] , ... ]
                            primary_21x2 = _select_primary_hand(lm)
                    else:
                        primary_21x2 = [[0.0, 0.0] for _ in range(21)]

                    label, score = main.predict_from_single_frame(primary_21x2)

                    # 프런트가 구독하는 타입으로 통일: caption
                    result = {
                        "type": "caption",
                        "text": str(label),          # 빈 문자열이면 표시 안 함 (프런트 정책)
                        "confidence": float(score)
                    }
                    payload = json.dumps(result, ensure_ascii=False)
                    for client in list(hub.by_role_in_room("client", room_id)):
                        await client.send_text(payload)

                except Exception:
                    logger.exception("infer_error (single frame)")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "single_frame_inference_failed"
                    }, ensure_ascii=False))
                continue

            # --- 시퀀스(길이 보정) -----------------------------------------
            if mtype == "hand_landmarks_sequence":
                try:
                    from . import main
                    frame_sequence = data.get("frame_sequence")
                    frames10 = _ensure_10_frames(frame_sequence)
                    logger.info("sequence frames: raw=%d used=%d",
                                len(frame_sequence) if frame_sequence else 0, len(frames10))

                    label, score = main.predict_from_sequence(frames10)

                    result = {
                        "type": "caption",           # <-- subtitle 대신 caption으로 통일
                        "text": str(label),
                        "confidence": float(score)
                    }
                    payload = json.dumps(result, ensure_ascii=False)
                    for client in list(hub.by_role_in_room("client", room_id)):
                        await client.send_text(payload)

                except Exception:
                    logger.exception("sequence_infer_error")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "sequence_inference_failed"
                    }, ensure_ascii=False))
                continue

            # --- 연결 테스트 -----------------------------------------------
            if mtype == "connection_test":
                await websocket.send_text(json.dumps({
                    "type": "connection_test_response",
                    "message": "백엔드 연결 확인됨"
                }, ensure_ascii=False))
                continue

            # --- 그 외는 브로드캐스트 --------------------------------------
            # (추가) 자막 이벤트 타입을 caption으로 강제 통일
            if data.get("type") == "subtitle":
                data["type"] = "caption"

            payload = json.dumps(data, ensure_ascii=False)
            for client in list(hub.in_room(room_id)):
                if client is not websocket:
                    await client.send_text(payload)


    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        await hub.remove(websocket)
