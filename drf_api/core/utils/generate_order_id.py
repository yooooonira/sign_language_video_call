
import uuid
from time import time

def generate_order_id(user_id: str) -> str:
    timestamp = int(time() * 1000)  # 밀리초 단위 timestamp
    random_suffix = uuid.uuid4().hex[:6]  # 6자리 랜덤 문자열
    return f"{user_id}-{timestamp}-{random_suffix}"