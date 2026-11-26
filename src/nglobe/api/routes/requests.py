"""Request history and detail endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from nglobe.api.dependencies import get_query_reader
from nglobe.database.reader import QueryReader

router = APIRouter(tags=["requests"])


@router.get("/requests")
async def list_requests(
    page: int = 1,
    limit: int = 50,
    hostname: str | None = None,
    country: str | None = None,
    org: str | None = None,
    since: str | None = None,
    until: str | None = None,
    reader: QueryReader = Depends(get_query_reader),
) -> dict:
    """Get paginated request history with optional filters."""
    return await reader.get_requests(
        page=page,
        limit=limit,
        hostname=hostname,
        country=country,
        org=org,
        since=since,
        until=until,
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
