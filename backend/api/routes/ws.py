"""WebSocket endpoint for real-time event streaming."""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from backend.api.dependencies import get_ws_manager
from backend.api.websocket.manager import WebSocketManager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/events")
async def ws_events(
    websocket: WebSocket,
) -> None:
    """WebSocket endpoint for real-time network event streaming.

    Clients connect here to receive live NetworkEvent objects as they
    are captured and processed by the pipeline.
    """
    ws_manager: WebSocketManager = websocket.app.state.ws_manager
    client_id = await ws_manager.connect(websocket)

    try:
        # Keep connection alive — the send loop handles outbound messages
        while True:
            # Read client messages (heartbeats, filter updates, etc.)
            data = await websocket.receive_text()
            # Future: handle client commands (filters, pause, etc.)
    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)
