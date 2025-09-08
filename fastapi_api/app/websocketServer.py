# --- 파일: fastapp/app/websocketServer.py ---
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .state import hub
import asyncio, json, logging
import numpy as np  # <<< ADDED: 길이 리샘플에 사용

logger = logging.getLogger(__name__)
router = APIRouter()

# <<< ADDED: 프레임 길이를 10으로 맞추는 헬퍼 (리샘플/패딩) -----------------
def _ensure_10_frames(frames):
    """
    frames: List[Frame], Frame = 21개의 [x,y] 또는 dict{x,y} 리스트
    길이가 10이 아니면 10으로 맞춤:
      - >10: 균등 샘플링
      - <10: 마지막 프레임 반복 패딩
    """
    if not isinstance(frames, list):
        return []

    T = len(frames)
    if T == 10:
        return frames

    # 프레임을 일단 [ [ [x,y], ... 21 ] , ... ] 형태로 통일
    def _to_xy21(frame):
        if not frame:
            return [[0.0, 0.0] for _ in range(21)]
        first = frame[0]
        if isinstance(first, dict):
            return [[float(p.get("x", 0.0)), float(p.get("y", 0.0))] for p in frame][:21]
        else:
            return [[float(p[0]), float(p[1])] for p in frame][:21]

    if T > 10:
        idxs = np.linspace(0, T - 1, 10).round().astype(int).tolist()
        return [_to_xy21(frames[i]) for i in idxs]

    # T < 10 → 패딩
    base = [_to_xy21(f) for f in frames]
    last = base[-1] if base else [[0.0, 0.0] for _ in range(21)]
    base += [last] * (10 - len(base))
    return base
# ------------------------------------------------------------------------


# <<< ADDED: 다수 손 중 대표 손 1개 선택(왼쪽손/오른손 구분 없을 때) -----------
def _select_primary_hand(hands):
    """
    hands: List[Hand], Hand = 21개의 포인트 (dict{x,y} 또는 [x,y])
    간단히 '왼쪽에 있는 손(평균 x가 작은 손)'을 대표로 선택.
    """
    if not hands:
        return [[0.0, 0.0] for _ in range(21)]

    def _to_xy21(hand):
        if not hand:
            return [[0.0, 0.0] for _ in range(21)]
        first = hand[0]
        if isinstance(first, dict):
            xy = [[float(p.get("x", 0.0)), float(p.get("y", 0.0))] for p in hand]
        else:
            xy = [[float(p[0]), float(p[1])] for p in hand]
        if len(xy) < 21:
            xy += [[0.0, 0.0]] * (21 - len(xy))
        return xy[:21]

    hands_xy = [_to_xy21(h) for h in hands]
    # 평균 x가 가장 작은(화면의 왼쪽) 손을 선택
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

            # JSON 파싱 실패시: 같은 방에 그대로 브로드캐스트(기존 동작 유지)
            try:
                data = json.loads(message)
                if isinstance(data, list):
                    # 옛 포맷 호환: 리스트만 오면 단일 프레임으로 간주
                    data = {"type": "hand_landmarks", "landmarks": data}
            except Exception:
                # logger.info("JSON 파싱 실패 -> 같은 방 브로드캐스트")
                room_id = hub.room_of(websocket)
                for client in list(hub.in_room(room_id)):
                    if client is not websocket:
                        await client.send_text(message)
                continue

            mtype = data.get("type")
            room_id = data.get("room_id") or hub.room_of(websocket)

            # <<< ADDED: 좌표 수신(type=coords) ACK / 디버그 캡션 ---------------
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
            # ------------------------------------------------------------------

            # 1) 단일 프레임 처리 (여러 손이 오면 대표 손 1개만 추려서 보냄)
            if mtype == "hand_landmarks":
                try:
                    from . import main
                    lm = data.get("landmarks")  # 예상: List[Hand], Hand=List[21개의 dict{x,y} or [x,y]]
                    logger.info("hand_landmarks 수신, hands=%d", len(lm) if isinstance(lm, list) else 0)

                    # <<< CHANGED: 대표 손 1개 선택 → (21,2)
                    if isinstance(lm, list) and lm and isinstance(lm[0], (list, tuple, dict)):
                        primary = _select_primary_hand(lm)
                    else:
                        primary = [[0.0, 0.0] for _ in range(21)]

                    type_result, text, score = main.predict_landmarks(primary)

                    result = {
                        "type": str(type_result),
                        "text": str(text),
                        "confidence": float(score)  # <<< CHANGED: 키 이름을 confidence로 통일
                    }
                    #logger.info("추론 결과(단건): %s (신뢰도: %.3f)", text, score)
                    payload = json.dumps(result, ensure_ascii=False)

                    for client in list(hub.by_role_in_room("client", room_id)):
                        await client.send_text(payload)

                except Exception:
                    #logger.exception("infer_error")
                    await websocket.send_text(json.dumps({
                        "type": "ai_result",
                        "ok": False,
                        "error": "infer_error"
                    }, ensure_ascii=False))
                continue

            # 2) 시퀀스 처리 (길이 10으로 강제 맞춤)
            if mtype == "hand_landmarks_sequence":
                try:
                    from . import main
                    frame_sequence = data.get("frame_sequence")  # 예상: List[Frame], Frame=21 포인트

                    # <<< CHANGED: 길이 보정 + 각 프레임을 [ [x,y]*21 ] 로 정규화
                    frames10 = _ensure_10_frames(frame_sequence)
                    logger.info("hand_landmarks_sequence 수신, frames(raw)=%d -> frames(used)=%d",
                                len(frame_sequence) if frame_sequence else 0, len(frames10))

                    type_result, text, score = main.predict_landmarks_sequence(frames10)

                    result = {
                        "type": "subtitle",
                        "text": str(text),
                        "confidence": float(score)
                    }
                    # logger.info("시퀀스 추론 결과: %s (신뢰도: %.3f)", text, score)
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

            # 3) 연결 테스트
            if mtype == "connection_test":
                # logger.info("연결 테스트 수신: %s", data.get("message"))
                await websocket.send_text(json.dumps({
                    "type": "connection_test_response",
                    "message": "백엔드 연결 확인됨"
                }, ensure_ascii=False))
                continue

            # 4) 그 외 메시지는 브로드캐스트
            payload = json.dumps(data, ensure_ascii=False)
            for client in list(hub.in_room(room_id)):
                if client is not websocket:
                    await client.send_text(payload)

    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        await hub.remove(websocket)
