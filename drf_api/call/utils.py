from .consumer import active_connections
import asyncio

async def notify_user(user_id: str, from_user: str, room_id: str):
    print(f"🔔 notify_user called: {user_id} <- from {from_user}, room {room_id}")

    consumer = active_connections.get(user_id)
    if consumer:
        await consumer.send_call_request(from_user, room_id)
    else:
        print(f"⚠️ User {user_id} not connected. 알람 전송 실패")