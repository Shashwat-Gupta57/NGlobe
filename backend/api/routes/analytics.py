"""Analytics endpoints for dashboard charts."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_query_reader
from backend.database.reader import QueryReader

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/top-countries")
async def top_countries(
    limit: int = 10,
    since: Optional[str] = None,
    reader: QueryReader = Depends(get_query_reader),
) -> list[dict]:
    return await reader.get_top_countries(limit=limit, since=since)


@router.get("/top-orgs")
async def top_orgs(
    limit: int = 10,
    since: Optional[str] = None,
    reader: QueryReader = Depends(get_query_reader),
) -> list[dict]:
    return await reader.get_top_orgs(limit=limit, since=since)


@router.get("/top-hostnames")
async def top_hostnames(
    limit: int = 10,
    since: Optional[str] = None,
    reader: QueryReader = Depends(get_query_reader),
) -> list[dict]:
    return await reader.get_top_hostnames(limit=limit, since=since)


@router.get("/bandwidth")
async def bandwidth(
    since: Optional[str] = None,
    reader: QueryReader = Depends(get_query_reader),
) -> list[dict]:
    return await reader.get_bandwidth_by_country(since=since)


@router.get("/rate")
async def request_rate(
    since: Optional[str] = None,
    granularity: str = "minute",
    reader: QueryReader = Depends(get_query_reader),
) -> list[dict]:
    return await reader.get_request_rate(since=since, granularity=granularity)


@router.get("/summary")
async def summary(
    reader: QueryReader = Depends(get_query_reader),
) -> dict:
    return await reader.get_summary()
