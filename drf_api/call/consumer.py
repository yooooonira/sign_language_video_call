import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.user_id = self.scope["query_string"].decode().split("=")[-1]  # ws://.../ws/call/1234/?user_id=1
        self.group_name = f"call_{self.room_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")
        data["from_user"] = self.user_id

        # 기존 신호 메시지
        if msg_type in ["call_request", "offer", "answer", "ice"]:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "signal_message",
                    "data": data,
                    "sender_channel": self.channel_name,
                }
            )
        # 통화 종료
        elif msg_type == "end_call":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "call_ended",
                    "sender_channel": self.channel_name,
                }
            )
        # ✅ 수락 / 거절 처리
        elif msg_type in ["accepted", "rejected"]:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "signal_message",
                    "data": {"type": msg_type},
                    "sender_channel": self.channel_name,
                }
            )

    async def signal_message(self, event):
        # sender 제외하고 모두 전달
        if self.channel_name != event.get("sender_channel"):
            await self.send(text_data=json.dumps(event["data"]))

    async def call_ended(self, event):
        if self.channel_name != event.get("sender_channel"):
            await self.send(text_data=json.dumps({"type": "end_call"}))
