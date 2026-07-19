"""GeoIP management endpoints."""

from __future__ import annotations

import asyncio
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request

from backend.api.dependencies import get_config
from backend.config import AppConfig
from backend.geoip.download import GeoIPDownloader

router = APIRouter(prefix="/geoip", tags=["geoip"])

class DownloadRequest(BaseModel):
    account_id: str
    license_key: str

@router.post("/download")
async def download_databases(
    payload: DownloadRequest, 
    request: Request,
    config: AppConfig = Depends(get_config)
) -> dict:
    """Download MaxMind GeoLite2 databases using the provided license key."""
    if not payload.license_key or not payload.license_key.strip():
        raise HTTPException(status_code=400, detail="License key is required")
        
    try:
        downloader = GeoIPDownloader(payload.account_id.strip(), payload.license_key.strip())
        
        # Run in threadpool since the download is synchronous
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(None, downloader.download_all)
        
        if success:
            # Tell orchestrator to reload geoip if possible
            orchestrator = getattr(request.app.state, "orchestrator", None)
            if orchestrator and orchestrator._geo_resolver:
                orchestrator._geo_resolver.open()
                orchestrator.startup_status["geoip_loaded"] = orchestrator._geo_resolver.is_available
                
            return {"success": True}
        else:
            raise HTTPException(status_code=500, detail="Download failed. Verify your license key.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
