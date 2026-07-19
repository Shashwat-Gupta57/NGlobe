"""Setup endpoints for NGlobe initialization."""

from __future__ import annotations

import asyncio
from typing import Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from nglobe.startup.cert_installer import CertInstaller
from nglobe.geoip.download import GeoIPDownloader
from nglobe.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["setup"])


class GeoIPSetupRequest(BaseModel):
    account_id: str
    license_key: str


@router.post("/setup/certificate")
async def setup_certificate(request: Request) -> Dict[str, str]:
    """Trigger the Windows certificate installation UAC prompt."""
    try:
        from pathlib import Path
        config = request.app.state.config
        cert_path = Path(config.proxy.cert_dir).expanduser() / "mitmproxy-ca.pem"
        success = CertInstaller.install(cert_path)
        if success:
            logger.info("setup_certificate_success")
            
            # Update orchestrator status so the UI knows it's fixed
            orchestrator = getattr(request.app.state, "orchestrator", None)
            if orchestrator:
                orchestrator.startup_status["cert_installed"] = True
                
            return {"status": "success", "message": "Certificate installed successfully."}
        else:
            logger.error("setup_certificate_failed")
            raise HTTPException(status_code=500, detail="Certificate installation failed or was cancelled by the user.")
    except Exception as e:
        logger.exception("setup_certificate_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup/geoip")
async def setup_geoip(request: Request, payload: GeoIPSetupRequest) -> Dict[str, str]:
    """Download MaxMind GeoLite2 databases using provided credentials."""
    try:
        config = request.app.state.config
        downloader = GeoIPDownloader(payload.account_id, payload.license_key)
        
        success = await asyncio.to_thread(
            downloader.download_all
        )
        
        if success:
            logger.info("setup_geoip_success")
            
            # Hot-reload the GeoIP resolver
            geo_resolver = getattr(request.app.state, "geo_resolver", None)
            if geo_resolver:
                geo_resolver.open()
                
            orchestrator = getattr(request.app.state, "orchestrator", None)
            if orchestrator:
                orchestrator.startup_status["geoip_loaded"] = True
                
            return {"status": "success", "message": "GeoLite2 databases downloaded successfully."}
        else:
            logger.error("setup_geoip_failed")
            raise HTTPException(status_code=500, detail="Failed to download databases. Please check your credentials.")
    except Exception as e:
        logger.exception("setup_geoip_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
