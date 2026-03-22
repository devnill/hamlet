"""Tests for PersistenceFacade lifecycle and operations (work item 080).

Run with: pytest tests/test_persistence_facade.py -v
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hamlet.event_processing.internal_event import HookType, InternalEvent
from hamlet.persistence.facade import PersistenceFacade
from hamlet.persistence.types import PersistenceConfig, WriteOperation
from hamlet.world_state.state import EventLogEntry


class TestPersistenceFacade:
    """Test suite for PersistenceFacade lifecycle and operations."""

    @pytest.fixture
    def config(self) -> PersistenceConfig:
        """Return a test persistence config."""
        return PersistenceConfig(db_path=":memory:", write_queue_size=100)

    @pytest.fixture
    def facade(self, config: PersistenceConfig) -> PersistenceFacade:
        """Return a PersistenceFacade with test config."""
        return PersistenceFacade(config)

    async def test_start_initializes_all_components(self, facade: PersistenceFacade) -> None:
        """start() initializes database, migrations, queue, and background loop."""
        with patch.object(facade, "_write_loop", new_callable=AsyncMock) as mock_loop:
            await facade.start()

            try:
                # Verify running state
                assert facade._running is True

                # Verify database connection initialized
                assert facade._db is not None

                # Verify write queue initialized
                assert facade._write_queue is not None

                # Verify write executor initialized
                assert facade._write_executor is not None

                # Verify state loader initialized
                assert facade._state_loader is not None

                # Verify event log manager initialized
                assert facade._event_log_manager is not None

                # Verify background task created
                assert facade._write_task is not None

            finally:
                await facade.stop()

    async def test_stop_drains_queue_and_closes_connection(self, facade: PersistenceFacade) -> None:
        """stop() cancels background loop and closes database connection."""
        await facade.start()

        # Verify started
        assert facade._running is True
        assert facade._db is not None

        await facade.stop()

        # Verify stopped state
        assert facade._running is False
        assert facade._db is None
        assert facade._write_queue is None
        assert facade._write_executor is None
        assert facade._state_loader is None
        assert facade._event_log_manager is None
        assert facade._write_task is None

    async def test_checkpoint_drains_and_wal_checkpoint(self, facade: PersistenceFacade) -> None:
        """checkpoint() drains queue and runs WAL checkpoint."""
        await facade.start()

        try:
            # Mock the write queue join
            with patch.object(facade._write_queue, "join", new_callable=AsyncMock) as mock_join:
                # Mock the database execute for WAL checkpoint
                with patch.object(facade._db, "execute", new_callable=AsyncMock) as mock_execute:
                    await facade.checkpoint()

                    # Verify queue was drained
                    mock_join.assert_called_once()

                    # Verify WAL checkpoint was executed
                    mock_execute.assert_called_once_with("PRAGMA wal_checkpoint")
        finally:
            await facade.stop()

    async def test_checkpoint_raises_when_not_running(self, facade: PersistenceFacade) -> None:
        """checkpoint() raises RuntimeError when facade not running."""
        with pytest.raises(RuntimeError, match="facade not running"):
            await facade.checkpoint()

    async def test_enqueue_write_adds_operation(self, facade: PersistenceFacade) -> None:
        """enqueue_write() adds operation to the write queue."""
        await facade.start()

        try:
            # Create a test operation
            operation = WriteOperation(
                entity_type="agent",
                entity_id="agent-1",
                operation="insert",
                data={"name": "Test Agent"},
            )

            # Initial queue size
            initial_size = facade._write_queue.qsize()

            # Enqueue the operation
            facade.enqueue_write(operation)

            # Verify operation was added
            assert facade._write_queue.qsize() == initial_size + 1
        finally:
            await facade.stop()

    async def test_enqueue_write_drops_when_full(self, facade: PersistenceFacade) -> None:
        """enqueue_write() silently drops operations when queue is full per GP-7."""
        # Use a very small queue
        config = PersistenceConfig(db_path=":memory:", write_queue_size=1)
        facade = PersistenceFacade(config)

        await facade.start()

        try:
            # Create operations
            operation1 = WriteOperation(
                entity_type="agent",
                entity_id="agent-1",
                operation="insert",
                data={},
            )
            operation2 = WriteOperation(
                entity_type="agent",
                entity_id="agent-2",
                operation="insert",
                data={},
            )

            # Fill the queue (don't process anything)
            with patch.object(facade._write_queue, "get_batch", new_callable=AsyncMock) as mock_get_batch:
                mock_get_batch.return_value = []  # Return empty to prevent processing

                # Enqueue first operation (should succeed)
                facade.enqueue_write(operation1)

                # Capture log output
                with patch("hamlet.persistence.facade.logger") as mock_logger:
                    # Enqueue second operation (should be dropped silently)
                    facade.enqueue_write(operation2)

                    # Verify drop was logged per GP-7
                    mock_logger.debug.assert_called_with("Write queue full, dropping operation")
        finally:
            await facade.stop()

    async def test_enqueue_write_raises_when_not_running(self, facade: PersistenceFacade) -> None:
        """enqueue_write() raises RuntimeError when facade not running."""
        operation = WriteOperation(
            entity_type="agent",
            entity_id="agent-1",
            operation="insert",
            data={},
        )

        with pytest.raises(RuntimeError, match="facade not running"):
            facade.enqueue_write(operation)

    async def test_load_state_raises_when_not_started(self, facade: PersistenceFacade) -> None:
        """load_state() raises RuntimeError when facade not started."""
        with pytest.raises(RuntimeError, match="facade not started"):
            await facade.load_state()

    async def test_start_is_idempotent(self, facade: PersistenceFacade) -> None:
        """start() is idempotent when already running."""
        await facade.start()

        try:
            # Calling start again should not raise or create duplicate resources
            await facade.start()

            assert facade._running is True
        finally:
            await facade.stop()

    async def test_stop_is_idempotent(self, facade: PersistenceFacade) -> None:
        """stop() is idempotent when not running."""
        # Calling stop before start should not raise
        await facade.stop()

    async def test_log_event_delegates_to_append_event_log(self, facade: PersistenceFacade) -> None:
        """log_event() constructs EventLogEntry and delegates to append_event_log."""
        event = InternalEvent(
            id="evt-001",
            sequence=1,
            received_at=datetime(2026, 1, 1, tzinfo=UTC),
            session_id="sess-abc",
            project_id="proj-123",
            project_name="TestProject",
            hook_type=HookType.PreToolUse,
            tool_name="Bash",
        )

        captured: list[EventLogEntry] = []

        async def fake_append(entry: EventLogEntry) -> None:
            captured.append(entry)

        facade.append_event_log = fake_append  # type: ignore[method-assign]

        await facade.log_event(event)

        assert len(captured) == 1
        entry = captured[0]
        assert entry.id == "evt-001"
        assert entry.session_id == "sess-abc"
        assert entry.project_id == "proj-123"
        assert entry.hook_type == "PreToolUse"
        assert entry.tool_name == "Bash"
        assert entry.summary == "PreToolUse: Bash"

    async def test_log_event_swallows_exceptions(self, facade: PersistenceFacade) -> None:
        """log_event() propagates exceptions from append_event_log (GP-7)."""
        event = InternalEvent(
            id="evt-002",
            sequence=2,
            received_at=datetime(2026, 1, 1, tzinfo=UTC),
            session_id="sess-abc",
            project_id="proj-123",
            project_name="TestProject",
            hook_type=HookType.PostToolUse,
            tool_name=None,
        )

        async def failing_append(entry: EventLogEntry) -> None:
            raise RuntimeError("DB unavailable")

        facade.append_event_log = failing_append  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="DB unavailable"):
            await facade.log_event(event)

    async def test_delete_agent_queues_delete_operation(self, facade: PersistenceFacade) -> None:
        """delete_agent() enqueues a delete WriteOperation for the agent."""
        await facade.start()

        try:
            agent_id = "agent-to-delete"
            initial_size = facade._write_queue.qsize()

            await facade.delete_agent(agent_id)

            # Verify one item was enqueued
            assert facade._write_queue.qsize() == initial_size + 1

            # Drain and inspect the operation
            batch = await facade._write_queue.get_batch(max_items=10)
            assert len(batch) == 1
            op = batch[0]
            assert op.entity_type == "agent"
            assert op.entity_id == agent_id
            assert op.operation == "delete"
        finally:
            await facade.stop()

    async def test_delete_agent_raises_when_not_running(self, facade: PersistenceFacade) -> None:
        """delete_agent() raises RuntimeError when facade is not running."""
        with pytest.raises(RuntimeError, match="facade not running"):
            await facade.delete_agent("agent-x")

    async def test_stop_drains_queue_before_cancelling_task(self, facade: PersistenceFacade) -> None:
        """stop() awaits queue.join() before cancelling the background write task."""
        await facade.start()

        call_order: list[str] = []
        original_join = facade._write_queue.join

        async def tracking_join() -> None:
            call_order.append("join")
            await original_join()

        original_cancel = facade._write_task.cancel  # type: ignore[union-attr]

        def tracking_cancel(*args: object, **kwargs: object) -> bool:
            call_order.append("cancel")
            return original_cancel(*args, **kwargs)

        with patch.object(facade._write_queue, "join", side_effect=tracking_join):
            with patch.object(facade._write_task, "cancel", side_effect=tracking_cancel):
                await facade.stop()

        assert "join" in call_order, "queue.join() was not awaited"
        assert "cancel" in call_order, "task.cancel() was not called"
        assert call_order.index("join") < call_order.index("cancel"), (
            "queue.join() must be called before task.cancel()"
        )
        assert facade._write_task is None
        assert facade._running is False
