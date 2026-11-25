"""Checks for the logic that can break a user's machine or silently drop traffic."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import socket

import pytest
from mitmproxy import connection
from mitmproxy.proxy.server_hooks import ServerConnectionHookData

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


def _server(host: str, port: int, ip: str) -> ServerConnectionHookData:
    server = connection.Server(address=(host, port))
    server.peername = (ip, port)
    return ServerConnectionHookData(server=server, client=connection.Client(peername=("127.0.0.1", 5000), sockname=("127.0.0.1", 8888)))


def _drain(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> list:
    loop.run_until_complete(asyncio.sleep(0))
    return [queue.get_nowait() for _ in range(queue.qsize())]


def test_passthrough_mode_emits_per_connection():
    loop = asyncio.new_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    addon = CaptureAddon(queue, loop, ignored_hosts=["localhost"], decrypt=False)
    addon.server_connected(_server("example.com", 443, "93.184.216.34"))
    addon.server_connected(_server("localhost", 443, "127.0.0.1"))  # ignored
    events = _drain(loop, queue)
    assert [(e.hostname, e.destination_ip, e.protocol) for e in events] == [("example.com", "93.184.216.34", "HTTPS")]
    loop.close()


def test_decrypt_mode_skips_connections_except_pinned_hosts():
    loop = asyncio.new_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    addon = CaptureAddon(queue, loop, decrypt=True)
    addon.server_connected(_server("example.com", 443, "93.184.216.34"))
    assert _drain(loop, queue) == []  # response() covers it
    addon._passthrough_hosts.add("pinned.app")
    addon.server_connected(_server("pinned.app", 443, "1.2.3.4"))
    assert [e.hostname for e in _drain(loop, queue)] == ["pinned.app"]
    loop.close()


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
