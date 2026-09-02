"""
ASGI config for Instant Mechanic LiveOps project.
Exposes the ASGI callable as `application`.

WebSocket origin validation uses Channels' OriginValidator with explicit origins
configured via WEBSOCKET_ALLOWED_ORIGINS (defaulting to CORS_ALLOWED_ORIGINS in production).
In development (DEBUG=True), origins are unconstrained to facilitate local testing.
In production (DEBUG=False), wildcards are rejected and explicit trusted origins are required.
"""
import os
from django.core.asgi import get_asgi_application
from django.core.exceptions import ImproperlyConfigured
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django_asgi_app = get_asgi_application()

import core.ws_routing  # noqa: E402

ws_origins = getattr(settings, 'WEBSOCKET_ALLOWED_ORIGINS', [])

if settings.DEBUG:
    # Local development: allow all connections
    ws_router = URLRouter(core.ws_routing.websocket_urlpatterns)
else:
    # Production: require explicit non-wildcard origins
    if not ws_origins or '*' in ws_origins:
        raise ImproperlyConfigured(
            "Explicit, non-wildcard WEBSOCKET_ALLOWED_ORIGINS (or CORS_ALLOWED_ORIGINS) "
            "is required in production."
        )
    ws_router = OriginValidator(
        URLRouter(core.ws_routing.websocket_urlpatterns),
        ws_origins
    )

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": ws_router,
})
