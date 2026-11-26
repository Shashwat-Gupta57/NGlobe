"""Startup orchestrator — manages the full NGlobe boot sequence.

1. Recover proxy settings left behind by a crashed run
2. Certificate check (decides decrypt vs pass-through)
3. Database, GeoIP, event bus + pipeline
4. Proxy launch (on a free port) + Windows system proxy
"""

from __future__ import annotations

import asyncio
import socket
from pathlib import Path

from nglobe.api.websocket.manager import WebSocketManager
from nglobe.capture.models import RawFlowEvent
from nglobe.capture.proxy_runner import ProxyRunner
from nglobe.config import AppConfig
from nglobe.database.connection import DatabaseConnection
from nglobe.database.reader import QueryReader
from nglobe.database.writer import BatchWriter
from nglobe.geoip.resolver import GeoIPResolver
from nglobe.pipeline.event_bus import EventBus
from nglobe.pipeline.event_pipeline import EventPipeline
from nglobe.startup import proxy_manager
from nglobe.startup.cert_installer import CertInstaller, cert_path
from nglobe.startup.proxy_manager import ProxyManager
from nglobe.utils.logging import get_logger

logger = get_logger(__name__)


class StartupOrchestrator:
    """Orchestrates the full application startup and shutdown sequence.

    All subsystems are created and wired together here, then stored
    on the FastAPI app.state for dependency injection.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config

        # Subsystems — populated during startup
        self._db: DatabaseConnection | None = None
        self._geo_resolver: GeoIPResolver | None = None
        self._event_bus: EventBus | None = None
        self._pipeline: EventPipeline | None = None
        self._proxy_runner: ProxyRunner | None = None
        self._batch_writer: BatchWriter | None = None
        self._ws_manager: WebSocketManager | None = None
        self._query_reader: QueryReader | None = None
        self._event_queue: asyncio.Queue[RawFlowEvent] | None = None
        self._proxy_manager: ProxyManager | None = None

        self.startup_status = {
            "step": "initializing",
            "proxy_enabled": False,
            "cert_installed": False,
            "geoip_loaded": False,
            "db_connected": False,
        }

    async def startup(self) -> dict:
        """Execute the full boot sequence.

        Returns:
            Dictionary of subsystem references to store on app.state.
        """
        logger.info("startup_begin")
        if proxy_manager.recover():
            logger.warning("restored_proxy_settings_from_previous_crash")

        self.startup_status["step"] = "Checking certificates"
        cert_dir = Path(self._config.proxy.cert_dir).expanduser()
        cert_dir.mkdir(parents=True, exist_ok=True)
        self.cert_path = cert_path(self._config.proxy.cert_dir)
        self.startup_status["cert_installed"] = await asyncio.to_thread(CertInstaller.is_installed, self.cert_path)

        # 3. Database
        self.startup_status["step"] = "Connecting database"
        self._db = DatabaseConnection(self._config.database.sqlite_path)
        await self._db.open()
        self.startup_status["db_connected"] = True

        # 4. GeoIP resolver
        self.startup_status["step"] = "Loading GeoIP database"
        self._geo_resolver = GeoIPResolver(
            city_db_path=self._config.geoip.city_db_path,
            asn_db_path=self._config.geoip.asn_db_path,
            cache_size=self._config.geoip.cache_size,
        )
        self._geo_resolver.open()
        self.startup_status["geoip_loaded"] = self._geo_resolver.is_available

        # 5. Event bus + subscribers
        self.startup_status["step"] = "Starting event bus"
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
        self.startup_status["step"] = "Starting pipeline"
        self._event_queue = asyncio.Queue()
        self._pipeline = EventPipeline(
            queue=self._event_queue,
            geo_resolver=self._geo_resolver,
            event_bus=self._event_bus,
        )

        # Start async subsystems
        await self._batch_writer.start()
        await self._pipeline.start()

        # 7. Proxy runner — any free port works since we set the system proxy ourselves
        self.startup_status["step"] = "Starting proxy"
        host = self._config.proxy.listen_host
        port = free_port(host, self._config.proxy.listen_port)
        self._proxy_runner = ProxyRunner(
            proxy_config=self._config.proxy.model_copy(update={"listen_port": port}),
            capture_config=self._config.capture,
            event_queue=self._event_queue,
            main_loop=asyncio.get_running_loop(),
            confdir=str(cert_dir),
            decrypt=self.startup_status["cert_installed"],
            all_apps=self._config.capture.all_apps,
        )
        self._proxy_runner.start()
        if self._config.proxy.set_system_proxy:
            self._proxy_manager = ProxyManager(host, port)
            self._proxy_manager.enable()
            self.startup_status["proxy_enabled"] = self._proxy_manager.is_enabled
        else:
            logger.info("system_proxy_not_set", proxy=f"{host}:{port}")

        # 8. Query reader
        self.startup_status["step"] = "Complete"
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
            "orchestrator": self,
        }

    async def install_certificate(self) -> bool:
        """Ask Windows to trust our CA; on success switch the proxy to decrypt mode."""
        ok = await asyncio.to_thread(CertInstaller.install, self.cert_path)
        self.startup_status["cert_installed"] = ok
        if ok and self._proxy_runner:
            self._proxy_runner.set_decrypt(True)
        return ok

    async def remove_certificate(self) -> bool:
        """Stop decrypting and remove our CA from Windows' trust store."""
        if self._proxy_runner:
            self._proxy_runner.set_decrypt(False)
        removed = await asyncio.to_thread(CertInstaller.uninstall, self.cert_path)
        self.startup_status["cert_installed"] = not removed
        return removed

    async def shutdown(self) -> None:
        """Graceful shutdown of all subsystems in reverse order."""
        logger.info("shutdown_begin")

        if self._proxy_manager:
            self._proxy_manager.restore()

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


def free_port(host: str, preferred: int) -> int:
    """Return `preferred` if it can be bound, else any free port."""
    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # No SO_REUSEADDR: on Windows it lets bind() succeed on a port already in use
            try:
                s.bind((host, port))
                return s.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("no free port available")
