"""Canonical event model for NetworkGlobe.

NetworkEvent is the single source of truth consumed by every subsystem:
- EventPipeline produces it
- EventBus distributes it
- BatchWriter persists it
- WebSocketManager serializes it
- QueryReader reconstructs it from DB rows
- React frontend mirrors it in TypeScript

Future-compatible fields (blocked, block_reason, rule_id, process_name, tags)
are present with defaults. They cost nothing in V1 but eliminate schema
migrations when future features land.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class NetworkEvent(BaseModel):
    """Canonical event representing a single intercepted network request.

    Every subsystem in NetworkGlobe operates on this model. Fields are
    grouped by lifecycle stage (core → geo → connection → future).
    """

    # ── Core Identity ───────────────────────────────────────────
    id: Optional[int] = None  # DB-assigned after persist, None before
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ── Request Metadata ────────────────────────────────────────
    hostname: str
    destination_ip: str
    port: int = 443
    protocol: str = "HTTPS"  # "HTTP" | "HTTPS"
    method: Optional[str] = None  # GET, POST, CONNECT, etc.
    path: Optional[str] = None
    status_code: Optional[int] = None

    # ── GeoIP Enrichment ────────────────────────────────────────
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    organization: Optional[str] = None
    asn: Optional[int] = None

    # ── Connection Metadata ─────────────────────────────────────
    tls_version: Optional[str] = None  # "TLSv1.2", "TLSv1.3"
    bytes_sent: int = 0
    bytes_received: int = 0
    latency_ms: Optional[float] = None

    # ── Future: Blocking (V2+) ──────────────────────────────────
    blocked: bool = False  # Always False in V1
    block_reason: Optional[str] = None  # e.g., "domain_rule", "country_rule"
    rule_id: Optional[int] = None  # FK to block_rules (future)

    # ── Future: Process Detection (V3+) ─────────────────────────
    process_name: Optional[str] = None  # e.g., "chrome.exe", "curl"

    # ── Future: Tagging / Labeling ──────────────────────────────
    tags: list[str] = Field(default_factory=list)  # e.g., ["cdn", "analytics"]

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        },
    }
