from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .state import hub  #허브에 등록용 
import asyncio, json, logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ai") # 클라이언트는 ws://localhost:8000/ai 로 연결. ai붙으면 허브로 들어감
async def websocket_endpoint(  # 프런트에서 값가져오기
    websocket: WebSocket,
    role: str =  Query(...),
    room: str = Query(default="")
):
    await websocket.accept() # 클라이언트의 WebSocket 연결 요청을 수락
    await hub.add(websocket, role=role, room=room) # 허브에 등록
    logger.info("연결됨 role=%s room=%s", role, room or "(없음)")   #★

    try:
        while True:
            message = await websocket.receive_text()   # 프런트에서 보낸 원본 문자열
            logger.info("프런트에서 수신(raw): %s", message[:200])

            try:
                data = json.loads(message)
            except Exception:
                # JSON 아니면 같은 방 브로드캐스트(기존 동작 유지)
                logger.info("JSON 파싱 실패 -> 같은 방 브로드캐스트")
                room_id = hub.room_of(websocket)
                for client in list(hub.in_room(room_id)):
                    if client is not websocket:
                        await client.send_text(message)
                continue

            mtype = data.get("type")
            room_id = data.get("room_id") or hub.room_of(websocket)

            # 1) 프런트 -> AI 워커 : 좌표 전달
            if mtype == "hand_landmarks": #{ "type": "hand_landmarks", "room_id": "<roomId>", "landmarks": [ [ { "x": number, "y": number }, ... ], ... ], "timestamp": <number> }
                try:
                    from app import main  # 순환 import 방지: 런타임에 불러오기
                    lm=data.get("landmarks")
                    processed = [
                        [[pt["x"], pt["y"]] for pt in hand]
                            for hand in lm
                    ]
                    logger.info("hand_landmarks 수신, landmark=%s",lm)
                    text, score = main.predict_landmarks(processed) #추론보내기 

                    # 클라이언트에 ai_result 전달
                    result = {
                        "type": "ai_result",
                        "text": str(text),      # 추론 라벨 문자열
                        "score": float(max(score)) 
                    }
                    payload = json.dumps(result)
                    logger.info("추론 결과를 프런트로 전달")
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

            # 3) 그 외 텍스트는 같은 방 브로드캐스트(기존 동작 유지)
            payload = json.dumps(data)
            for client in list(hub.in_room(room_id)):
                if client is not websocket:
                    await client.send_text(payload)
            continue

    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
	    await hub.remove(websocket)