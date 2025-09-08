# websocketServer.py 전체 수정
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .state import hub
import asyncio, json, logging

logger = logging.getLogger(__name__)
router = APIRouter()

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

            try:
                data = json.loads(message)
                if isinstance(data, list):
                    data = {"type": "hand_landmarks", "landmarks": data}
            except Exception:
                logger.info("JSON 파싱 실패 -> 같은 방 브로드캐스트")
                room_id = hub.room_of(websocket)
                for client in list(hub.in_room(room_id)):
                    if client is not websocket:
                        await client.send_text(message)
                continue

            mtype = data.get("type")
            room_id = data.get("room_id") or hub.room_of(websocket)

            # 1) 기존 단일 프레임 처리 (호환성 유지)
            if mtype == "hand_landmarks":
                try:
                    from . import main
                    lm = data.get("landmarks")
                    processed = [
                        [[pt["x"], pt["y"]] for pt in hand]
                        for hand in lm
                    ]
                    logger.info("hand_landmarks 수신, landmark=%s", lm)
                    type_result, text, score = main.predict_landmarks(processed)

                    result = {
                        "type": type_result,
                        "text": str(text),
                        "score": float(score)
                    }
                    logger.info("추론 결과: %s", text)
                    payload = json.dumps(result)

                    for client in list(hub.by_role_in_room("client", room_id)):
                        await client.send_text(payload)

                except Exception:
                    logger.exception("infer_error")
                    await websocket.send_text(json.dumps({
                        "type": "ai_result",
                        "ok": False,
                        "error": "infer_error"
                    }))
                continue

            # 2) 새로운 15프레임 시퀀스 처리
            if mtype == "hand_landmarks_sequence":
                try:
                    from . import main
                    frame_sequence = data.get("frame_sequence")

                    logger.info("hand_landmarks_sequence 수신, frames=%d", len(frame_sequence) if frame_sequence else 0)
                    type_result, text, score = main.predict_landmarks_sequence(frame_sequence)

                    result = {
                        "type": "subtitle",
                        "text": str(text),
                        "confidence": float(score)
                    }
                    logger.info("시퀀스 추론 결과: %s (신뢰도: %.3f)", text, score)
                    payload = json.dumps(result)

                    for client in list(hub.by_role_in_room("client", room_id)):
                        await client.send_text(payload)

                except Exception:
                    logger.exception("sequence_infer_error")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "sequence_inference_failed"
                    }))
                continue

            # 3) 연결 테스트 메시지 처리
            if mtype == "connection_test":
                logger.info("연결 테스트 수신: %s", data.get("message"))
                await websocket.send_text(json.dumps({
                    "type": "connection_test_response",
                    "message": "백엔드 연결 확인됨"
                }))
                continue

            # 4) 그 외 메시지는 브로드캐스트
            payload = json.dumps(data)
            for client in list(hub.in_room(room_id)):
                if client is not websocket:
                    await client.send_text(payload)

    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        await hub.remove(websocket)