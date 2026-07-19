"""SQLite connection manager for NetworkGlobe.

Manages an aiosqlite connection with WAL mode, proper PRAGMAs,
and schema initialization. Provides a single shared connection
used by both the BatchWriter and QueryReader.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import aiosqlite

from nglobe.database.schema import CREATE_INDEXES, CREATE_REQUESTS_TABLE, CREATE_SETTINGS_TABLE, PRAGMAS
from nglobe.utils.logging import get_logger

logger = get_logger(__name__)


class DatabaseConnection:
    """Manages a single aiosqlite connection with performance optimizations.

    The connection is opened once at startup and shared across
    the BatchWriter and QueryReader via dependency injection.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path)
        self._conn: Optional[aiosqlite.Connection] = None

    async def open(self) -> None:
        """Open the database connection and initialize schema."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = await aiosqlite.connect(str(self._db_path))
        self._conn.row_factory = aiosqlite.Row

        # Apply performance PRAGMAs
        for pragma in PRAGMAS:
            await self._conn.execute(pragma)

        # Create tables and indexes
        await self._conn.execute(CREATE_REQUESTS_TABLE)
        await self._conn.execute(CREATE_SETTINGS_TABLE)
        for index_sql in CREATE_INDEXES:
            await self._conn.execute(index_sql)
        await self._conn.commit()

        logger.info("database_opened", path=str(self._db_path))

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            logger.info("database_closed")

    @property
    def connection(self) -> aiosqlite.Connection:
        """Return the active connection (raises if not open)."""
        if self._conn is None:
            raise RuntimeError("Database connection not open")
        return self._conn

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a SQL statement."""
        return await self.connection.execute(sql, params)

    async def executemany(self, sql: str, params_list: list[tuple]) -> None:
        """Execute a SQL statement for multiple parameter sets."""
        await self.connection.executemany(sql, params_list)
        await self.connection.commit()

    async def fetchone(self, sql: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
        """Execute and fetch one row."""
        cursor = await self.connection.execute(sql, params)
        return await cursor.fetchone()

    async def fetchall(self, sql: str, params: tuple = ()) -> list[aiosqlite.Row]:
        """Execute and fetch all rows."""
        cursor = await self.connection.execute(sql, params)
        return await cursor.fetchall()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.connection.commit()
