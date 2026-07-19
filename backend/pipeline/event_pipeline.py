"""Event pipeline — consumes raw flow events, enriches with GeoIP, publishes NetworkEvents.

The pipeline is the central processing stage between capture and distribution.
It runs as an async task on the main event loop, consuming RawFlowEvents from
the thread-safe queue and producing canonical NetworkEvent objects.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from backend.capture.models import RawFlowEvent
from backend.geoip.resolver import GeoIPResolver
from backend.models import NetworkEvent
from backend.pipeline.event_bus import EventBus
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class EventPipeline:
    """Async consumer that enriches raw flow events and publishes them.

    Consumes RawFlowEvent objects from the capture queue, resolves
    GeoIP data, constructs canonical NetworkEvent objects, and
    publishes them through the EventBus.
    """

    def __init__(
        self,
        queue: asyncio.Queue[RawFlowEvent],
        geo_resolver: GeoIPResolver,
        event_bus: EventBus,
    ) -> None:
        self._queue = queue
        self._geo_resolver = geo_resolver
        self._event_bus = event_bus
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._processed_count = 0

    async def start(self) -> None:
        """Start the pipeline consumer loop."""
        self._running = True
        self._task = asyncio.create_task(self._process_loop(), name="event-pipeline")
        logger.info("event_pipeline_started")

    async def stop(self) -> None:
        """Stop the pipeline consumer loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(
            "event_pipeline_stopped",
            total_processed=self._processed_count,
        )

    async def _process_loop(self) -> None:
        """Main consumer loop — runs until stopped."""
        logger.info("event_pipeline_loop_started")
        while self._running:
            try:
                raw_event = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                logger.debug("pipeline_dequeued", host=raw_event.hostname)
                event = self._build_network_event(raw_event)
                logger.info(
                    "pipeline_event_built", 
                    host=event.hostname, 
                    dest_ip=event.destination_ip, 
                    country=event.country_name, 
                    city=event.city, 
                    lat=event.latitude, 
                    lon=event.longitude
                )
                await self._event_bus.publish(event)
                logger.debug("pipeline_published", host=event.hostname)
                self._processed_count += 1
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("pipeline_process_error", error=str(e))

    def _build_network_event(self, raw: RawFlowEvent) -> NetworkEvent:
        """Enrich a RawFlowEvent with GeoIP data and build a NetworkEvent."""
        geo = self._geo_resolver.resolve(raw.destination_ip)

        return NetworkEvent(
            timestamp=raw.timestamp,
            hostname=raw.hostname,
            destination_ip=raw.destination_ip,
            port=raw.port,
            protocol=raw.protocol,
            method=raw.method,
            path=raw.path,
            status_code=raw.status_code,
            country_code=geo.country_code,
            country_name=geo.country_name,
            city=geo.city,
            latitude=geo.latitude,
            longitude=geo.longitude,
            organization=geo.organization,
            asn=geo.asn,
            tls_version=raw.tls_version,
            bytes_sent=raw.bytes_sent,
            bytes_received=raw.bytes_received,
            latency_ms=raw.latency_ms,
        )

    @property
    def processed_count(self) -> int:
        """Total events processed by this pipeline."""
        return self._processed_count

    @property
    def queue_size(self) -> int:
        """Current number of events waiting in the queue."""
        return self._queue.qsize()
