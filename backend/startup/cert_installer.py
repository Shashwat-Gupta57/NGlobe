"""Certificate installer for NetworkGlobe.

Detects if the mitmproxy certificate is in the Windows trust store,
and provides a UAC-prompted installation flow if missing.
"""

import platform
import subprocess
from pathlib import Path

from backend.utils.logging import get_logger

logger = get_logger(__name__)


class CertInstaller:
    """Manages installation of the CA certificate into the system root store."""

    @staticmethod
    def is_installed() -> bool:
        """Check if the mitmproxy certificate is installed in the Windows root store."""
        if platform.system() != "Windows":
            return False

        try:
            result = subprocess.run(
                ["certutil", "-store", "root", "mitmproxy"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0,
            )
            return result.returncode == 0 and "mitmproxy" in result.stdout
        except Exception as e:
            logger.error("cert_check_failed", error=str(e))
            return False

    @staticmethod
    def install(cert_path: Path) -> bool:
        """Install the certificate via PowerShell UAC prompt."""
        if platform.system() != "Windows":
            return False

        if not cert_path.exists():
            logger.error(
                "cert_install_failed", error="Certificate not found", path=str(cert_path)
            )
            return False

        try:
            # Start-Process with -Verb RunAs triggers the UAC prompt
            ps_command = (
                f"Start-Process certutil -ArgumentList '-addstore root \"{cert_path}\"' "
                f"-Verb RunAs -Wait"
            )
            subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0,
            )
            installed = CertInstaller.is_installed()
            if installed:
                logger.info("cert_installed_successfully")
            return installed
        except Exception as e:
            logger.error("cert_install_failed", error=str(e))
            return False
