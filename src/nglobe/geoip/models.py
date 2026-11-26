"""GeoIP resolution models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class GeoLocation:
    """Result of a GeoIP lookup for a single IP address."""

    country_code: str | None = None
    country_name: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    organization: str | None = None
    asn: int | None = None

    @property
    def is_resolved(self) -> bool:
        """Check if at least country information was resolved."""
        return self.country_code is not None

    @property
    def has_coordinates(self) -> bool:
        """Check if lat/lon coordinates are available."""
        return self.latitude is not None and self.longitude is not None
