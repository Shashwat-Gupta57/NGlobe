"""Removes every trace of NGlobe from this PC (run as unins.exe or `NGlobe.exe uninstall`).

Order matters: stop the app, put the Windows proxy back, untrust the certificate,
then delete data, shortcuts, the Apps & features entry and finally the program
folder itself (after this process has exited, since its files are in use).
"""

from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

from nglobe.config import HOME, load_config
from nglobe.startup import proxy_manager
from nglobe.startup.cert_installer import CertInstaller, cert_path
from nglobe.winpaths import APP, EXE, UNINSTALL_KEY, shortcut_paths

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_MB_YESNO, _MB_ICONQUESTION, _MB_ICONINFO, _IDYES = 0x04, 0x20, 0x40, 6


def _message(text: str, flags: int) -> int:
    return ctypes.windll.user32.MessageBoxW(None, text, f"Uninstall {APP}", flags)  # type: ignore[attr-defined]


def uninstall(quiet: bool = False) -> None:
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)  # type: ignore[attr-defined]
    if (
        not quiet
        and _message(
            f"Remove {APP} and everything it saved on this PC (history, logs, certificate, settings)?",
            _MB_YESNO | _MB_ICONQUESTION,
        )
        != _IDYES
    ):
        return

    subprocess.run(["taskkill", "/F", "/IM", EXE], capture_output=True, creationflags=_NO_WINDOW)
    proxy_manager.recover()  # a killed NGlobe can't put the proxy back itself
    CertInstaller.uninstall(cert_path(load_config().proxy.cert_dir))  # Windows asks to confirm
    shutil.rmtree(HOME, ignore_errors=True)
    for link in shortcut_paths():
        link.unlink(missing_ok=True)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        pass

    install_dir = Path(sys.executable).parent
    # Only ever delete a folder that is clearly ours
    if getattr(sys, "frozen", False) and install_dir.name == APP and (install_dir / EXE).exists():
        subprocess.Popen(
            f'cmd /c ping -n 3 127.0.0.1 >nul & rmdir /s /q "{install_dir}"',
            creationflags=_NO_WINDOW | subprocess.DETACHED_PROCESS,
            cwd=str(install_dir.parent),
        )
    if not quiet:
        _message(f"{APP} was removed.", _MB_ICONINFO)
