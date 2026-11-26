"""Mitmproxy addon that turns traffic into RawFlowEvents.

Traffic arrives two ways:
- Browsers (and anything honouring the Windows proxy) via the regular proxy.
  Decrypted when our CA is trusted: one event per HTTP request with
  method/path/status/bytes/latency.
- Every other app via mitmproxy's "local" mode (WinDivert, one UAC prompt),
  when available. Always passed through untouched so nothing breaks.

Anything not decrypted (local-mode traffic, CA not trusted, apps that pin
certificates) is relayed as raw TCP/UDP. Those connections produce a "live"
event when data first flows (so the globe reacts instantly) and a "final"
event with byte counts when they close (that one is persisted).

Runs in the proxy thread; events are handed to the main loop thread-safely.
"""

from __future__ import annotations

import asyncio
import fnmatch
import ipaddress
from datetime import datetime, timezone

from mitmproxy import ctx, dns, http, tcp, udp
from mitmproxy.proxy.layer import NextLayer
from mitmproxy.proxy.layers import DNSLayer, TCPLayer, UDPLayer
from mitmproxy.proxy.layers.tls import parse_client_hello
from mitmproxy.proxy.mode_specs import ProxyMode
from mitmproxy.tls import TlsData

from nglobe.capture.models import RawFlowEvent
from nglobe.utils.logging import get_logger

logger = get_logger(__name__)

_MAX_DNS_CACHE = 5000


class CaptureAddon:
    def __init__(
        self,
        queue: asyncio.Queue[RawFlowEvent],
        main_loop: asyncio.AbstractEventLoop,
        ignored_hosts: list[str] | None = None,
        max_path_length: int = 500,
        decrypt: bool = False,
        all_apps: bool = True,
    ) -> None:
        self._queue = queue
        self._main_loop = main_loop
        self._ignored_hosts = [p.lower() for p in (ignored_hosts or [])]
        self._max_path_length = max_path_length
        self.decrypt = decrypt
        self._want_all_apps = all_apps
        self.all_apps: bool | None = None  # None = not tried / waiting for UAC
        self._passthrough_hosts: set[str] = set()
        self._dns_names: dict[str, str] = {}  # ip -> hostname seen in DNS answers
        self._captured_count = 0
        self._tasks: set[asyncio.Task] = set()

    # ── startup: try to capture every app, not just browsers ────

    def running(self) -> None:
        if self._want_all_apps:
            task = asyncio.get_running_loop().create_task(self._start_all_apps())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _start_all_apps(self) -> None:
        servers = ctx.master.addons.get("proxyserver").servers
        base = [ProxyMode.parse(m) for m in ctx.options.mode]
        # Shows one UAC prompt (mitmproxy elevates only its small redirector process)
        ok = await servers.update([*base, ProxyMode.parse("local")])
        if not ok:
            await servers.update(base)  # declined / unavailable: browsers only
        self.all_apps = ok
        logger.info("all_apps_capture", enabled=ok)

    # ── deciding what gets decrypted ────────────────────────────

    def next_layer(self, nextlayer: NextLayer) -> None:
        context, layer = nextlayer.context, nextlayer.layer
        # Only once a destination is known; the regular proxy's own HTTP layer must stay
        if layer is None or context.server.address is None or isinstance(layer, DNSLayer):
            return
        if isinstance(layer, (TCPLayer, UDPLayer)):
            if layer.flow is None:  # "ignored" relays have no flow; give them one so we can count bytes
                nextlayer.layer = type(layer)(context)
            return
        local = context.client.proxy_mode.type_name == "local"
        if local or not self.decrypt or context.server.address[0] in self._passthrough_hosts:
            udp_ = context.client.transport_protocol == "udp"
            nextlayer.layer = UDPLayer(context) if udp_ else TCPLayer(context)

    def tls_failed_client(self, data: TlsData) -> None:
        host = data.context.client.sni or (data.context.server.address or ("",))[0]
        if self.decrypt and host and host not in self._passthrough_hosts:
            logger.info("tls_interception_refused_passthrough", host=host)
            self._passthrough_hosts.add(host)

    # ── decrypted / plain HTTP: one event per request ───────────

    def response(self, flow: http.HTTPFlow) -> None:
        self._emit(self._from_http(flow))

    def error(self, flow: http.HTTPFlow) -> None:
        if flow.server_conn.peername:  # failed requests still went somewhere
            self._emit(self._from_http(flow))

    # ── raw relayed connections: live event + final byte count ──

    def tcp_message(self, flow: tcp.TCPFlow) -> None:
        self._on_message(flow)

    def udp_message(self, flow: udp.UDPFlow) -> None:
        self._on_message(flow)

    def tcp_end(self, flow: tcp.TCPFlow) -> None:
        self._emit(self._from_raw(flow, "final"))

    tcp_error = udp_end = udp_error = tcp_end

    def dns_response(self, flow: dns.DNSFlow) -> None:
        if not flow.response or not flow.request.questions:
            return
        name = flow.request.questions[0].name
        if len(self._dns_names) > _MAX_DNS_CACHE:
            self._dns_names.clear()
        for answer in flow.response.answers:
            if answer.type == 1:
                self._dns_names[str(answer.ipv4_address)] = name
            elif answer.type == 28:
                self._dns_names[str(answer.ipv6_address)] = name

    # ── helpers ─────────────────────────────────────────────────

    def _on_message(self, flow: tcp.TCPFlow | udp.UDPFlow) -> None:
        msg = flow.messages[-1]
        meta = flow.metadata
        key = "ng_sent" if msg.from_client else "ng_recv"
        meta[key] = meta.get(key, 0) + len(msg.content)
        if "ng_host" not in meta and msg.from_client:
            meta["ng_host"] = self._hostname(flow, msg.content)
            self._emit(self._from_raw(flow, "live"))
        flow.messages.clear()  # counted; don't keep payloads in RAM

    def _hostname(self, flow: tcp.TCPFlow | udp.UDPFlow, first_bytes: bytes) -> str:
        host = flow.server_conn.address[0] if flow.server_conn.address else ""
        if not _is_ip(host):
            return host  # regular proxy: CONNECT already named it
        if name := self._dns_names.get(host):
            return name
        if isinstance(flow, tcp.TCPFlow):
            try:
                if (hello := parse_client_hello(first_bytes)) and hello.sni:
                    return hello.sni
            except ValueError:
                pass
        return host

    def _from_raw(self, flow: tcp.TCPFlow | udp.UDPFlow, stage: str) -> RawFlowEvent:
        server = flow.server_conn
        port = server.address[1] if server.address else 0
        meta = flow.metadata
        return RawFlowEvent(
            timestamp=datetime.now(timezone.utc),
            hostname=meta.get("ng_host") or (server.address[0] if server.address else ""),
            destination_ip=server.peername[0] if server.peername else "",
            port=port,
            protocol=("QUIC" if port == 443 else "UDP")
            if isinstance(flow, udp.UDPFlow)
            else "HTTPS"
            if port == 443
            else "HTTP"
            if port == 80
            else "TCP",
            method="CONNECT",
            tls_version=server.tls_version,
            bytes_sent=meta.get("ng_sent", 0),
            bytes_received=meta.get("ng_recv", 0),
            stage=stage,
        )

    def _from_http(self, flow: http.HTTPFlow) -> RawFlowEvent:
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

    def _emit(self, event: RawFlowEvent) -> None:
        if not event.destination_ip or self._should_ignore(event.hostname):
            return
        if event.stage != "final":
            self._captured_count += 1
        self._main_loop.call_soon_threadsafe(self._queue.put_nowait, event)

    def _should_ignore(self, hostname: str) -> bool:
        hostname = hostname.lower()
        return any(fnmatch.fnmatch(hostname, p) for p in self._ignored_hosts)

    @property
    def captured_count(self) -> int:
        return self._captured_count


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
