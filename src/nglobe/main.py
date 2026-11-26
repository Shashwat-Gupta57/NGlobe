"""NGlobe entry point — `nglobe`, `python -m nglobe`, or double-click NGlobe.exe."""

from __future__ import annotations

import argparse
import ctypes
import json
import multiprocessing
import sys
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

from nglobe import __version__
from nglobe.api.app import create_app
from nglobe.config import load_config
from nglobe.startup import proxy_manager
from nglobe.startup.orchestrator import free_port
from nglobe.utils.logging import get_logger, setup_logging
from nglobe.winpaths import UNINSTALLER


def _nglobe_running_at(url: str) -> bool:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"{url}/api/health", timeout=1) as resp:
            return json.load(resp).get("status") == "healthy"
    except (OSError, ValueError):
        return False


def main() -> None:
    multiprocessing.freeze_support()  # PyInstaller on Windows

    parser = argparse.ArgumentParser(prog="nglobe", description="Real-time 3D visualization of your network traffic")
    parser.add_argument("command", nargs="?", default="start", choices=["start", "version", "uninstall", "recover"])
    parser.add_argument("--quiet", action="store_true", help="uninstall without dialogs")
    args = parser.parse_args()
    if Path(sys.executable).name.lower() == UNINSTALLER:
        args.command = "uninstall"  # unins.exe is a renamed copy of NGlobe.exe
    if args.command == "version":
        print(f"NGlobe {__version__}")
        return
    if args.command == "uninstall":
        from nglobe.uninstall import uninstall

        uninstall(quiet=args.quiet)
        return
    if args.command == "recover":  # used by the installer after closing a running copy
        proxy_manager.recover()
        return

    config = load_config()
    setup_logging(config.logging)
    logger = get_logger("nglobe")

    url = f"http://{config.server.host}:{config.server.port}"
    if _nglobe_running_at(url):
        # Second double-click: just bring up the existing instance
        print(f"NGlobe is already running at {url}")
        webbrowser.open(url)
        return
    config.server.port = free_port(config.server.host, config.server.port)
    url = f"http://{config.server.host}:{config.server.port}"

    if sys.platform == "win32":
        ctypes.windll.kernel32.SetConsoleTitleW("NGlobe — close this window to stop")  # type: ignore[attr-defined]
    print(
        f"\n  NGlobe {__version__}  ->  {url}\n  Close this window (or press Ctrl+C) to stop; your proxy settings are restored.\n"
    )
    logger.info("nglobe_starting", version=__version__, url=url, proxy_port=config.proxy.listen_port)

    uvicorn.run(
        create_app(config),
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
