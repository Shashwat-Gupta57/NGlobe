"""Mitmproxy addon that turns traffic into RawFlowEvents.

Two modes:
- decrypt=True  (our CA is trusted): TLS is intercepted, one event per HTTP
  request with method/path/status/bytes/latency.
- decrypt=False (CA not trusted): every connection is passed through untouched
  so the user's internet keeps working; one event per server connection with
  host + IP, which is all the globe needs.

Hosts that refuse interception (certificate pinning) are switched to
pass-through on the fly instead of staying broken.

Runs in the proxy thread; events are handed to the main loop thread-safely.
"""

from __future__ import annotations

import asyncio
import fnmatch
import re
from datetime import datetime, timezone
from typing import Optional

from mitmproxy import ctx, http
from mitmproxy.proxy.server_hooks import ServerConnectionHookData
from mitmproxy.tls import TlsData

from nglobe.capture.models import RawFlowEvent
from nglobe.utils.logging import get_logger

logger = get_logger(__name__)


class CaptureAddon:
    def __init__(
        self,
        queue: asyncio.Queue[RawFlowEvent],
        main_loop: asyncio.AbstractEventLoop,
        ignored_hosts: Optional[list[str]] = None,
        max_path_length: int = 500,
        decrypt: bool = False,
    ) -> None:
        self._queue = queue
        self._main_loop = main_loop
        self._ignored_hosts = [p.lower() for p in (ignored_hosts or [])]
        self._max_path_length = max_path_length
        self.decrypt = decrypt
        self._passthrough_hosts: set[str] = set()
        self._captured_count = 0

    # ── mitmproxy hooks ─────────────────────────────────────────

    def running(self) -> None:
        self.sync_options()

    def response(self, flow: http.HTTPFlow) -> None:
        if self.decrypt:
            self._emit(self._from_flow(flow))

    def error(self, flow: http.HTTPFlow) -> None:
        # Failed requests (resets, timeouts) still went somewhere
        if self.decrypt and flow.server_conn.peername:
            self._emit(self._from_flow(flow))

    def server_connected(self, data: ServerConnectionHookData) -> None:
        server = data.server
        if not server.address:
            return
        host, port = server.address[0], server.address[1]
        if self.decrypt and host not in self._passthrough_hosts:
            return  # covered per-request by response()
        self._emit(RawFlowEvent(
            timestamp=datetime.now(timezone.utc),
            hostname=host,
            destination_ip=server.peername[0] if server.peername else "",
            port=port,
            protocol="HTTPS" if port == 443 else "HTTP" if port == 80 else "TCP",
            method="CONNECT",
            tls_version=server.tls_version,
        ))

    def tls_failed_client(self, data: TlsData) -> None:
        host = data.context.client.sni or (data.context.server.address or ("",))[0]
        if self.decrypt and host and host not in self._passthrough_hosts:
            logger.info("tls_interception_refused_passthrough", host=host)
            self._passthrough_hosts.add(host)
            self.sync_options()

    # ── helpers ─────────────────────────────────────────────────

    def sync_options(self) -> None:
        """Push the current mode into mitmproxy. Must run on the proxy loop."""
        if self.decrypt:
            patterns = [f"^{re.escape(h)}:" for h in sorted(self._passthrough_hosts)]
        else:
            patterns = [".*"]
        ctx.options.update(ignore_hosts=patterns)

    def _emit(self, event: RawFlowEvent) -> None:
        if not event.destination_ip or self._should_ignore(event.hostname):
            return
        self._captured_count += 1
        self._main_loop.call_soon_threadsafe(self._queue.put_nowait, event)

    def _from_flow(self, flow: http.HTTPFlow) -> RawFlowEvent:
        req, resp = flow.request, flow.response
        path = req.path
        if path and len(path) > self._max_path_length:
            path = path[: self._max_path_length] + "..."
        latency_ms = None
        if resp and resp.timestamp_end and req.timestamp_start:
            latency_ms = (resp.timestamp_end - req.timestamp_start) * 1000
        return RawFlowEvent(
            timestamp=datetime.now(timezone.utc),
            hostname=req.pretty_host,
            destination_ip=flow.server_conn.peername[0] if flow.server_conn.peername else "",
            port=req.port,
            protocol="HTTPS" if req.scheme == "https" else "HTTP",
            method=req.method,
            path=path,
            status_code=resp.status_code if resp else None,
            tls_version=flow.server_conn.tls_version,
            bytes_sent=len(req.raw_content or b""),
            bytes_received=len(resp.raw_content or b"") if resp else 0,
            latency_ms=latency_ms,
        )

    def _should_ignore(self, hostname: str) -> bool:
        hostname = hostname.lower()
        return any(fnmatch.fnmatch(hostname, p) for p in self._ignored_hosts)

    @property
    def captured_count(self) -> int:
        return self._captured_count
