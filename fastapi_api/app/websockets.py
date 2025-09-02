from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .state import hub  #허브에 등록용 
import asyncio, json  

import logging

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ai") # 클라이언트는 ws://localhost:8000/ai 로 연결. ai붙으면 허브로 들어감
async def websocket_endpoint(  # 프런트에서 값가져오기
    websocket: WebSocket,
    token: str | None = Query(default=None),
    role: str =  Query(...),
    room: str = Query(default="")
):
    await websocket.accept() # 클라이언트의 WebSocket 연결 요청을 수락
    await hub.add(websocket, role=role, room=room) # 허브에 등록

    try:
        while True:
            message = await websocket.receive() #프런트에서 받고 

            if message.get("type") == "websocket.disconnect":#못받으면 break 나가기
                break

            if "text" in message and message["text"] is not None: #받은거 처리 
                print(f"[hub] recv text: {message['text'][:50]}...")
                raw = message["text"] #원천 

                # JSON이면 type 기반 라우팅
                try:
                    data = json.loads(raw)
                except Exception:
                    # JSON 아니면 같은 방 브로드캐스트(기존 동작 유지)
                    room_id = hub.room_of(websocket)
                    for client in list(hub.in_room(room_id)):
                        if client is not websocket:
                            await client.send_text(raw)
                    continue

                mtype = data.get("type")
                room_id = data.get("room_id") or hub.room_of(websocket)

                # 1) 프런트 -> AI 워커 : 좌표 전달
                if mtype == "hand_landmarks":
                    payload = json.dumps(data)
                    for client in list(hub.by_role_in_room("ai", room_id)):
                        if client is not websocket:
                            await client.send_text(payload)
                    continue

                # 2) AI 워커 -> 프런트 : 자막 전달
                if mtype == "ai_result":
                    payload = json.dumps(data)
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