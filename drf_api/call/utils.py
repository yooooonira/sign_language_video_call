import json
from django.conf import settings
from pywebpush import webpush

def notify_user_via_webpush(subscription_info, caller_id, room_id):
    payload = {
        "type": "incoming_call",
        "from_user": caller_id,
        "room_id": room_id
    }
    if isinstance(subscription_info, str):
        subscription_info = json.loads(subscription_info)

    webpush(
        subscription_info=subscription_info,
        data=json.dumps(payload),
        vapid_private_key=settings.VAPID_PRIVATE_KEY_BASE64,
        vapid_claims={"sub": "mailto:your@email.com"}
    )
