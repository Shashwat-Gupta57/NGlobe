"""Mitmproxy conflict detection for NetworkGlobe.

Before launching the embedded mitmproxy instance, check if another
mitmproxy process is already running or if the target port is occupied.
NetworkGlobe NEVER kills another process — it informs the user and waits.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Optional

import psutil

from nglobe.utils.logging import get_logger

logger = get_logger(__name__)

# Process names that indicate a running mitmproxy instance
_MITMPROXY_PROCESS_NAMES = {"mitmdump", "mitmproxy", "mitmweb", "mitmdump.exe", "mitmproxy.exe", "mitmweb.exe"}


@dataclass
class ConflictResult:
    """Result of a mitmproxy conflict check."""
    has_conflict: bool
    conflict_type: Optional[str] = None  # "process" | "port"
    details: Optional[str] = None
    pid: Optional[int] = None
    process_name: Optional[str] = None


class ConflictChecker:
    """Detects existing mitmproxy instances and port conflicts.

    Used by the StartupOrchestrator to ensure the proxy port is
    available before launching the embedded mitmproxy.
    """

    def __init__(self, proxy_host: str, proxy_port: int) -> None:
        self._host = proxy_host
        self._port = proxy_port

    def check(self) -> ConflictResult:
        """Run all conflict checks.

        Returns:
            ConflictResult indicating whether a conflict was found.
        """
        # 1. Check for running mitmproxy processes
        process_result = self._find_mitmproxy_processes()
        if process_result.has_conflict:
            return process_result

        # 2. Check if port is available
        port_result = self._check_port()
        if port_result.has_conflict:
            return port_result

        return ConflictResult(has_conflict=False)

    def _find_mitmproxy_processes(self) -> ConflictResult:
        """Scan the process list for running mitmproxy instances."""
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    name = proc.info["name"].lower()  # type: ignore[index]
                    if name in _MITMPROXY_PROCESS_NAMES:
                        logger.warning(
                            "mitmproxy_process_found",
                            pid=proc.info["pid"],  # type: ignore[index]
                            name=proc.info["name"],  # type: ignore[index]
                        )
                        return ConflictResult(
                            has_conflict=True,
                            conflict_type="process",
                            details=(
                                f"Another mitmproxy instance is running "
                                f"(PID {proc.info['pid']}, {proc.info['name']}). "  # type: ignore[index]
                                f"Please close it before starting NetworkGlobe."
                            ),
                            pid=proc.info["pid"],  # type: ignore[index]
                            process_name=proc.info["name"],  # type: ignore[index]
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.warning("process_scan_failed", error=str(e))

        return ConflictResult(has_conflict=False)

    def _check_port(self) -> ConflictResult:
        """Check if the proxy port is available by attempting to bind."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self._host, self._port))
                return ConflictResult(has_conflict=False)
        except OSError:
            logger.warning(
                "port_in_use",
                host=self._host,
                port=self._port,
            )
            return ConflictResult(
                has_conflict=True,
                conflict_type="port",
                details=(
                    f"Port {self._port} is already in use on {self._host}. "
                    f"Please free the port or change proxy.listen_port in config.toml."
                ),
            )

    def is_port_available(self) -> bool:
        """Quick check if the proxy port is free."""
        return not self._check_port().has_conflict
