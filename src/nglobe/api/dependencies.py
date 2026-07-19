"""FastAPI dependency injection for NetworkGlobe.

Provides access to shared services (database, WebSocket manager, etc.)
via FastAPI's Depends() system. Services are stored in app.state
and injected into route handlers.
"""

from __future__ import annotations

from fastapi import Depends, Request

from nglobe.api.websocket.manager import WebSocketManager
from nglobe.config import AppConfig
from nglobe.database.reader import QueryReader


def get_config(request: Request) -> AppConfig:
    """Inject the application configuration."""
    return request.app.state.config


def get_query_reader(request: Request) -> QueryReader:
    """Inject the database query reader."""
    return request.app.state.query_reader


def get_ws_manager(request: Request) -> WebSocketManager:
    """Inject the WebSocket manager."""
    return request.app.state.ws_manager
