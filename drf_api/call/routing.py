from django.urls import re_path
from . import consumer

websocket_urlpatterns = [
    # 기존 CallConsumer
    re_path(r"ws/call/(?P<room_id>\w+)/$", consumer.CallConsumer.as_asgi()),

    # 새 알림용 Consumer
    re_path(r"ws/call-notify/$", consumer.CallNotifyConsumer.as_asgi()),
]