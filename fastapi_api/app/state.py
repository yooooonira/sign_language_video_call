from typing import Set
from fastapi import WebSocket

class Hub: #허브 
    def __init__(self) -> None:
        self.clients: Set[WebSocket] = set()

    async def add(self, ws: WebSocket) -> None: # 접속자 등록 
        self.clients.add(ws)

    def remove(self, ws: WebSocket) -> None: # 접속자 제거 
        self.clients.discard(ws)
hub = Hub()