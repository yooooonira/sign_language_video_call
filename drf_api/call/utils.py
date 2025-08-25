import json
from django.conf import settings
from pywebpush import webpush

def notify_user_via_webpush(subscription_info, caller_id, caller_name, room_id):
    payload = {
        "type": "incoming_call",
        "from_user_id": caller_id,
        "from_user_name": caller_name,
        "room_id": room_id
    }
    if isinstance(subscription_info, str):
        subscription_info = json.loads(subscription_info)

    webpush(
        subscription_info=subscription_info,
        data=json.dumps(payload),
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims={"sub": "mailto:your@email.com"}
    )
