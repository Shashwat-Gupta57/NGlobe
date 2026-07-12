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

    batch_writer = getattr(request.app.state, "batch_writer", None)
    db_written = batch_writer.total_written if batch_writer else 0

    return {
        "status": "healthy",
        "version": "0.1.0",
        "uptime_seconds": round(time.time() - _start_time, 1),
        "proxy_running": proxy_running,
        "total_captured": total_requests,
        "pipeline_processed": pipeline_processed,
        "pipeline_queue_size": queue_size,
        "db_written": db_written,
        "geoip_available": geoip_available,
        "ws_connections": ws_connections,
    }
