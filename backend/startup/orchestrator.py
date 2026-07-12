"""Startup orchestrator — manages the full NetworkGlobe boot sequence.

Coordinates initialization of all subsystems in the correct order:
1. Conflict check (port + process)
2. Certificate verification
3. Database connection
4. GeoIP resolver
5. Event pipeline + bus
6. Proxy launch
7. WebSocket manager
"""

from __future__ import annotations

import asyncio
from typing import Optional

from backend.api.websocket.manager import WebSocketManager
from backend.capture.models import RawFlowEvent
from backend.capture.proxy_runner import ProxyRunner
from backend.config import AppConfig
from backend.database.connection import DatabaseConnection
from backend.database.reader import QueryReader
from backend.database.writer import BatchWriter
from backend.geoip.resolver import GeoIPResolver
from backend.pipeline.event_bus import EventBus
from backend.pipeline.event_pipeline import EventPipeline
from backend.startup.cert_manager import CertManager
from backend.startup.conflict_checker import ConflictChecker
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class StartupOrchestrator:
    """Orchestrates the full application startup and shutdown sequence.

    All subsystems are created and wired together here, then stored
    on the FastAPI app.state for dependency injection.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config

        # Subsystems — populated during startup
        self._db: Optional[DatabaseConnection] = None
        self._geo_resolver: Optional[GeoIPResolver] = None
        self._event_bus: Optional[EventBus] = None
        self._pipeline: Optional[EventPipeline] = None
        self._proxy_runner: Optional[ProxyRunner] = None
        self._batch_writer: Optional[BatchWriter] = None
        self._ws_manager: Optional[WebSocketManager] = None
        self._query_reader: Optional[QueryReader] = None
        self._event_queue: Optional[asyncio.Queue[RawFlowEvent]] = None

    async def startup(self) -> dict:
        """Execute the full boot sequence.

        Returns:
            Dictionary of subsystem references to store on app.state.
        """
        logger.info("startup_begin")

        # 1. Conflict check
        checker = ConflictChecker(
            self._config.proxy.listen_host,
            self._config.proxy.listen_port,
        )
        conflict = checker.check()
        if conflict.has_conflict:
            logger.warning(
                "startup_conflict_detected",
                conflict_type=conflict.conflict_type,
                details=conflict.details,
            )
            # Don't abort — continue without proxy. User can restart later.

        # 2. Certificate management
        cert_mgr = CertManager(self._config.proxy.cert_dir)
        cert_mgr.ensure_cert_dir()
        cert_mgr.log_cert_status()

        # 3. Database
        self._db = DatabaseConnection(self._config.database.sqlite_path)
        await self._db.open()

        # 4. GeoIP resolver
        self._geo_resolver = GeoIPResolver(
            city_db_path=self._config.geoip.city_db_path,
            asn_db_path=self._config.geoip.asn_db_path,
            cache_size=self._config.geoip.cache_size,
        )
        self._geo_resolver.open()

        # 5. Event bus + subscribers
        self._event_bus = EventBus()
        self._ws_manager = WebSocketManager(
            max_queue_size=self._config.performance.max_ws_queue_size,
        )
        self._batch_writer = BatchWriter(
            db=self._db,
            batch_size=self._config.performance.pipeline_batch_size,
            flush_interval_ms=self._config.performance.pipeline_flush_interval_ms,
        )

        # Wire subscribers
        self._event_bus.subscribe(self._ws_manager.broadcast)
        self._event_bus.subscribe(self._batch_writer.on_event)

        # 6. Event pipeline
        self._event_queue = asyncio.Queue()
        self._pipeline = EventPipeline(
            queue=self._event_queue,
            geo_resolver=self._geo_resolver,
            event_bus=self._event_bus,
        )

        # Start async subsystems
        await self._batch_writer.start()
        await self._pipeline.start()

        # 7. Proxy runner (only if no conflict)
        if not conflict.has_conflict:
            main_loop = asyncio.get_running_loop()
            self._proxy_runner = ProxyRunner(
                proxy_config=self._config.proxy,
                capture_config=self._config.capture,
                event_queue=self._event_queue,
                main_loop=main_loop,
                confdir=str(cert_mgr.cert_dir),
            )
            self._proxy_runner.start()
        else:
            logger.warning("proxy_skipped_due_to_conflict")

        # 8. Query reader
        self._query_reader = QueryReader(db=self._db)

        logger.info(
            "startup_complete",
            proxy_running=self._proxy_runner.is_running if self._proxy_runner else False,
            geoip_available=self._geo_resolver.is_available,
        )

        return {
            "db": self._db,
            "geo_resolver": self._geo_resolver,
            "event_bus": self._event_bus,
            "pipeline": self._pipeline,
            "proxy_runner": self._proxy_runner,
            "batch_writer": self._batch_writer,
            "ws_manager": self._ws_manager,
            "query_reader": self._query_reader,
        }

    async def shutdown(self) -> None:
        """Graceful shutdown of all subsystems in reverse order."""
        logger.info("shutdown_begin")

        if self._proxy_runner:
            self._proxy_runner.stop()

        if self._pipeline:
            await self._pipeline.stop()

        if self._batch_writer:
            await self._batch_writer.stop()

        if self._geo_resolver:
            self._geo_resolver.close()

        if self._db:
            await self._db.close()

        logger.info("shutdown_complete")
