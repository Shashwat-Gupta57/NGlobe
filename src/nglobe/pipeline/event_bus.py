"""Event bus — pub/sub fan-out for NetworkEvent distribution.

The EventBus receives enriched NetworkEvent objects from the EventPipeline
and distributes them to all subscribers (BatchWriter, WebSocketManager).
"""

from __future__ import annotations

import asyncio
from typing import Callable, Awaitable

from nglobe.models import NetworkEvent
from nglobe.utils.logging import get_logger

logger = get_logger(__name__)

# Subscriber type: async callable that accepts a NetworkEvent
Subscriber = Callable[[NetworkEvent], Awaitable[None]]


class EventBus:
    """Asynchronous pub/sub event bus for NetworkEvent distribution.

    Subscribers are async callables. Publishing fans out to all
    subscribers concurrently. Subscriber failures are logged but
    don't block other subscribers.
    """

    def __init__(self) -> None:
        self._subscribers: list[Subscriber] = []
        self._event_count = 0

    def subscribe(self, callback: Subscriber) -> None:
        """Register a subscriber to receive NetworkEvent objects."""
        self._subscribers.append(callback)
        logger.info("event_bus_subscriber_added", total=len(self._subscribers))

    def unsubscribe(self, callback: Subscriber) -> None:
        """Remove a subscriber."""
        self._subscribers = [s for s in self._subscribers if s is not callback]
        logger.info("event_bus_subscriber_removed", total=len(self._subscribers))

    async def publish(self, event: NetworkEvent) -> None:
        """Publish an event to all subscribers concurrently."""
        self._event_count += 1
        logger.debug("event_bus_publishing", host=event.hostname, subs=len(self._subscribers))

        if not self._subscribers:
            return

        tasks = [
            asyncio.create_task(self._safe_deliver(sub, event))
            for sub in self._subscribers
        ]
        await asyncio.gather(*tasks)

    async def _safe_deliver(self, subscriber: Subscriber, event: NetworkEvent) -> None:
        """Deliver event to a subscriber with error isolation."""
        try:
            await subscriber(event)
        except Exception as e:
            logger.error(
                "event_bus_delivery_error",
                subscriber=str(subscriber),
                error=str(e),
            )

    @property
    def event_count(self) -> int:
        """Total events published through this bus."""
        return self._event_count

    @property
    def subscriber_count(self) -> int:
        """Number of active subscribers."""
        return len(self._subscribers)
