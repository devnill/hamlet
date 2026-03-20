"""Tests for EventProcessor (work item 082).

Test framework: pytest + pytest-asyncio (see pyproject.toml dev dependencies).
Run with: pytest tests/test_event_processor.py -v
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from hamlet.event_processing.event_processor import EventProcessor, _REQUIRED_FIELDS
from hamlet.event_processing.internal_event import HookType, InternalEvent


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def event_queue() -> asyncio.Queue[dict[str, Any]]:
    """Return an empty asyncio Queue for testing."""
    return asyncio.Queue()


@pytest.fixture
def processor(event_queue: asyncio.Queue[dict[str, Any]]) -> EventProcessor:
    """Return an EventProcessor with mocked dependencies."""
    return EventProcessor(event_queue)


@pytest.fixture
def mock_handlers() -> dict[str, MagicMock]:
    """Return a dict of mocked handler objects with required methods."""
    # Create mocks with the specific methods that _route_event checks for
    world_state = MagicMock()
    world_state.handle_event = AsyncMock()

    agent_inference = MagicMock()
    agent_inference.process_event = AsyncMock()

    persistence = MagicMock()
    persistence.log_event = AsyncMock()

    return {
        "world_state": world_state,
        "agent_inference": agent_inference,
        "persistence": persistence,
    }


@pytest.fixture
def valid_raw_event() -> dict[str, Any]:
    """Return a minimal valid raw event dict."""
    return {
        "session_id": str(uuid4()),
        "project_id": "proj-1",
        "hook_type": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/test.txt"},
    }


# -----------------------------------------------------------------------------
# Test Class: TestEventProcessor
# -----------------------------------------------------------------------------

class TestEventProcessor:
    """Tests for EventProcessor class."""

    # -------------------------------------------------------------------------
    # AC-2: test_process_event_validates_required_fields
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_process_event_validates_required_fields(
        self,
        processor: EventProcessor,
    ) -> None:
        """process_event raises ValueError when required fields are missing or empty."""
        # Test missing each required field
        for field in _REQUIRED_FIELDS:
            raw_event: dict[str, Any] = {
                "session_id": str(uuid4()),
                "project_id": "proj-1",
                "hook_type": "PreToolUse",
            }
            del raw_event[field]

            with pytest.raises(ValueError) as exc_info:
                await processor.process_event(raw_event)
            assert f"missing required field '{field}'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_event_validates_empty_required_fields(
        self,
        processor: EventProcessor,
    ) -> None:
        """process_event raises ValueError when required fields are empty strings."""
        for field in _REQUIRED_FIELDS:
            raw_event: dict[str, Any] = {
                "session_id": str(uuid4()),
                "project_id": "proj-1",
                "hook_type": "PreToolUse",
            }
            raw_event[field] = ""

            with pytest.raises(ValueError) as exc_info:
                await processor.process_event(raw_event)
            assert f"missing required field '{field}'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_event_validates_unknown_hook_type(
        self,
        processor: EventProcessor,
    ) -> None:
        """process_event raises ValueError for unknown hook_type values."""
        raw_event: dict[str, Any] = {
            "session_id": str(uuid4()),
            "project_id": "proj-1",
            "hook_type": "UnknownHookType",
        }

        with pytest.raises(ValueError) as exc_info:
            await processor.process_event(raw_event)
        assert "Unknown hook_type" in str(exc_info.value)

    # -------------------------------------------------------------------------
    # AC-3: test_route_event_calls_all_handlers
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_route_event_calls_all_handlers(
        self,
        processor: EventProcessor,
        mock_handlers: dict[str, MagicMock],
    ) -> None:
        """_route_event calls all registered handlers concurrently."""
        # Set up mock handlers on the processor
        processor._world_state = mock_handlers["world_state"]
        processor._agent_inference = mock_handlers["agent_inference"]
        processor._persistence = mock_handlers["persistence"]

        # Create a test event
        event = InternalEvent(
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

        # Call _route_event
        await processor._route_event(event)

        # Verify all handlers were called (using the specific methods)
        mock_handlers["world_state"].handle_event.assert_awaited_once_with(event)
        mock_handlers["agent_inference"].process_event.assert_awaited_once_with(event)
        mock_handlers["persistence"].log_event.assert_awaited_once_with(event)

    @pytest.mark.asyncio
    async def test_route_event_calls_subscribers(
        self,
        processor: EventProcessor,
    ) -> None:
        """_route_event calls all subscribed callbacks."""
        # Create mock subscribers
        subscriber1 = AsyncMock()
        subscriber2 = AsyncMock()

        # Subscribe them
        await processor.subscribe(subscriber1)
        await processor.subscribe(subscriber2)

        # Create a test event
        event = InternalEvent(
            id=str(uuid4()),
            sequence=1,
            received_at=datetime.now(UTC),
            session_id=str(uuid4()),
            project_id="proj-1",
            project_name="test-project",
            hook_type=HookType.PreToolUse,
        )

        # Call _route_event
        await processor._route_event(event)

        # Verify subscribers were called
        subscriber1.assert_awaited_once_with(event)
        subscriber2.assert_awaited_once_with(event)

    # -------------------------------------------------------------------------
    # AC-4: test_route_event_error_in_handler_logged - GP-7
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_route_event_error_in_handler_logged(
        self,
        processor: EventProcessor,
        mock_handlers: dict[str, MagicMock],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Errors in handlers are logged, not raised (GP-7)."""
        # Set up one handler to raise an exception
        mock_handlers["world_state"].handle_event.side_effect = Exception("boom")
        mock_handlers["agent_inference"].process_event.return_value = None
        mock_handlers["persistence"].log_event.return_value = None

        # Set up mock handlers on the processor
        processor._world_state = mock_handlers["world_state"]
        processor._agent_inference = mock_handlers["agent_inference"]
        processor._persistence = mock_handlers["persistence"]

        # Create a test event
        event = InternalEvent(
            id=str(uuid4()),
            sequence=1,
            received_at=datetime.now(UTC),
            session_id=str(uuid4()),
            project_id="proj-1",
            project_name="test-project",
            hook_type=HookType.PreToolUse,
        )

        # Call _route_event - should not raise
        with caplog.at_level(logging.ERROR, logger="hamlet.event_processing.event_processor"):
            await processor._route_event(event)

        # Verify error was logged
        assert "Error routing event" in caplog.text
        assert "boom" in caplog.text

        # Verify other handlers were still called
        mock_handlers["agent_inference"].process_event.assert_awaited_once()
        mock_handlers["persistence"].log_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_route_event_subscriber_error_logged(
        self,
        processor: EventProcessor,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Errors in subscriber callbacks are logged, not raised (GP-7)."""
        # Create a subscriber that raises an exception
        failing_subscriber = AsyncMock(side_effect=Exception("subscriber error"))
        working_subscriber = AsyncMock()

        # Subscribe them
        await processor.subscribe(failing_subscriber)
        await processor.subscribe(working_subscriber)

        # Create a test event
        event = InternalEvent(
            id=str(uuid4()),
            sequence=1,
            received_at=datetime.now(UTC),
            session_id=str(uuid4()),
            project_id="proj-1",
            project_name="test-project",
            hook_type=HookType.PreToolUse,
        )

        # Call _route_event - should not raise
        with caplog.at_level(logging.ERROR, logger="hamlet.event_processing.event_processor"):
            await processor._route_event(event)

        # Verify error was logged
        assert "Error routing event" in caplog.text
        assert "subscriber error" in caplog.text

        # Verify working subscriber was still called
        working_subscriber.assert_awaited_once_with(event)

    # -------------------------------------------------------------------------
    # AC-5: test_consume_loop_processes_queue
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_consume_loop_processes_queue(
        self,
        event_queue: asyncio.Queue[dict[str, Any]],
        valid_raw_event: dict[str, Any],
    ) -> None:
        """_consume_loop processes events from the queue."""
        processor = EventProcessor(event_queue)

        # Put an event in the queue
        await event_queue.put(valid_raw_event)

        # Start the processor
        await processor.start()

        # Wait a bit for the event to be processed
        await asyncio.sleep(0.1)

        # Stop the processor
        await processor.stop()

        # Verify the queue is empty (event was processed)
        assert event_queue.empty()

    @pytest.mark.asyncio
    async def test_consume_loop_processes_multiple_events(
        self,
        event_queue: asyncio.Queue[dict[str, Any]],
        valid_raw_event: dict[str, Any],
    ) -> None:
        """_consume_loop processes multiple events from the queue."""
        processor = EventProcessor(event_queue)

        # Create a mock to track processed events
        processed_events: list[InternalEvent] = []

        async def tracking_callback(event: InternalEvent) -> None:
            processed_events.append(event)

        await processor.subscribe(tracking_callback)

        # Put multiple events in the queue
        for _ in range(3):
            await event_queue.put(dict(valid_raw_event))

        # Start the processor
        await processor.start()

        # Wait for events to be processed
        await asyncio.sleep(0.2)

        # Stop the processor
        await processor.stop()

        # Verify all events were processed
        assert len(processed_events) == 3
        assert event_queue.empty()

    @pytest.mark.asyncio
    async def test_consume_loop_handles_invalid_events(
        self,
        event_queue: asyncio.Queue[dict[str, Any]],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """_consume_loop logs errors for invalid events but continues processing."""
        processor = EventProcessor(event_queue)

        # Put an invalid event (missing required field)
        invalid_event: dict[str, Any] = {"session_id": str(uuid4())}  # Missing project_id and hook_type

        # Put a valid event
        valid_event: dict[str, Any] = {
            "session_id": str(uuid4()),
            "project_id": "proj-1",
            "hook_type": "PreToolUse",
        }

        await event_queue.put(invalid_event)
        await event_queue.put(valid_event)

        # Start the processor
        await processor.start()

        # Wait for events to be processed
        await asyncio.sleep(0.2)

        # Stop the processor
        await processor.stop()

        # Verify the queue is empty and error was logged
        assert event_queue.empty()
        assert "Failed to process event" in caplog.text

    # -------------------------------------------------------------------------
    # Additional tests for process_event
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_process_event_returns_internal_event(
        self,
        processor: EventProcessor,
        valid_raw_event: dict[str, Any],
    ) -> None:
        """process_event returns a properly formed InternalEvent."""
        result = await processor.process_event(valid_raw_event)

        assert isinstance(result, InternalEvent)
        assert result.session_id == valid_raw_event["session_id"]
        assert result.project_id == valid_raw_event["project_id"]
        assert result.hook_type == HookType.PreToolUse
        assert result.tool_name == valid_raw_event["tool_name"]
        assert result.tool_input == valid_raw_event["tool_input"]
        assert result.sequence > 0
        assert result.id is not None
        assert result.received_at is not None

    @pytest.mark.asyncio
    async def test_process_event_assigns_sequence_numbers(
        self,
        processor: EventProcessor,
        valid_raw_event: dict[str, Any],
    ) -> None:
        """process_event assigns incrementing sequence numbers."""
        result1 = await processor.process_event(valid_raw_event)
        result2 = await processor.process_event(valid_raw_event)

        assert result2.sequence == result1.sequence + 1

    @pytest.mark.asyncio
    async def test_process_event_uses_project_id_as_default_project_name(
        self,
        processor: EventProcessor,
        valid_raw_event: dict[str, Any],
    ) -> None:
        """process_event uses project_id as project_name when project_name is not provided."""
        result = await processor.process_event(valid_raw_event)

        assert result.project_name == valid_raw_event["project_id"]

    @pytest.mark.asyncio
    async def test_process_event_uses_provided_project_name(
        self,
        processor: EventProcessor,
        valid_raw_event: dict[str, Any],
    ) -> None:
        """process_event uses provided project_name when available."""
        valid_raw_event["project_name"] = "My Project"
        result = await processor.process_event(valid_raw_event)

        assert result.project_name == "My Project"
