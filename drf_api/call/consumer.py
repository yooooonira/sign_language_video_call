import json
import logging

# ignore unused import
from channels.generic.websocket import AsyncWebsocketConsumer

import time
from prometheus_client import Gauge, Histogram #현재 접속사 수, 지연시간 

logger = logging.getLogger(__name__)

# 현재 접속자 수
ws_active_connections = Gauge(
    "ws_active_connections", "Number of active WebSocket connections"
)

# 메시지 처리 지연 시간 (초)
ws_message_latency = Histogram(
    "ws_message_latency_seconds",
    "WebSocket message processing latency (seconds)",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1, 2, 5],
)


class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.user_id = self.scope["query_string"].decode().split("=")[-1]
        self.group_name = f"call_{self.room_id}"

        logger.info(f"User {self.user_id} connecting to room {self.room_id}")

        ws_active_connections.inc()  # 접속자 수 증가

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        import asyncio

        await asyncio.sleep(0.5)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user_joined_message",
                "sender_channel": self.channel_name,
                "user_id": self.user_id,
            },
        )

    async def disconnect(self, close_code):
        logger.info(f"User {self.user_id} disconnecting from room {self.room_id}")

        ws_active_connections.dec()  # 접속자 수 감소

        # 다른 사용자들에게 사용자가 나갔음을 알림
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user_left_message",
                "sender_channel": self.channel_name,
                "user_id": self.user_id,
            },
        )

        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        start = time.perf_counter()
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")
            data["from_user"] = self.user_id

            logger.info(
                f"Received {msg_type} from user {self.user_id} in room {self.room_id}"
            )

            # WebRTC signaling 메시지들
            if msg_type in ["offer", "answer", "ice"]:
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "signal_message",
                        "data": data,
                        "sender_channel": self.channel_name,
                    },
                )
            # 통화 종료
            elif msg_type == "end_call":
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "call_ended",
                        "sender_channel": self.channel_name,
                        "user_id": self.user_id,
                    },
                )
            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from user {self.user_id}")
        except Exception as e:
            logger.error(f"Error processing message from user {self.user_id}: {e}")
        finally:
            duration = time.perf_counter() - start
            ws_message_latency.observe(duration)

    async def signal_message(self, event):
        # sender 제외하고 모두에게 전달
        if self.channel_name != event.get("sender_channel"):
            await self.send(text_data=json.dumps(event["data"]))

    async def user_joined_message(self, event):
        # sender 제외하고 다른 사용자들에게 새 사용자가 들어왔다고 알림
        if self.channel_name != event.get("sender_channel"):
            await self.send(
                text_data=json.dumps(
                    {"type": "user_joined", "user_id": event.get("user_id")}
                )
            )

    async def user_left_message(self, event):
        # sender 제외하고 다른 사용자들에게 사용자가 나갔다고 알림
        if self.channel_name != event.get("sender_channel"):
            await self.send(
                text_data=json.dumps(
                    {"type": "user_left", "user_id": event.get("user_id")}
                )
            )

    async def call_ended(self, event):
        if self.channel_name != event.get("sender_channel"):
            await self.send(
                text_data=json.dumps(
                    {"type": "end_call", "user_id": event.get("user_id")}
                )
            )
