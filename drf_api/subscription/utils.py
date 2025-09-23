# utils.py
import json

from django.conf import settings
from pywebpush import WebPushException, webpush


def notify_user_via_webpush(subscription_info, caller_id, room_id):
    payload = json.dumps(
        {"type": "incoming_call", "from_user": caller_id, "room_id": room_id}
    )
    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=str(settings.VAPID_PRIVATE_KEY_PATH),
            vapid_claims=settings.VAPID_CLAIMS,
        )
    except WebPushException as ex:
        print("웹푸시 전송 실패:", ex)
