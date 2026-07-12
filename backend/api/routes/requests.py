"""Request history and detail endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_query_reader
from backend.database.reader import QueryReader

router = APIRouter(tags=["requests"])


@router.get("/requests")
async def list_requests(
    page: int = 1,
    limit: int = 50,
    hostname: Optional[str] = None,
    country: Optional[str] = None,
    org: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    reader: QueryReader = Depends(get_query_reader),
) -> dict:
    """Get paginated request history with optional filters."""
    return await reader.get_requests(
        page=page, limit=limit, hostname=hostname,
        country=country, org=org, since=since, until=until,
    )


@router.get("/requests/{request_id}")
async def get_request(
    request_id: int,
    reader: QueryReader = Depends(get_query_reader),
) -> dict:
    """Get a single request by ID."""
    result = await reader.get_request_by_id(request_id)
    if result is None:
        return {"error": "not_found"}
    return result
