from django.urls import path

from . import consumer

websocket_urlpatterns = [
    path("ws/call/<str:room_id>/", consumer.CallConsumer.as_asgi()),
]
