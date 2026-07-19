"""CA certificate management for NetworkGlobe.

Handles verification and generation of the mitmproxy CA certificate
required for HTTPS interception. Certificates are stored in a dedicated
directory separate from the user's default mitmproxy configuration.
"""

from __future__ import annotations

from pathlib import Path

from nglobe.utils.logging import get_logger

logger = get_logger(__name__)


class CertManager:
    """Manages the mitmproxy CA certificate lifecycle.

    NetworkGlobe reuses the standard mitmproxy certificate directory
    to ensure browsers that already trust mitmproxy work seamlessly.
    """

    def __init__(self, cert_dir: str) -> None:
        self._cert_dir = Path(cert_dir).expanduser().resolve()

    @property
    def cert_dir(self) -> Path:
        """Return the resolved certificate directory path."""
        return self._cert_dir

    def cert_exists(self) -> bool:
        """Check if the CA certificate already exists."""
        ca_pem = self._cert_dir / "mitmproxy-ca.pem"
        return ca_pem.exists()

    def ensure_cert_dir(self) -> None:
        """Create the certificate directory if it doesn't exist."""
        self._cert_dir.mkdir(parents=True, exist_ok=True)
        logger.info("cert_dir_ensured", path=str(self._cert_dir))

    def get_ca_cert_path(self) -> Path:
        """Return the path to the CA certificate PEM file.

        Note: mitmproxy generates this automatically on first run
        when confdir is set to our cert directory.
        """
        return self._cert_dir / "mitmproxy-ca.pem"

    def get_ca_cert_for_install(self) -> Path:
        """Return the path to the CA cert in a format suitable for OS installation.

        On Windows, users need the .p12 or .pem file to import into the trust store.
        """
        return self._cert_dir / "mitmproxy-ca-cert.pem"

    def log_cert_status(self) -> None:
        """Log the current certificate status for diagnostics."""
        if self.cert_exists():
            logger.info(
                "ca_cert_found",
                path=str(self.get_ca_cert_path()),
            )
        else:
            logger.warning(
                "ca_cert_missing",
                expected_path=str(self.get_ca_cert_path()),
                message="mitmproxy will generate certificates on first launch",
            )
