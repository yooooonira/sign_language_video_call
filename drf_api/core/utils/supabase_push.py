from typing import Any, Dict

import requests  # type: ignore
from django.conf import settings


def notify_user_via_supabase(receiver_supabase_id: str, room_id: str, caller_id: int) -> None:
    url = f"{settings.SUPABASE_URL}/realtime/v1/realtime?topic=user-{receiver_supabase_id}"
    payload: Dict[str, Any] = {
        "type": "call_request",
        "from_user": caller_id,
        "room_id": room_id,
    }
    headers: Dict[str, str] = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    requests.post(url, json=payload, headers=headers)
