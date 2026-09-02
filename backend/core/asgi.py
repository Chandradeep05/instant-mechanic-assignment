"""
ASGI config for Instant Mechanic LiveOps project.
It exposes the ASGI callable as a module-level variable named `application`.

IMPORTANT: WebSocket origin validation uses AllowedHostsOriginValidator,
which checks the Origin header against Django's ALLOWED_HOSTS setting.
This means ALLOWED_HOSTS must include your Vercel frontend domain
(e.g., "instant-mechanic-liveops.vercel.app") in addition to the backend domain.
CORS_ALLOWED_ORIGINS does NOT control WebSocket origin validation — they are separate.

Example ALLOWED_HOSTS for production:
  ALLOWED_HOSTS=13.233.44.55,api.instantmechanic.in,instant-mechanic-liveops.vercel.app
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django_asgi_app = get_asgi_application()

import core.ws_routing  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        URLRouter(
            core.ws_routing.websocket_urlpatterns
        )
    ),
})
