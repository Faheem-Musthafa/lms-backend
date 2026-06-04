"""In-process async event bus.

``event_bus.publish(event)`` fans out to every subscriber registered for the
event's type (and its base types). Handler errors are isolated and logged — a
failing consumer never breaks the publisher.

Outbox-ready: the public surface is ``publish`` / ``subscribe``. To move to
durable delivery (transactional outbox → Redis Streams) later, swap this
dispatcher's body; publishers and consumers stay unchanged.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.events.base import DomainEvent

logger = logging.getLogger("events")

EventT = TypeVar("EventT", bound=DomainEvent)
Handler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def _resolve(self, event: DomainEvent) -> list[Handler]:
        handlers: list[Handler] = []
        for etype, hs in self._handlers.items():
            if isinstance(event, etype):
                handlers.extend(hs)
        return handlers

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._resolve(event)
        if not handlers:
            return
        results = await asyncio.gather(*(h(event) for h in handlers), return_exceptions=True)
        for handler, result in zip(handlers, results, strict=True):
            if isinstance(result, Exception):
                logger.exception(
                    "event handler failed: %s for %s",
                    getattr(handler, "__qualname__", handler),
                    event.name,
                    exc_info=result,
                )

    def clear(self) -> None:
        self._handlers.clear()


event_bus = EventBus()


def subscribe(event_type: type[EventT]) -> Callable[[Handler], Handler]:
    """Decorator: register a coroutine as a handler for an event type."""

    def decorator(handler: Handler) -> Handler:
        event_bus.subscribe(event_type, handler)
        return handler

    return decorator
