"""Settings endpoints."""

from __future__ import annotations

import asyncio
import urllib.request

from fastapi import APIRouter, Request

from nglobe.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


def _public_ip() -> str:
    # Empty ProxyHandler: go direct, not through our own system proxy
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open("https://api.ipify.org", timeout=5) as resp:
        return resp.read().decode().strip()


@router.get("/location")
async def get_location(request: Request) -> dict:
    """Where the packets start from: configured coordinates, or auto-detected from public IP."""
    state = request.app.state
    cfg = state.config.location
    if not cfg.auto_detect:
        return {"latitude": cfg.latitude, "longitude": cfg.longitude, "detected": False}
    if getattr(state, "detected_location", None) is None:
        try:
            geo = state.geo_resolver.resolve(await asyncio.to_thread(_public_ip))
            if geo.has_coordinates:
                state.detected_location = {
                    "latitude": geo.latitude, "longitude": geo.longitude,
                    "city": geo.city, "country": geo.country_name, "detected": True,
                }
        except OSError as e:
            logger.warning("location_detect_failed", error=str(e))
    return getattr(state, "detected_location", None) or {
        "latitude": cfg.latitude, "longitude": cfg.longitude, "detected": False,
    }
