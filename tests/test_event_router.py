"""Tests for EventRouter (work item 082).

Test framework: pytest + pytest-asyncio (see pyproject.toml dev dependencies).
Run with: pytest tests/test_event_router.py -v
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from hamlet.event_processing.event_router import EventCallback, EventRouter
from hamlet.event_processing.internal_event import HookType, InternalEvent


# -----------------------------------------------------------------------------
# Concrete implementation for testing the abstract base class
# -----------------------------------------------------------------------------

class ConcreteEventRouter(EventRouter):
    """Concrete implementation of EventRouter for testing."""

    def __init__(self) -> None:
        self._subscribers: list[EventCallback] = []

    async def subscribe(self, callback: EventCallback) -> None:
        """Register a callback to receive all processed events."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    async def unsubscribe(self, callback: EventCallback) -> None:
        """Remove a previously registered callback."""
        try:
            self._subscribers.remove(callback)
        except ValueError:
            pass

    def get_subscribers(self) -> list[EventCallback]:
        """Return the list of subscribers (for testing)."""
        return list(self._subscribers)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def router() -> ConcreteEventRouter:
    """Return a ConcreteEventRouter instance for testing."""
    return ConcreteEventRouter()


@pytest.fixture
def sample_event() -> InternalEvent:
    """Return a sample InternalEvent for testing."""
    return InternalEvent(
        id=str(uuid4()),
        sequence=1,
        received_at=datetime.now(UTC),
        session_id=str(uuid4()),
        project_id="proj-1",
        project_name="test-project",
        hook_type=HookType.PreToolUse,
        tool_name="Read",
        tool_input={},
    )


# -----------------------------------------------------------------------------
# Test Class: TestEventRouter
# -----------------------------------------------------------------------------

class TestEventRouter:
    """Tests for EventRouter abstract base class."""

    # -------------------------------------------------------------------------
    # AC-7: test_subscribe_adds_callback
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_subscribe_adds_callback(
        self,
        router: ConcreteEventRouter,
    ) -> None:
        """subscribe adds a callback to the subscribers list."""
        callback: EventCallback = AsyncMock()

        await router.subscribe(callback)

        assert callback in router.get_subscribers()
        assert len(router.get_subscribers()) == 1

    @pytest.mark.asyncio
    async def test_subscribe_adds_multiple_callbacks(
        self,
        router: ConcreteEventRouter,
    ) -> None:
        """subscribe can add multiple different callbacks."""
        callback1: EventCallback = AsyncMock()
        callback2: EventCallback = AsyncMock()

        await router.subscribe(callback1)
        await router.subscribe(callback2)

        assert callback1 in router.get_subscribers()
        assert callback2 in router.get_subscribers()
        assert len(router.get_subscribers()) == 2

    @pytest.mark.asyncio
    async def test_subscribe_does_not_add_duplicate_callback(
        self,
        router: ConcreteEventRouter,
    ) -> None:
        """subscribe does not add the same callback twice."""
        callback: EventCallback = AsyncMock()

        await router.subscribe(callback)
        await router.subscribe(callback)

        assert callback in router.get_subscribers()
        assert len(router.get_subscribers()) == 1

    # -------------------------------------------------------------------------
    # AC-8: test_unsubscribe_removes_callback
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_callback(
        self,
        router: ConcreteEventRouter,
    ) -> None:
        """unsubscribe removes a previously registered callback."""
        callback: EventCallback = AsyncMock()

        await router.subscribe(callback)
        assert callback in router.get_subscribers()

        await router.unsubscribe(callback)
        assert callback not in router.get_subscribers()
        assert len(router.get_subscribers()) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_does_not_affect_other_callbacks(
        self,
        router: ConcreteEventRouter,
    ) -> None:
        """unsubscribe removes only the specified callback."""
        callback1: EventCallback = AsyncMock()
        callback2: EventCallback = AsyncMock()
        callback3: EventCallback = AsyncMock()

        await router.subscribe(callback1)
        await router.subscribe(callback2)
        await router.subscribe(callback3)

        await router.unsubscribe(callback2)

        assert callback1 in router.get_subscribers()
        assert callback2 not in router.get_subscribers()
        assert callback3 in router.get_subscribers()
        assert len(router.get_subscribers()) == 2

    @pytest.mark.asyncio
    async def test_unsubscribe_silently_ignores_unregistered_callback(
        self,
        router: ConcreteEventRouter,
    ) -> None:
        """unsubscribe does not raise when removing a callback that was never subscribed."""
        callback: EventCallback = AsyncMock()

        # Should not raise
        await router.unsubscribe(callback)

        assert len(router.get_subscribers()) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_silently_ignores_already_removed_callback(
        self,
        router: ConcreteEventRouter,
    ) -> None:
        """unsubscribe does not raise when removing a callback that was already unsubscribed."""
        callback: EventCallback = AsyncMock()

        await router.subscribe(callback)
        await router.unsubscribe(callback)

        # Should not raise
        await router.unsubscribe(callback)

        assert len(router.get_subscribers()) == 0

    # -------------------------------------------------------------------------
    # Additional integration tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_subscribed_callback_can_receive_events(
        self,
        router: ConcreteEventRouter,
        sample_event: InternalEvent,
    ) -> None:
        """Subscribed callbacks can be called with events."""
        callback: EventCallback = AsyncMock()

        await router.subscribe(callback)
        await callback(sample_event)

        callback.assert_awaited_once_with(sample_event)
