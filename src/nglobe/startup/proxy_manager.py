"""Windows system-proxy management with crash recovery.

The user's original settings are written to disk *before* anything is changed,
so if NGlobe dies (window closed, crash, power loss) they are restored by the
console-close handler, atexit, or at the latest by the next launch. Without
this, a dead NGlobe leaves the whole machine pointing at a proxy that no longer
exists — i.e. no internet.
"""

from __future__ import annotations

import atexit
import ctypes
import json
import platform

from nglobe.config import HOME
from nglobe.utils.logging import get_logger

logger = get_logger(__name__)

IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    import winreg

_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
_BACKUP = HOME / "proxy_backup.json"
_VALUE_NAMES = ("ProxyEnable", "ProxyServer", "ProxyOverride")
_console_handler = None  # keep a reference so ctypes doesn't GC the callback


class ProxyManager:
    """Points the Windows system proxy at NGlobe and puts it back afterwards."""

    def __init__(self, proxy_host: str, proxy_port: int) -> None:
        self.proxy_server = f"http={proxy_host}:{proxy_port};https={proxy_host}:{proxy_port}"

    def enable(self) -> None:
        if not IS_WINDOWS:
            logger.warning("windows_proxy_skipped_non_windows")
            return
        try:
            recover()  # never back up our own leftover settings as "original"
            _BACKUP.parent.mkdir(parents=True, exist_ok=True)
            _BACKUP.write_text(json.dumps(_read()))
            _write({"ProxyEnable": 1, "ProxyServer": self.proxy_server, "ProxyOverride": "<local>"})
            atexit.register(recover)
            _install_console_close_handler()
            logger.info("windows_proxy_enabled", server=self.proxy_server)
        except OSError as e:
            logger.error("windows_proxy_enable_failed", error=str(e))

    def restore(self) -> None:
        recover()

    @property
    def is_enabled(self) -> bool:
        if not IS_WINDOWS:
            return False
        try:
            current = _read()
            return current["ProxyEnable"] == 1 and current["ProxyServer"] == self.proxy_server
        except OSError:
            return False


def recover() -> bool:
    """Restore the proxy settings saved by enable(), if any. Safe to call any time."""
    if not IS_WINDOWS or not _BACKUP.exists():
        return False
    try:
        original = json.loads(_BACKUP.read_text())
        _write({k: original.get(k) for k in _VALUE_NAMES})
        _BACKUP.unlink(missing_ok=True)
        logger.info("windows_proxy_restored")
        return True
    except (OSError, ValueError) as e:
        logger.error("windows_proxy_restore_failed", error=str(e))
        return False


def _read() -> dict:
    values: dict = {}
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY) as key:
        for name in _VALUE_NAMES:
            try:
                values[name] = winreg.QueryValueEx(key, name)[0]
            except FileNotFoundError:
                values[name] = None
    return values


def _write(values: dict) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, winreg.KEY_SET_VALUE) as key:
        for name, value in values.items():
            if value is None:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
            else:
                kind = winreg.REG_DWORD if name == "ProxyEnable" else winreg.REG_SZ
                winreg.SetValueEx(key, name, 0, kind, value)
    # Tell WinINet-based apps (Edge, Chrome, ...) to re-read the settings now
    set_option = ctypes.windll.wininet.InternetSetOptionW  # type: ignore[attr-defined]
    set_option(0, 39, 0, 0)  # INTERNET_OPTION_SETTINGS_CHANGED
    set_option(0, 37, 0, 0)  # INTERNET_OPTION_REFRESH


def _install_console_close_handler() -> None:
    """Closing the console window kills Python without running atexit; catch it first."""
    global _console_handler
    if _console_handler is not None:
        return

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
    def handler(_event: int) -> bool:
        recover()
        return False  # let Windows continue with the default action

    _console_handler = handler
    ctypes.windll.kernel32.SetConsoleCtrlHandler(handler, True)  # type: ignore[attr-defined]
