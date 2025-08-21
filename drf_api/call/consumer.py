import json
from channels.generic.websocket import AsyncWebsocketConsumer


class CallConsumer(AsyncWebsocketConsumer):
    # 클라이언트 → 서버 연결
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"call_{self.room_id}"

        # 그룹에 참가
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    # 연결 끊김 처리
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # 클라이언트 → 서버 메시지
    async def receive(self, text_data):
        data = json.loads(text_data)

        # 방 전체에 broadcast
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "signal_message",
                "data": data,
            }
        )

    # 서버 → 클라이언트 메시지 (broadcast)
    async def signal_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))
