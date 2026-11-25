"""FastAPI application factory for NetworkGlobe.

Creates and configures the FastAPI app with all routes, middleware,
lifespan management, and the full startup/shutdown orchestration.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import webbrowser
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from nglobe import __version__
from nglobe.api.routes import analytics, health, requests, settings, setup, ws
from nglobe.config import AppConfig
from nglobe.startup.orchestrator import StartupOrchestrator
from nglobe.utils.logging import get_logger
from nglobe.utils.resource_path import get_resource_path

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

        url = f"http://{config.server.host}:{config.server.port}"
        logger.info("nglobe_ready", url=url)
        if config.server.open_browser_on_start:
            webbrowser.open(url)

        yield

        # Graceful shutdown
        await orchestrator.shutdown()
        logger.info("fastapi_shutting_down")

    app = FastAPI(
        title="NetworkGlobe",
        description="Real-time MITM proxy visualization platform",
        version=__version__,
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
    app.include_router(setup.router, prefix="/api")
    app.include_router(ws.router)

    # ── Serve React frontend (production only) ──────────────────
    frontend_dist = get_resource_path("ui")
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
        logger.info("serving_frontend", path=str(frontend_dist))

    return app
