from .consumer import active_connections
import asyncio

async def notify_user(user_id: str, from_user: str, room_id: str):
    if user_id in active_connections:
        consumer = active_connections[user_id]
        await consumer.send_call_request(from_user, room_id)