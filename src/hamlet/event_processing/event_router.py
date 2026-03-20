"""Event router interface for the event processing pipeline."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from .internal_event import InternalEvent

# Type alias for event callbacks
EventCallback = Callable[[InternalEvent], Awaitable[None]]


class EventRouter(ABC):
    """Abstract interface for routing processed events to subscribers."""

    @abstractmethod
    async def subscribe(self, callback: EventCallback) -> None:
        """Register a callback to receive all processed events."""

    @abstractmethod
    async def unsubscribe(self, callback: EventCallback) -> None:
        """Remove a previously registered callback."""


__all__ = ["EventCallback", "EventRouter"]
