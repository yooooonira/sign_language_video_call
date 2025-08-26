from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .state import hub
import asyncio

router = APIRouter()

@router.websocket("/ai") # 클라이언트는 ws://localhost:8000/ws 로 연결. ws붙으면 허브로 들어감 
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept() # 클라이언트의 WebSocket 연결 요청을 수락
    await hub.add(websocket) # 허브에 등록 

    try:

        while True:
            message = await websocket.receive() # 클라이언트로부터 텍스트 메시지를 기다림 (await → 비동기 처리)

            # 텍스트/좌표 
            text = message.get("text")
            if text is not None:
                # 보낸 사람 제외 브로드캐스트
                for client in list(hub.clients):
                    if client is not websocket:
                        await client.send_text(text)
                continue

            # 프레임/비디오 
            b = message.get("bytes")
            if b is not None:
                for client in list(hub.clients):
                    if client is not websocket:
                        await client.send_bytes(b)
                continue

    except (WebSocketDisconnect, asyncio.TimeoutError): 
        pass #웹소켓 닫는거 처리 
    finally:
        hub.remove(websocket)

