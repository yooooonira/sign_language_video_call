from django.urls import re_path
from consumer import CallConsumer, CallNotifyConsumer

websocket_urlpatterns = [
    # 기존 CallConsumer
    re_path(r"ws/call/(?P<room_id>\w+)/$", CallConsumer.as_asgi()),

    # 새 알림용 Consumer
    re_path(r"ws/call-notify/$", CallNotifyConsumer.as_asgi()),
]