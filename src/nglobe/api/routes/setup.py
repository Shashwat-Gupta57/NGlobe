"""First-run setup endpoints: trust the CA certificate, download fresh GeoIP data."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from nglobe.geoip.download import GeoIPDownloader
from nglobe.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/setup", tags=["setup"])


class GeoIPSetupRequest(BaseModel):
    account_id: str
    license_key: str


@router.post("/certificate")
async def setup_certificate(request: Request) -> dict:
    """Show the Windows 'trust this certificate?' prompt; switches capture to full HTTPS detail."""
    if not await request.app.state.orchestrator.install_certificate():
        raise HTTPException(status_code=400, detail="Certificate was not installed (cancelled, or not generated yet).")
    return {"status": "success"}


@router.delete("/certificate")
async def remove_certificate(request: Request) -> dict:
    """Untrust NGlobe's certificate (Windows asks to confirm); capture continues in pass-through."""
    if not await request.app.state.orchestrator.remove_certificate():
        raise HTTPException(status_code=400, detail="Certificate was not removed (cancelled).")
    return {"status": "success"}


@router.post("/geoip")
async def setup_geoip(request: Request, payload: GeoIPSetupRequest) -> dict:
    """Download the latest MaxMind GeoLite2 databases (the app ships with a bundled copy)."""
    if not payload.account_id.strip() or not payload.license_key.strip():
        raise HTTPException(status_code=400, detail="Account ID and license key are required.")
    resolver = request.app.state.geo_resolver
    resolver.close()  # Windows can't overwrite a memory-mapped file
    try:
        ok = await asyncio.to_thread(
            GeoIPDownloader(payload.account_id.strip(), payload.license_key.strip()).download_all
        )
    finally:
        resolver.open()
    if not ok:
        raise HTTPException(status_code=400, detail="Download failed. Check your Account ID and license key.")
    return {"status": "success"}
