"""WebSocket manager for real-time event streaming.

Manages client connections, per-client bounded queues with backpressure,
and broadcasts NetworkEvent objects to all connected frontends.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from backend.models import NetworkEvent
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts events.

    Each client gets a dedicated asyncio.Queue with backpressure.
    If a slow client's queue fills, oldest events are dropped.
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._max_queue_size = max_queue_size
        self._start_time = time.time()
        self._total_events_broadcast = 0

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a WebSocket connection and start its send loop."""
        await websocket.accept()
        client_id = str(uuid.uuid4())[:8]

        self._connections[client_id] = websocket
        self._queues[client_id] = asyncio.Queue(maxsize=self._max_queue_size)
        self._tasks[client_id] = asyncio.create_task(
            self._send_loop(client_id), name=f"ws-send-{client_id}"
        )

        logger.info("ws_client_connected", client_id=client_id, total=len(self._connections))
        return client_id

    async def disconnect(self, client_id: str) -> None:
        """Remove a client and cancel its send loop."""
        if client_id in self._tasks:
            self._tasks[client_id].cancel()
            del self._tasks[client_id]
        self._connections.pop(client_id, None)
        self._queues.pop(client_id, None)
        logger.info("ws_client_disconnected", client_id=client_id, total=len(self._connections))

    async def broadcast(self, event: NetworkEvent) -> None:
        """Broadcast a NetworkEvent to all connected clients (EventBus subscriber)."""
        if not self._connections:
            return

        self._total_events_broadcast += 1
        message = {"type": "request", "data": event.model_dump(mode="json")}

        disconnected: list[str] = []
        for client_id, queue in self._queues.items():
            try:
                if queue.full():
                    # Backpressure: drop oldest events
                    dropped = 0
                    while not queue.empty() and dropped < 200:
                        try:
                            queue.get_nowait()
                            dropped += 1
                        except asyncio.QueueEmpty:
                            break
                    logger.warning("ws_backpressure", client_id=client_id, dropped=dropped)
                    # Send drop notification
                    try:
                        queue.put_nowait({"type": "dropped", "count": dropped})
                    except asyncio.QueueFull:
                        pass

                queue.put_nowait(message)
            except Exception:
                disconnected.append(client_id)

        for client_id in disconnected:
            await self.disconnect(client_id)

    async def broadcast_status(self, total_requests: int, requests_per_minute: int) -> None:
        """Send periodic status updates to all clients."""
        status = {
            "type": "status",
            "data": {
                "proxy_running": True,
                "total_requests": total_requests,
                "requests_per_minute": requests_per_minute,
                "active_connections": len(self._connections),
                "uptime_seconds": round(time.time() - self._start_time),
            },
        }
        for queue in self._queues.values():
            try:
                queue.put_nowait(status)
            except asyncio.QueueFull:
                pass

    async def _send_loop(self, client_id: str) -> None:
        """Per-client send loop — dequeues messages and sends via WebSocket."""
        websocket = self._connections.get(client_id)
        queue = self._queues.get(client_id)
        if not websocket or not queue:
            return

        try:
            while True:
                message = await queue.get()
                await websocket.send_json(message)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.debug("ws_send_error", client_id=client_id, error=str(e))
        finally:
            await self.disconnect(client_id)

    @property
    def active_connections(self) -> int:
        """Number of active WebSocket connections."""
        return len(self._connections)

    @property
    def total_broadcast(self) -> int:
        """Total events broadcast."""
        return self._total_events_broadcast
