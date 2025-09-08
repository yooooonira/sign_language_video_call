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
    logger.info("연결됨 logger role=%s room=%s", role, room or "(없음)")
    print("웹소켓 연결됨 print", role, room)
    try:
        while True:
            message = await websocket.receive() #프런트에서 받고

            if message.get("type") == "websocket.disconnect":#못받으면 break 나가기
                break

            if "text" in message and message["text"] is not None: #받은거 처리
                raw = message["text"] #원천
                logger.info("프런트에서 수신(raw): %s", raw[:200])

                # JSON이면 type 기반 라우팅
                try:
                    data = json.loads(raw)
                except Exception:
                    # JSON 아니면 같은 방 브로드캐스트(기존 동작 유지)
                    logger.info("JSON 파싱 실패 -> 같은 방 브로드캐스트")
                    room_id = hub.room_of(websocket)
                    for client in list(hub.in_room(room_id)):
                        if client is not websocket:
                            await client.send_text(raw)
                    continue

                mtype = data.get("type")
                room_id = data.get("room_id") or hub.room_of(websocket)

                # 1) 프런트 -> AI 워커 : 좌표 전달
                if mtype == "hand_landmarks":
                    try:
                        from app import main  # 순환 import 방지: 런타임에 불러오기
                        pred_idx, probs = main.predict_landmarks(data.get("data")) #추론

                        # 클라이언트에 ai_result 전달
                        result = {
                            "type": "ai_result",
                            "ok": True, #추론 상태
                            "pred_idx": pred_idx, #모델이 예측한 클래스 인덱스 (정수).
                            "probs": probs #모델 출력의 전체 확률 분포 (리스트).
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

                # 2) AI 워커 -> 프런트 : 자막 전달
                if mtype == "ai_result":
                    payload = json.dumps(data)
                    logger.info("번역을 프런트로 전달")
                    for client in list(hub.by_role_in_room("client", room_id)):
                        if client is not websocket:
                            await client.send_text(payload)
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