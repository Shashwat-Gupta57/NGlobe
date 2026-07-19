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


@router.post("/install-cert")
async def install_certificate(config: AppConfig = Depends(get_config)) -> dict:
    """Attempt to install the CA certificate into the Windows root store."""
    from backend.startup.cert_manager import CertManager
    from backend.startup.cert_installer import CertInstaller
    
    cert_mgr = CertManager(config.proxy.cert_dir)
    cert_path = cert_mgr.get_ca_cert_for_install()
    
    success = CertInstaller.install(cert_path)
    return {"success": success}
