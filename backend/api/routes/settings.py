"""Settings endpoints for configuration management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.api.dependencies import get_config
from backend.config import AppConfig

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(config: AppConfig = Depends(get_config)) -> dict:
    """Get current application settings (read-only subset safe for frontend)."""
    return {
        "theme": config.theme.model_dump(),
        "animations": config.animations.model_dump(),
        "performance": {
            "frontend_ring_buffer_size": config.performance.frontend_ring_buffer_size,
        },
        "location": config.location.model_dump(),
        "proxy": {
            "listen_port": config.proxy.listen_port,
        },
    }


@router.get("/location")
async def get_location(config: AppConfig = Depends(get_config)) -> dict:
    """Get user location settings."""
    return config.location.model_dump()
