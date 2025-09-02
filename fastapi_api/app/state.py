from typing import Set, Dict, List, Optional
from fastapi import WebSocket
import logging


logger = logging.getLogger(__name__)


class Hub: #허브 
    def __init__(self) -> None:
        self.clients: Set[WebSocket] = set()
        self.meta: Dict[WebSocket, Dict[str, Optional[str]]] = {}  # {"role": "ai|client", "room": str|None}
        self.ai_pool: Set[WebSocket] = set()  # room 없이 대기 중인 AI

    def room_of(self, ws: WebSocket) -> str:
        return self.meta.get(ws, {}).get("room") or ""

    async def add(self, ws: WebSocket, *, role: str, room: str) -> None:
        self.clients.add(ws)
        self.meta[ws] = {"role": role, "room": (room or None)}

        if role == "ai":
            if not room:
                self.ai_pool.add(ws)  #  워커 대기
                logger.info("Hub.add: AI parked in pool (pool=%d, clients=%d)", len(self.ai_pool), len(self.clients))
            else:
                logger.info("Hub.add: AI joined room=%s (pool=%d)", room, len(self.ai_pool))
        else:  # client
            if room and self.ai_pool:
                ai_ws = self.ai_pool.pop()
                self.meta[ai_ws]["room"] = room        #  서버가 워커에 room을 ‘지정’
                try:
                    await ai_ws.send_json({"type": "bind", "room": room})  #  알림(옵션)
                except Exception:
                    logger.exception("Hub.add: notify bind failed")
                logger.info("Hub.add: matched client with AI -> room=%s (pool=%d)", room, len(self.ai_pool))
            else:
                logger.info("Hub.add: client joined room=%s (no AI in pool=%d)", room or "(없음)", len(self.ai_pool))


    async def remove(self, ws: WebSocket) -> None:
        self.ai_pool.discard(ws)
        self.clients.discard(ws)
        self.meta.pop(ws, None)
        logger.info("Hub.remove")

    def in_room(self, room: str) -> List[WebSocket]:
        if not room:
            return []
        res = [ws for ws in self.clients if self.meta.get(ws, {}).get("room") == room]
        logger.debug("Hub.in_room(%s) -> %d", room, len(res))
        return res

    def by_role_in_room(self, role: str, room: str) -> List[WebSocket]:
        if not room:
            return []
        res = [ws for ws in self.clients
               if self.meta.get(ws, {}).get("room") == room and self.meta.get(ws, {}).get("role") == role]
        logger.debug("Hub.by_role_in_room(role=%s, room=%s) -> %d", role, room, len(res))
        return res

hub = Hub()
