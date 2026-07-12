"""Batch writer — buffered database inserts for NetworkEvent persistence.

Subscribes to the EventBus and buffers events, flushing to SQLite
either when the batch size is reached or the flush interval expires.
This amortizes transaction overhead for high-throughput scenarios.
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

from backend.database.connection import DatabaseConnection
from backend.models import NetworkEvent
from backend.utils.logging import get_logger

logger = get_logger(__name__)

INSERT_SQL = """
INSERT INTO requests (
    timestamp, hostname, destination_ip, port, protocol,
    method, path, status_code,
    country_code, country_name, city, latitude, longitude,
    organization, asn,
    tls_version, bytes_sent, bytes_received, latency_ms,
    blocked, block_reason, rule_id, process_name, tags
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class BatchWriter:
    """Buffered database writer that batches inserts for performance.

    Subscribes to the EventBus. Flushes when batch_size is reached
    or flush_interval expires (whichever comes first).
    """

    def __init__(
        self,
        db: DatabaseConnection,
        batch_size: int = 50,
        flush_interval_ms: int = 500,
    ) -> None:
        self._db = db
        self._batch_size = batch_size
        self._flush_interval = flush_interval_ms / 1000.0
        self._buffer: list[NetworkEvent] = []
        self._flush_task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._total_written = 0

    async def start(self) -> None:
        """Start the periodic flush timer."""
        self._running = True
        self._flush_task = asyncio.create_task(
            self._flush_loop(), name="batch-writer-flush"
        )
        logger.info(
            "batch_writer_started",
            batch_size=self._batch_size,
            flush_interval_ms=int(self._flush_interval * 1000),
        )

    async def stop(self) -> None:
        """Stop the flush timer and flush remaining events."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # Final flush
        await self.flush()
        logger.info("batch_writer_stopped", total_written=self._total_written)

    async def on_event(self, event: NetworkEvent) -> None:
        """Receive an event from the EventBus (subscriber callback)."""
        self._buffer.append(event)
        if len(self._buffer) >= self._batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Write all buffered events to the database."""
        if not self._buffer:
            return

        batch = self._buffer[:]
        self._buffer.clear()

        try:
            params_list = [self._event_to_row(e) for e in batch]
            await self._db.executemany(INSERT_SQL, params_list)
            self._total_written += len(batch)
            logger.debug("batch_flushed", count=len(batch), total=self._total_written)
        except Exception as e:
            logger.error("batch_flush_error", error=str(e), lost_events=len(batch))

    async def _flush_loop(self) -> None:
        """Periodic flush timer."""
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("flush_loop_error", error=str(e))

    @staticmethod
    def _event_to_row(event: NetworkEvent) -> tuple:
        """Convert a NetworkEvent to a database row tuple."""
        return (
            event.timestamp.isoformat(),
            event.hostname,
            event.destination_ip,
            event.port,
            event.protocol,
            event.method,
            event.path,
            event.status_code,
            event.country_code,
            event.country_name,
            event.city,
            event.latitude,
            event.longitude,
            event.organization,
            event.asn,
            event.tls_version,
            event.bytes_sent,
            event.bytes_received,
            event.latency_ms,
            1 if event.blocked else 0,
            event.block_reason,
            event.rule_id,
            event.process_name,
            json.dumps(event.tags) if event.tags else None,
        )

    @property
    def total_written(self) -> int:
        """Total events written to the database."""
        return self._total_written

    @property
    def buffer_size(self) -> int:
        """Current number of events buffered."""
        return len(self._buffer)
