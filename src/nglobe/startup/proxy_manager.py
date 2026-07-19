"""Windows proxy management.

Automatically enables the proxy on startup and restores original settings
on shutdown to ensure seamless user experience.
"""

import ctypes
import platform
import winreg
from typing import Optional

from nglobe.utils.logging import get_logger

logger = get_logger(__name__)


class ProxyManager:
    """Manages Windows system proxy settings via registry and wininet."""

    def __init__(self, proxy_host: str, proxy_port: int) -> None:
        self.proxy_server = f"http={proxy_host}:{proxy_port};https={proxy_host}:{proxy_port}"
        self.original_enable: Optional[int] = None
        self.original_server: Optional[str] = None
        self.original_override: Optional[str] = None
        self.is_windows = platform.system() == "Windows"

    def enable(self) -> None:
        """Save current proxy state and enable NetworkGlobe proxy."""
        if not self.is_windows:
            logger.warning("windows_proxy_skipped_non_windows")
            return

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0,
                winreg.KEY_ALL_ACCESS,
            ) as key:
                # Save original state
                try:
                    self.original_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                except FileNotFoundError:
                    self.original_enable = 0
                try:
                    self.original_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                except FileNotFoundError:
                    self.original_server = None
                try:
                    self.original_override, _ = winreg.QueryValueEx(key, "ProxyOverride")
                except FileNotFoundError:
                    self.original_override = None

                # Set new state
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, self.proxy_server)
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "<local>")

            self._notify_system()
            logger.info("windows_proxy_enabled", server=self.proxy_server)
        except Exception as e:
            logger.error("windows_proxy_enable_failed", error=str(e))

    def restore(self) -> None:
        """Restore original proxy state."""
        if not self.is_windows or self.original_enable is None:
            return

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0,
                winreg.KEY_ALL_ACCESS,
            ) as key:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, self.original_enable)
                if self.original_server:
                    winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, self.original_server)
                else:
                    try:
                        winreg.DeleteValue(key, "ProxyServer")
                    except FileNotFoundError:
                        pass

                if self.original_override:
                    winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, self.original_override)
                else:
                    try:
                        winreg.DeleteValue(key, "ProxyOverride")
                    except FileNotFoundError:
                        pass

            self._notify_system()
            logger.info("windows_proxy_restored")
            self.original_enable = None  # Prevent double restore
        except Exception as e:
            logger.error("windows_proxy_restore_failed", error=str(e))

    def _notify_system(self) -> None:
        """Notify the OS that internet settings have changed."""
        try:
            internet_set_option = ctypes.windll.wininet.InternetSetOptionW  # type: ignore[attr-defined]
            INTERNET_OPTION_SETTINGS_CHANGED = 39
            INTERNET_OPTION_REFRESH = 37
            internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
            internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)
        except Exception as e:
            logger.error("windows_proxy_notify_failed", error=str(e))

    @property
    def is_enabled(self) -> bool:
        """Check if our proxy is currently enabled."""
        if not self.is_windows:
            return False

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            ) as key:
                enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                server, _ = winreg.QueryValueEx(key, "ProxyServer")
                return enable == 1 and server == self.proxy_server
        except Exception:
            return False
