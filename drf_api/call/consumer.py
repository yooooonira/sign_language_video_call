# call/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.user_id = self.scope["query_string"].decode().split("=")[-1]  # 예: ws://.../ws/call/1234/?user_id=1
        self.group_name = f"call_{self.room_id}"

        # 방 그룹 참가
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # 1:1이면 현재 방 인원 체크
        # (간단 구현: 그룹 내 채널 수 확인 -> 나중에 DB로 관리 가능)
        # await self.send(text_data=json.dumps({"type": "joined", "user_id": self.user_id}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")
        data["from_user"] = self.user_id  # 메시지 발신자 기록

        # 메시지 타입에 따라 다른 처리
        if msg_type in ["call_request", "offer", "answer", "ice"]:
            # 1:1이라서 상대방에게만 전달
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "signal_message",
                    "data": data,
                    "sender_channel": self.channel_name,  # 보내는 사람 제외
                }
            )
        else:
            # 알 수 없는 타입 무시
            pass

    async def signal_message(self, event):
        # 보낸 사람 제외하고 다른 사람에게만 전송
        if self.channel_name != event.get("sender_channel"):
            await self.send(text_data=json.dumps(event["data"]))
