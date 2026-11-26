"""Checks for the logic that can break a user's machine or silently drop traffic."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import socket
import ssl
from types import SimpleNamespace

import pytest
from mitmproxy import connection, tcp
from mitmproxy.options import Options
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.layers import TCPLayer
from mitmproxy.proxy.mode_specs import ProxyMode

from nglobe.capture.addon import CaptureAddon
from nglobe.startup import proxy_manager
from nglobe.startup.cert_installer import thumbprint
from nglobe.startup.orchestrator import free_port


@pytest.fixture
def fake_registry(tmp_path, monkeypatch):
    reg = {"ProxyEnable": 0, "ProxyServer": "corp:3128", "ProxyOverride": None}
    monkeypatch.setattr(proxy_manager, "IS_WINDOWS", True)
    monkeypatch.setattr(proxy_manager, "_BACKUP", tmp_path / "proxy_backup.json")
    monkeypatch.setattr(proxy_manager, "_read", lambda: dict(reg))
    monkeypatch.setattr(proxy_manager, "_write", reg.update)
    monkeypatch.setattr(proxy_manager, "_install_console_close_handler", lambda: None)
    return reg


def test_proxy_restored_after_crash(fake_registry):
    original = dict(fake_registry)
    proxy_manager.ProxyManager("127.0.0.1", 8888).enable()
    assert fake_registry["ProxyEnable"] == 1
    # process dies here without restore(); next launch must put things back
    assert proxy_manager.recover() is True
    assert fake_registry == original
    assert proxy_manager.recover() is False  # backup consumed


def test_enable_twice_keeps_true_original(fake_registry):
    original = dict(fake_registry)
    proxy_manager.ProxyManager("127.0.0.1", 8888).enable()
    proxy_manager.ProxyManager("127.0.0.1", 9999).enable()  # e.g. crash + relaunch
    proxy_manager.recover()
    assert fake_registry == original


def _context(host: str, port: int, mode: str = "regular") -> Context:
    client = connection.Client(peername=("127.0.0.1", 5000), sockname=("127.0.0.1", 8888))
    client.proxy_mode = ProxyMode.parse(mode)
    context = Context(client, Options())
    context.server = connection.Server(address=(host, port))
    return context


class Intercept:
    """Stands in for whatever decrypting layer mitmproxy would pick."""

    def __init__(self, context):
        self.context = context


def _decide(addon: CaptureAddon, context: Context, proposed) -> object:
    nl = SimpleNamespace(context=context, layer=proposed(context))
    addon.next_layer(nl)
    return nl.layer


def test_what_gets_decrypted():
    loop = asyncio.new_event_loop()
    addon = CaptureAddon(asyncio.Queue(), loop, decrypt=True)
    assert isinstance(_decide(addon, _context("example.com", 443), Intercept), Intercept)
    # other apps (local mode) are never decrypted
    assert isinstance(_decide(addon, _context("1.2.3.4", 443, "local"), Intercept), TCPLayer)
    # pinned hosts fall back to pass-through
    addon._passthrough_hosts.add("pinned.app")
    assert isinstance(_decide(addon, _context("pinned.app", 443), Intercept), TCPLayer)
    # untrusted CA: everything passes through
    addon.decrypt = False
    assert isinstance(_decide(addon, _context("example.com", 443), Intercept), TCPLayer)
    # "ignored" relays get a flow so their bytes are counted
    layer = _decide(addon, _context("example.com", 443), lambda c: TCPLayer(c, ignore=True))
    assert isinstance(layer, TCPLayer) and layer.flow is not None
    loop.close()


def _drain(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> list:
    loop.run_until_complete(asyncio.sleep(0))
    return [queue.get_nowait() for _ in range(queue.qsize())]


def test_raw_connection_live_then_final_with_bytes_and_sni():
    loop = asyncio.new_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    addon = CaptureAddon(queue, loop, ignored_hosts=["localhost"])
    context = _context("93.184.216.34", 443, "local")
    context.server.peername = ("93.184.216.34", 443)
    flow = tcp.TCPFlow(context.client, context.server)
    hello = _client_hello("example.com")
    for from_client, content in [(True, hello), (False, b"x" * 1000), (True, b"y" * 10)]:
        flow.messages.append(tcp.TCPMessage(from_client, content))
        addon.tcp_message(flow)
    assert flow.messages == []  # payloads aren't kept in RAM
    addon.tcp_end(flow)
    live, final = _drain(loop, queue)
    assert (live.stage, live.hostname, live.bytes_received) == ("live", "example.com", 0)
    assert (final.stage, final.bytes_sent, final.bytes_received) == ("final", len(hello) + 10, 1000)
    loop.close()


def test_dns_answers_name_bare_ips():
    loop = asyncio.new_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    addon = CaptureAddon(queue, loop)
    addon._dns_names["1.2.3.4"] = "api.example.org"
    context = _context("1.2.3.4", 5222, "local")
    context.server.peername = ("1.2.3.4", 5222)
    flow = tcp.TCPFlow(context.client, context.server)
    flow.messages.append(tcp.TCPMessage(True, b"hello"))
    addon.tcp_message(flow)
    assert _drain(loop, queue)[0].hostname == "api.example.org"
    loop.close()


def _client_hello(sni: str) -> bytes:
    """A real TLS ClientHello, as a browser would send first."""
    incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
    tls = ssl.create_default_context().wrap_bio(incoming, outgoing, server_hostname=sni)
    try:
        tls.do_handshake()
    except ssl.SSLWantReadError:
        pass
    return outgoing.read()


def test_free_port_falls_back_when_taken():
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        busy = taken.getsockname()[1]
        port = free_port("127.0.0.1", busy)
        assert port != busy and port > 0


def test_thumbprint_matches_der_sha1(tmp_path):
    der = b"\x30\x03\x02\x01\x01"
    pem = tmp_path / "c.pem"
    pem.write_text("-----BEGIN CERTIFICATE-----\n" + base64.b64encode(der).decode() + "\n-----END CERTIFICATE-----\n")
    assert thumbprint(pem) == hashlib.sha1(der).hexdigest()
    assert thumbprint(tmp_path / "missing.pem") is None


def test_app_builds_and_serves_bundled_ui():
    from nglobe.api.app import create_app
    from nglobe.config import load_config

    app = create_app(load_config())
    assert any(getattr(r, "name", "") == "frontend" for r in app.routes)
