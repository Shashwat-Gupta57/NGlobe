"""Mitmproxy capture addon for NetworkGlobe.

This addon is registered with the embedded mitmproxy DumpMaster instance.
It intercepts HTTP/S flows, extracts metadata into RawFlowEvent objects,
and pushes them to a thread-safe asyncio.Queue for processing by the
EventPipeline on the main thread.
"""

from __future__ import annotations

import asyncio
import fnmatch
import time
from datetime import datetime, timezone
from typing import Optional

from mitmproxy import http

from nglobe.capture.models import RawFlowEvent
from nglobe.utils.logging import get_logger

logger = get_logger(__name__)


class CaptureAddon:
    """Mitmproxy addon that captures HTTP/S flow metadata.

    Runs in the proxy thread. Pushes RawFlowEvent objects to a
    thread-safe queue consumed by the EventPipeline on the main thread.
    """

    def __init__(
        self,
        queue: asyncio.Queue[RawFlowEvent],
        main_loop: asyncio.AbstractEventLoop,
        ignored_hosts: Optional[list[str]] = None,
        max_path_length: int = 500,
    ) -> None:
        self._queue = queue
        self._main_loop = main_loop
        self._ignored_hosts = ignored_hosts or []
        self._max_path_length = max_path_length
        self._flow_start_times: dict[str, float] = {}
        self._captured_count = 0

    def request(self, flow: http.HTTPFlow) -> None:
        """Called when a client request is received."""
        logger.debug("capture_addon_request", host=flow.request.pretty_host, path=flow.request.path)
        # Record start time for latency calculation
        self._flow_start_times[flow.id] = time.monotonic()

    def response(self, flow: http.HTTPFlow) -> None:
        """Called when a server response is received.

        Extracts all available metadata and pushes a RawFlowEvent
        to the queue for pipeline processing.
        """
        try:
            hostname = flow.request.pretty_host
            logger.debug("capture_addon_response", host=hostname, status=flow.response.status_code if flow.response else None)
            if self._should_ignore(hostname):
                logger.debug("capture_addon_ignored", host=hostname)
                return

            event = self._extract_metadata(flow)
            # Thread-safe push to the main loop's queue
            asyncio.run_coroutine_threadsafe(
                self._queue.put(event), self._main_loop
            )
            logger.debug("capture_addon_queued", host=hostname)
            self._captured_count += 1

            if self._captured_count % 100 == 0:
                logger.debug(
                    "capture_milestone",
                    total_captured=self._captured_count,
                )
        except Exception as e:
            logger.error("capture_error", error=str(e), flow_id=flow.id)

    def _extract_metadata(self, flow: http.HTTPFlow) -> RawFlowEvent:
        """Extract all available metadata from a completed flow."""
        # Calculate latency
        latency_ms: Optional[float] = None
        start_time = self._flow_start_times.pop(flow.id, None)
        if start_time is not None:
            latency_ms = (time.monotonic() - start_time) * 1000

        # Determine protocol
        protocol = "HTTPS" if flow.request.scheme == "https" else "HTTP"

        # Extract TLS version
        tls_version: Optional[str] = None
        if flow.server_conn and flow.server_conn.tls_version:
            tls_version = flow.server_conn.tls_version

        # Resolve destination IP
        destination_ip = ""
        if flow.server_conn and flow.server_conn.peername:
            destination_ip = flow.server_conn.peername[0]

        # Port
        port = flow.request.port

        # Bytes
        bytes_sent = len(flow.request.raw_content) if flow.request.raw_content else 0
        bytes_received = 0
        if flow.response and flow.response.raw_content:
            bytes_received = len(flow.response.raw_content)

        # Path (truncated)
        path = flow.request.path
        if path and len(path) > self._max_path_length:
            path = path[: self._max_path_length] + "..."

        # Status code
        status_code: Optional[int] = None
        if flow.response:
            status_code = flow.response.status_code

        return RawFlowEvent(
            timestamp=datetime.now(timezone.utc),
            hostname=flow.request.pretty_host,
            destination_ip=destination_ip,
            port=port,
            protocol=protocol,
            method=flow.request.method,
            path=path,
            status_code=status_code,
            tls_version=tls_version,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            latency_ms=latency_ms,
        )

    def _should_ignore(self, hostname: str) -> bool:
        """Check if a hostname matches any ignore pattern."""
        for pattern in self._ignored_hosts:
            if fnmatch.fnmatch(hostname.lower(), pattern.lower()):
                return True
        return False

    @property
    def captured_count(self) -> int:
        """Return the total number of captured flows."""
        return self._captured_count
