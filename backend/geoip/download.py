"""GeoIP database download helper.

Downloads GeoLite2 City and ASN databases from MaxMind.
Requires a MaxMind license key (free account at https://www.maxmind.com).

Usage:
    python -m backend.geoip.download --license-key YOUR_KEY

Or set the MAXMIND_LICENSE_KEY environment variable:
    set MAXMIND_LICENSE_KEY=YOUR_KEY
    python -m backend.geoip.download
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

# GeoLite2 download URLs
CITY_URL = "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={key}&suffix=tar.gz"
ASN_URL = "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-ASN&license_key={key}&suffix=tar.gz"

DATA_DIR = Path(__file__).resolve().parent / "data"


def download_and_extract(url: str, db_name: str, data_dir: Path) -> None:
    """Download a GeoLite2 database archive and extract the .mmdb file."""
    print(f"  Downloading {db_name}...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=60) as response:
            archive_data = response.read()
    except Exception as e:
        print(f"  ✗ Failed to download {db_name}: {e}")
        return

    print(f"  Extracting {db_name}...")
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_data), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith(".mmdb"):
                    # Extract just the .mmdb file
                    member.name = Path(member.name).name
                    tar.extract(member, path=str(data_dir))
                    print(f"  ✓ Saved {data_dir / member.name}")
                    return
        print(f"  ✗ No .mmdb file found in archive")
    except Exception as e:
        print(f"  ✗ Failed to extract {db_name}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download GeoLite2 databases")
    parser.add_argument(
        "--license-key",
        default=os.environ.get("MAXMIND_LICENSE_KEY", ""),
        help="MaxMind license key (or set MAXMIND_LICENSE_KEY env var)",
    )
    args = parser.parse_args()

    if not args.license_key:
        print("╔══════════════════════════════════════════════════════╗")
        print("║          GeoLite2 Database Download                 ║")
        print("╠══════════════════════════════════════════════════════╣")
        print("║                                                     ║")
        print("║  A MaxMind license key is required.                 ║")
        print("║                                                     ║")
        print("║  1. Create a free account at:                       ║")
        print("║     https://www.maxmind.com/en/geolite2/signup      ║")
        print("║                                                     ║")
        print("║  2. Generate a license key at:                      ║")
        print("║     https://www.maxmind.com/en/accounts/current/    ║")
        print("║     license-key                                     ║")
        print("║                                                     ║")
        print("║  3. Run this script again:                          ║")
        print("║     python -m backend.geoip.download \\              ║")
        print("║       --license-key YOUR_KEY                        ║")
        print("║                                                     ║")
        print("║  Or set the environment variable:                   ║")
        print("║     set MAXMIND_LICENSE_KEY=YOUR_KEY                ║")
        print("║                                                     ║")
        print("║  NetworkGlobe works without GeoIP databases but     ║")
        print("║  arc destinations won't be plotted on the map.      ║")
        print("║                                                     ║")
        print("╚══════════════════════════════════════════════════════╝")
        sys.exit(1)

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n📍 Downloading GeoLite2 databases to {DATA_DIR}\n")

    download_and_extract(
        CITY_URL.format(key=args.license_key),
        "GeoLite2-City",
        DATA_DIR,
    )

    download_and_extract(
        ASN_URL.format(key=args.license_key),
        "GeoLite2-ASN",
        DATA_DIR,
    )

    print("\n✓ Done! Restart NetworkGlobe to use the new databases.\n")


if __name__ == "__main__":
    main()
