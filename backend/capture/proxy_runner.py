"""Mitmproxy proxy runner for NetworkGlobe.

Manages the lifecycle of an embedded mitmproxy DumpMaster instance
running in a dedicated background thread with its own asyncio event loop.
"""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, Optional

from backend.capture.addon import CaptureAddon
from backend.capture.models import RawFlowEvent
from backend.utils.logging import get_logger

if TYPE_CHECKING:
    from backend.config import ProxyConfig, CaptureConfig

logger = get_logger(__name__)


class ProxyRunner:
    """Manages an embedded mitmproxy DumpMaster in a background thread.

    The proxy runs in its own thread with a dedicated asyncio event loop,
    completely isolated from the Uvicorn main loop. Communication with the
    main thread happens via a thread-safe asyncio.Queue.
    """

    def __init__(
        self,
        proxy_config: ProxyConfig,
        capture_config: CaptureConfig,
        event_queue: asyncio.Queue[RawFlowEvent],
        main_loop: asyncio.AbstractEventLoop,
        confdir: str,
    ) -> None:
        self._proxy_config = proxy_config
        self._capture_config = capture_config
        self._event_queue = event_queue
        self._main_loop = main_loop
        self._confdir = confdir
        self._thread: Optional[threading.Thread] = None
        self._proxy_loop: Optional[asyncio.AbstractEventLoop] = None
        self._master: Optional[object] = None
        self._running = False
        self._addon: Optional[CaptureAddon] = None

    def start(self) -> None:
        """Start the mitmproxy instance in a background thread."""
        if self._running:
            logger.warning("proxy_already_running")
            return

        self._proxy_loop = asyncio.new_event_loop()
        self._addon = CaptureAddon(
            queue=self._event_queue,
            main_loop=self._main_loop,
            ignored_hosts=self._capture_config.ignored_hosts,
            max_path_length=self._capture_config.max_path_length,
        )

        self._thread = threading.Thread(
            target=self._run_proxy,
            name="networkglobe-proxy",
            daemon=True,
        )
        self._thread.start()
        self._running = True
        logger.info(
            "proxy_started",
            host=self._proxy_config.listen_host,
            port=self._proxy_config.listen_port,
            thread=self._thread.name,
        )

    def _run_proxy(self) -> None:
        """Entry point for the proxy thread. Runs the mitmproxy event loop."""
        assert self._proxy_loop is not None
        asyncio.set_event_loop(self._proxy_loop)

        try:
            self._proxy_loop.run_until_complete(self._start_master())
        except Exception as e:
            logger.error("proxy_thread_error", error=str(e))
        finally:
            self._running = False
            logger.info("proxy_thread_stopped")

    async def _start_master(self) -> None:
        """Create and run the DumpMaster within the proxy event loop."""
        from mitmproxy.options import Options
        from mitmproxy.tools.dump import DumpMaster

        opts = Options(
            listen_host=self._proxy_config.listen_host,
            listen_port=self._proxy_config.listen_port,
            ssl_insecure=self._proxy_config.ssl_insecure,
            confdir=self._confdir,
        )

        master = DumpMaster(opts, with_termlog=False, with_dumper=False)
        master.addons.add(self._addon)
        self._master = master

        logger.info("mitmproxy_master_created", confdir=self._confdir)
        await master.run()

    def stop(self) -> None:
        """Stop the mitmproxy instance and join the thread."""
        if not self._running:
            return

        logger.info("proxy_stopping")

        if self._master is not None and self._proxy_loop is not None:
            # Schedule shutdown on the proxy's event loop
            asyncio.run_coroutine_threadsafe(
                self._shutdown_master(), self._proxy_loop
            )

        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("proxy_thread_join_timeout")

        self._running = False
        logger.info("proxy_stopped")

    async def _shutdown_master(self) -> None:
        """Gracefully shut down the DumpMaster."""
        if self._master is not None:
            self._master.shutdown()  # type: ignore[attr-defined]

    @property
    def is_running(self) -> bool:
        """Check if the proxy is currently running."""
        return self._running

    @property
    def captured_count(self) -> int:
        """Return total captured events from the addon."""
        if self._addon is not None:
            return self._addon.captured_count
        return 0
