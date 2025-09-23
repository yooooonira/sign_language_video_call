"""
ASGI config for drf_api project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from call import routing as call_routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "drf_api.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter(call_routing.websocket_urlpatterns),
    }
)
