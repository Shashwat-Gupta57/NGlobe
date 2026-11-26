"""History database: size and clearing."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/database", tags=["database"])


@router.get("")
async def database_info(request: Request) -> dict:
    db = request.app.state.db
    row = await db.fetchone("SELECT COUNT(*) AS rows FROM requests")
    return {"size_bytes": db.size_bytes, "rows": row["rows"] if row else 0}


@router.delete("")
async def clear_database(request: Request) -> dict:
    await request.app.state.db.clear()
    return {"size_bytes": request.app.state.db.size_bytes, "rows": 0}
