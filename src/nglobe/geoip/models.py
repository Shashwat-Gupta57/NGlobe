"""GeoIP resolution models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True, frozen=True)
class GeoLocation:
    """Result of a GeoIP lookup for a single IP address."""

    country_code: Optional[str] = None
    country_name: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    organization: Optional[str] = None
    asn: Optional[int] = None

    @property
    def is_resolved(self) -> bool:
        """Check if at least country information was resolved."""
        return self.country_code is not None

    @property
    def has_coordinates(self) -> bool:
        """Check if lat/lon coordinates are available."""
        return self.latitude is not None and self.longitude is not None
