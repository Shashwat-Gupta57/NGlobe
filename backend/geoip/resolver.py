"""GeoIP resolver using MaxMind GeoLite2 databases.

Uses maxminddb directly (with C extension) for maximum lookup performance.
Wraps raw dict responses in typed GeoLocation objects. Includes an LRU
cache to avoid redundant lookups for frequently seen IPs.
"""

from __future__ import annotations

import ipaddress
from functools import lru_cache
from pathlib import Path
from typing import Optional

import maxminddb

from backend.geoip.models import GeoLocation
from backend.utils.logging import get_logger
from backend.utils.resource_path import get_resource_path

logger = get_logger(__name__)


class GeoIPResolver:
    """Resolves IP addresses to geographic locations using GeoLite2 databases.

    Uses maxminddb with the C extension for ~0.5ms per lookup.
    Results are cached in an LRU cache to avoid redundant lookups.
    """

    def __init__(
        self,
        city_db_path: str,
        asn_db_path: str,
        cache_size: int = 10_000,
    ) -> None:
        self._city_reader: Optional[maxminddb.Reader] = None
        self._asn_reader: Optional[maxminddb.Reader] = None
        self._city_path = get_resource_path(city_db_path)
        self._asn_path = get_resource_path(asn_db_path)
        self._cache_size = cache_size
        self._lookup_count = 0
        self._cache_hits = 0

        # Create cached resolve method with configurable size
        self._cached_resolve = lru_cache(maxsize=cache_size)(self._resolve_uncached)

    def open(self) -> None:
        """Open the GeoLite2 database files."""
        if self._city_path.exists():
            self._city_reader = maxminddb.open_database(
                str(self._city_path), maxminddb.MODE_MMAP_EXT
            )
            logger.info("geoip_city_db_loaded", path=str(self._city_path))
        else:
            logger.warning("geoip_city_db_missing", path=str(self._city_path))

        if self._asn_path.exists():
            self._asn_reader = maxminddb.open_database(
                str(self._asn_path), maxminddb.MODE_MMAP_EXT
            )
            logger.info("geoip_asn_db_loaded", path=str(self._asn_path))
        else:
            logger.warning("geoip_asn_db_missing", path=str(self._asn_path))

    def close(self) -> None:
        """Close the database readers and clear cache."""
        if self._city_reader:
            self._city_reader.close()
        if self._asn_reader:
            self._asn_reader.close()
        self._cached_resolve.cache_clear()
        logger.info(
            "geoip_closed",
            total_lookups=self._lookup_count,
        )

    def resolve(self, ip: str) -> GeoLocation:
        """Resolve an IP address to a GeoLocation (cached).

        Args:
            ip: IPv4 or IPv6 address string.

        Returns:
            GeoLocation with available geographic data.
        """
        self._lookup_count += 1

        if not ip or self._is_private(ip):
            return GeoLocation()

        return self._cached_resolve(ip)

    def _resolve_uncached(self, ip: str) -> GeoLocation:
        """Perform the actual GeoIP lookup (called by cache on miss)."""
        country_code = None
        country_name = None
        city = None
        latitude = None
        longitude = None
        organization = None
        asn = None

        # City database lookup
        if self._city_reader:
            try:
                result = self._city_reader.get(ip)
                if result:
                    country = result.get("country", {})
                    country_code = country.get("iso_code")
                    names = country.get("names", {})
                    country_name = names.get("en")

                    city_data = result.get("city", {})
                    city_names = city_data.get("names", {})
                    city = city_names.get("en")

                    location = result.get("location", {})
                    latitude = location.get("latitude")
                    longitude = location.get("longitude")
            except Exception as e:
                logger.debug("geoip_city_lookup_error", ip=ip, error=str(e))

        # ASN database lookup
        if self._asn_reader:
            try:
                result = self._asn_reader.get(ip)
                if result:
                    asn = result.get("autonomous_system_number")
                    organization = result.get("autonomous_system_organization")
            except Exception as e:
                logger.debug("geoip_asn_lookup_error", ip=ip, error=str(e))

        return GeoLocation(
            country_code=country_code,
            country_name=country_name,
            city=city,
            latitude=latitude,
            longitude=longitude,
            organization=organization,
            asn=asn,
        )

    @staticmethod
    def _is_private(ip: str) -> bool:
        """Check if an IP address is private/reserved."""
        try:
            return ipaddress.ip_address(ip).is_private
        except ValueError:
            return False

    @property
    def is_available(self) -> bool:
        """Check if at least the city database is loaded."""
        return self._city_reader is not None

    @property
    def stats(self) -> dict:
        """Return resolver statistics."""
        cache_info = self._cached_resolve.cache_info()
        return {
            "total_lookups": self._lookup_count,
            "cache_hits": cache_info.hits,
            "cache_misses": cache_info.misses,
            "cache_size": cache_info.currsize,
            "city_db_loaded": self._city_reader is not None,
            "asn_db_loaded": self._asn_reader is not None,
        }
