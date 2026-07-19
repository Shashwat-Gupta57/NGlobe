"""Downloads and extracts MaxMind GeoLite2 databases."""

import os
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from backend.utils.logging import get_logger
from backend.utils.resource_path import get_resource_path

logger = get_logger(__name__)

class GeoIPDownloader:
    """Downloader for GeoLite2 City and ASN databases."""

    def __init__(self, account_id: str, license_key: str):
        self.account_id = account_id
        self.license_key = license_key
        # Use resource path logic so it works natively and in PyInstaller
        self.data_dir = get_resource_path("geoip/data")

    def download_all(self) -> bool:
        """Download both City and ASN databases."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            city_success = self._download_db("GeoLite2-City")
            asn_success = self._download_db("GeoLite2-ASN")
            return city_success and asn_success
        except Exception as e:
            logger.error("geoip_download_failed", error=str(e))
            return False

    def _download_db(self, edition_id: str) -> bool:
        url = f"https://download.maxmind.com/geoip/databases/{edition_id}/download?suffix=tar.gz"
        
        logger.info("geoip_download_started", edition=edition_id)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as tmp:
                req = urllib.request.Request(url)
                
                # Basic Auth
                import base64
                auth_str = f"{self.account_id}:{self.license_key}"
                auth_bytes = auth_str.encode("utf-8")
                auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")
                req.add_header("Authorization", f"Basic {auth_b64}")
                
                with urllib.request.urlopen(req) as response, open(tmp.name, 'wb') as out_file:
                    out_file.write(response.read())
                
                with tarfile.open(tmp.name, "r:gz") as tar:
                    for member in tar.getmembers():
                        if member.name.endswith(".mmdb"):
                            # Extract directly to the target path without the parent directory
                            target_path = self.data_dir / f"{edition_id}.mmdb"
                            # We can't use tar.extract directly to a specific filename easily
                            with tar.extractfile(member) as source, open(target_path, "wb") as dest:
                                dest.write(source.read())
                            logger.info("geoip_extracted", path=str(target_path))
                            break
                            
            os.unlink(tmp.name)
            return True
        except Exception as e:
            logger.error("geoip_download_error", edition=edition_id, error=str(e))
            return False
