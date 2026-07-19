"""Raw flow event model — lightweight data extracted from mitmproxy flows.

This is an intermediate model used only within the capture subsystem.
The EventPipeline enriches it with GeoIP data and converts it into
the canonical NetworkEvent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(slots=True)
class RawFlowEvent:
    """Lightweight event extracted from a mitmproxy HTTPFlow.

    Contains only the fields directly available from the flow object,
    without any GeoIP enrichment. The EventPipeline handles enrichment.
    """

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hostname: str = ""
    destination_ip: str = ""
    port: int = 443
    protocol: str = "HTTPS"
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    tls_version: Optional[str] = None
    bytes_sent: int = 0
    bytes_received: int = 0
    latency_ms: Optional[float] = None
