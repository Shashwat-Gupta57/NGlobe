"""Where an installed NGlobe lives. Shared by the installer and the uninstaller (stdlib only)."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path

APP = "NGlobe"
EXE = "NGlobe.exe"
UNINSTALLER = "unins.exe"  # a copy of NGlobe.exe; the name makes it run the uninstall flow
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\NGlobe"


def default_install_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Programs" / APP


def _shell_folder(csidl: int) -> Path:
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf)  # type: ignore[attr-defined]
    return Path(buf.value)


def start_menu_dir() -> Path:
    return _shell_folder(0x0002)  # CSIDL_PROGRAMS (per user)


def desktop_dir() -> Path:
    return _shell_folder(0x0010)  # CSIDL_DESKTOPDIRECTORY (follows OneDrive redirection)


def shortcut_paths() -> list[Path]:
    return [
        start_menu_dir() / f"{APP}.lnk",
        start_menu_dir() / f"Uninstall {APP}.lnk",
        desktop_dir() / f"{APP}.lnk",
    ]
