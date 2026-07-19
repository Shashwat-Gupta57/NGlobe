"""Query reader — analytics and history queries for the REST API.

Provides all read operations against the SQLite database, returning
typed results for the API layer to serialize.
"""

from __future__ import annotations

from typing import Any, Optional

from nglobe.database.connection import DatabaseConnection
from nglobe.utils.logging import get_logger

logger = get_logger(__name__)


class QueryReader:
    """Reads from the SQLite database for analytics and history queries."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    async def get_requests(
        self,
        page: int = 1,
        limit: int = 50,
        hostname: Optional[str] = None,
        country: Optional[str] = None,
        org: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get paginated request history with optional filters."""
        conditions: list[str] = []
        params: list[Any] = []

        if hostname:
            conditions.append("hostname LIKE ?")
            params.append(f"%{hostname}%")
        if country:
            conditions.append("country_code = ?")
            params.append(country)
        if org:
            conditions.append("organization LIKE ?")
            params.append(f"%{org}%")
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        if until:
            conditions.append("timestamp <= ?")
            params.append(until)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * limit

        # Count
        count_row = await self._db.fetchone(
            f"SELECT COUNT(*) as total FROM requests {where}", tuple(params)
        )
        total = count_row["total"] if count_row else 0

        # Fetch
        rows = await self._db.fetchall(
            f"SELECT * FROM requests {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )

        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0,
        }

    async def get_request_by_id(self, request_id: int) -> Optional[dict]:
        """Get a single request by ID."""
        row = await self._db.fetchone("SELECT * FROM requests WHERE id = ?", (request_id,))
        return dict(row) if row else None

    async def get_top_countries(self, limit: int = 10, since: Optional[str] = None) -> list[dict]:
        """Get top countries by request count."""
        where = "WHERE country_code IS NOT NULL"
        params: list[Any] = []
        if since:
            where += " AND timestamp >= ?"
            params.append(since)

        rows = await self._db.fetchall(
            f"""SELECT country_code, country_name,
                       COUNT(*) as count,
                       SUM(bytes_sent + bytes_received) as bytes_total
                FROM requests {where}
                GROUP BY country_code
                ORDER BY count DESC LIMIT ?""",
            (*params, limit),
        )
        return [dict(r) for r in rows]

    async def get_top_orgs(self, limit: int = 10, since: Optional[str] = None) -> list[dict]:
        """Get top organizations by request count."""
        where = "WHERE organization IS NOT NULL"
        params: list[Any] = []
        if since:
            where += " AND timestamp >= ?"
            params.append(since)

        rows = await self._db.fetchall(
            f"""SELECT organization,
                       COUNT(*) as count,
                       SUM(bytes_sent + bytes_received) as bytes_total
                FROM requests {where}
                GROUP BY organization
                ORDER BY count DESC LIMIT ?""",
            (*params, limit),
        )
        return [dict(r) for r in rows]

    async def get_top_hostnames(self, limit: int = 10, since: Optional[str] = None) -> list[dict]:
        """Get top hostnames by request count."""
        where = ""
        params: list[Any] = []
        if since:
            where = "WHERE timestamp >= ?"
            params.append(since)

        rows = await self._db.fetchall(
            f"""SELECT hostname,
                       COUNT(*) as count,
                       SUM(bytes_sent + bytes_received) as bytes_total,
                       MAX(timestamp) as last_seen
                FROM requests {where}
                GROUP BY hostname
                ORDER BY count DESC LIMIT ?""",
            (*params, limit),
        )
        return [dict(r) for r in rows]

    async def get_bandwidth_by_country(self, since: Optional[str] = None) -> list[dict]:
        """Get bandwidth consumption grouped by country."""
        where = "WHERE country_code IS NOT NULL"
        params: list[Any] = []
        if since:
            where += " AND timestamp >= ?"
            params.append(since)

        rows = await self._db.fetchall(
            f"""SELECT country_code, country_name,
                       SUM(bytes_sent) as bytes_sent,
                       SUM(bytes_received) as bytes_received,
                       SUM(bytes_sent + bytes_received) as bytes_total
                FROM requests {where}
                GROUP BY country_code
                ORDER BY bytes_total DESC LIMIT 20""",
            tuple(params),
        )
        return [dict(r) for r in rows]

    async def get_request_rate(
        self, since: Optional[str] = None, granularity: str = "minute"
    ) -> list[dict]:
        """Get request rate over time."""
        fmt = {
            "second": "%Y-%m-%dT%H:%M:%S",
            "minute": "%Y-%m-%dT%H:%M",
            "hour": "%Y-%m-%dT%H",
        }.get(granularity, "%Y-%m-%dT%H:%M")

        where = ""
        params: list[Any] = []
        if since:
            where = "WHERE timestamp >= ?"
            params.append(since)

        rows = await self._db.fetchall(
            f"""SELECT strftime('{fmt}', timestamp) as bucket,
                       COUNT(*) as count
                FROM requests {where}
                GROUP BY bucket
                ORDER BY bucket DESC LIMIT 120""",
            tuple(params),
        )
        return [dict(r) for r in rows]

    async def get_summary(self) -> dict:
        """Get dashboard summary statistics."""
        row = await self._db.fetchone("""
            SELECT
                COUNT(*) as total_requests,
                COUNT(DISTINCT country_code) as unique_countries,
                COUNT(DISTINCT organization) as unique_organizations,
                COALESCE(SUM(bytes_sent), 0) as total_bytes_sent,
                COALESCE(SUM(bytes_received), 0) as total_bytes_received
            FROM requests
        """)
        result = dict(row) if row else {}

        # Recent rate (last 60 seconds)
        rate_row = await self._db.fetchone("""
            SELECT COUNT(*) as recent
            FROM requests
            WHERE timestamp >= datetime('now', '-60 seconds')
        """)
        result["requests_per_minute"] = rate_row["recent"] if rate_row else 0

        return result
