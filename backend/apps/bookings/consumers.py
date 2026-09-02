import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class OperationsConsumer(AsyncJsonWebsocketConsumer):
    GROUP_NAME = "liveops_channel"

    async def connect(self):
        await self.channel_layer.group_add(
            self.GROUP_NAME,
            self.channel_name
        )
        await self.accept()
        # Send initial connection acknowledgement
        await self.send_json({
            "type": "connection.ack",
            "message": "Connected to Instant Mechanic LiveOps real-time stream.",
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.GROUP_NAME,
            self.channel_name
        )

    async def receive_json(self, content):
        """
        Handle incoming client messages (e.g. heartbeat ping).
        """
        msg_type = content.get("type", "")
        if msg_type == "ping":
            await self.send_json({"type": "pong", "timestamp": content.get("timestamp")})

    async def broadcast_event(self, event):
        """
        Handler for messages sent to the group.
        """
        await self.send_json({
            "type": event.get("event", "update"),
            "data": event.get("data", {}),
        })
