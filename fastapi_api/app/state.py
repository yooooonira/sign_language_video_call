from typing import Set, Dict, List
from fastapi import WebSocket

class Hub: #허브 
    def __init__(self) -> None:
        self.clients: Set[WebSocket] = set()
        self.meta: Dict[WebSocket, Dict[str, str]] = {}

    async def add(self, ws: WebSocket, *, role: str, room: str) -> None: # 접속자 등록 
        self.clients.add(ws)
        self.meta[ws] = {"role": role, "room": room}

    def remove(self, ws: WebSocket) -> None: # 접속자 제거 
        self.clients.discard(ws)
        self.meta.pop(ws, None)
    
    def in_room(self, room: str) -> List[WebSocket]:
        return [ws for ws in self.clients if self.meta.get(ws, {}).get("room") == room]

    def by_role_in_room(self, role: str, room: str) -> List[WebSocket]:
        return [ws for ws in self.in_room(room) if self.meta.get(ws, {}).get("role") == role]

hub = Hub()
