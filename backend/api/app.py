"""FastAPI application factory for NetworkGlobe.

Creates and configures the FastAPI app with all routes, middleware,
lifespan management, and the full startup/shutdown orchestration.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import analytics, health, requests, settings, ws, geoip
from backend.config import AppConfig
from backend.startup.orchestrator import StartupOrchestrator
from backend.utils.logging import get_logger

logger = get_logger(__name__)


def create_app(config: AppConfig) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Application configuration.

    Returns:
        Configured FastAPI instance.
    """
    orchestrator = StartupOrchestrator(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Application lifespan: full startup orchestration and shutdown."""
        logger.info("fastapi_starting", host=config.server.host, port=config.server.port)

        # Execute boot sequence
        services = await orchestrator.startup()

        # Store services on app.state for dependency injection
        for key, value in services.items():
            setattr(app.state, key, value)

        yield

        # Graceful shutdown
        await orchestrator.shutdown()
        logger.info("fastapi_shutting_down")

    app = FastAPI(
        title="NetworkGlobe",
        description="Real-time MITM proxy visualization platform",
        version="0.2.0",
        lifespan=lifespan,
    )

    # ── CORS (for Vite dev server during development) ───────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Store config in app state ───────────────────────────────
    app.state.config = config

    # ── Register routes ─────────────────────────────────────────
    app.include_router(health.router, prefix="/api")
    app.include_router(requests.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    app.include_router(geoip.router, prefix="/api")
    app.include_router(ws.router)

    # ── Serve React frontend (production only) ──────────────────
    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
        logger.info("serving_frontend", path=str(frontend_dist))

    return app
