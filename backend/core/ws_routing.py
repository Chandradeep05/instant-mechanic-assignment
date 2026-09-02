"""
WebSocket URL patterns for Channels routing.
"""
from django.urls import re_path
from apps.bookings.consumers import OperationsConsumer

websocket_urlpatterns = [
    re_path(r'^ws/operations/?$', OperationsConsumer.as_asgi()),
]
