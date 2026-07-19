"""Health check endpoint for NetworkGlobe."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Return application health status with live subsystem info."""
    proxy_running = False
    total_requests = 0
    geoip_available = False
    cert_installed = False
    windows_proxy_enabled = False
    db_connected = False
    startup_step = "unknown"

    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator:
        status = orchestrator.startup_status
        cert_installed = status.get("cert_installed", False)
        windows_proxy_enabled = status.get("proxy_enabled", False)
        db_connected = status.get("db_connected", False)
        startup_step = status.get("step", "unknown")

    proxy_runner = getattr(request.app.state, "proxy_runner", None)
    if proxy_runner is not None:
        proxy_running = proxy_runner.is_running
        total_requests = proxy_runner.captured_count

    geo_resolver = getattr(request.app.state, "geo_resolver", None)
    if geo_resolver is not None:
        geoip_available = geo_resolver.is_available

    pipeline = getattr(request.app.state, "pipeline", None)
    pipeline_processed = pipeline.processed_count if pipeline else 0
    queue_size = pipeline.queue_size if pipeline else 0

    ws_manager = getattr(request.app.state, "ws_manager", None)
    ws_connections = ws_manager.active_connections if ws_manager else 0
    dropped_events = ws_manager.total_dropped_events if ws_manager else 0

    batch_writer = getattr(request.app.state, "batch_writer", None)
    db_written = batch_writer.total_written if batch_writer else 0
    
    uptime = max(1.0, round(time.time() - _start_time, 1))
    rps = round(pipeline_processed / uptime, 1)

    return {
        "status": "healthy",
        "version": "0.2.0",
        "uptime_seconds": uptime,
        "startup_step": startup_step,
        "proxy_running": proxy_running,
        "windows_proxy_enabled": windows_proxy_enabled,
        "certificate_installed": cert_installed,
        "geoip_available": geoip_available,
        "sqlite_connected": db_connected,
        "ws_connections": ws_connections,
        "pipeline_queue_size": queue_size,
        "requests_per_second": rps,
        "dropped_events": dropped_events,
        "total_captured": total_requests,
        "pipeline_processed": pipeline_processed,
        "db_written": db_written,
    }
