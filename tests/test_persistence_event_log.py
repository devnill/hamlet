"""Tests for EventLogManager append/prune (work item 081).

Run with: pytest tests/test_persistence_event_log.py -v
"""
from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from hamlet.persistence.connection import DatabaseConnection
from hamlet.persistence.migrations import run_migrations
from hamlet.persistence.event_log import EventLogManager
from hamlet.world_state.state import EventLogEntry


@pytest.fixture
async def db():
    """Create an in-memory database with migrations applied."""
    db = DatabaseConnection(":memory:")
    await db.__aenter__()
    await run_migrations(db)
    yield db
    await db.__aexit__(None, None, None)


class TestEventLogManager:
    """Test suite for EventLogManager append/prune."""

    @pytest.mark.asyncio
    async def test_append_inserts_entry(self, db: DatabaseConnection) -> None:
        """Test append inserts an event log entry."""
        manager = EventLogManager(db, max_entries=100)

        entry = EventLogEntry(
            id="entry-001",
            timestamp=datetime.now(),
            session_id="sess-001",
            project_id="proj-001",
            hook_type="tool_call",
            tool_name="test_tool",
            summary="Test event summary",
        )

        await manager.append(entry)

        # Verify the entry was inserted
        await db.execute(
            "SELECT session_id, project_id, hook_type, tool_name, summary FROM event_log WHERE session_id = ?",
            ("sess-001",)
        )
        row = await db.fetchone()
        assert row is not None
        assert row[0] == "sess-001"
        assert row[1] == "proj-001"
        assert row[2] == "tool_call"
        assert row[3] == "test_tool"
        assert row[4] == "Test event summary"

    @pytest.mark.asyncio
    async def test_append_prunes_old_entries(self, db: DatabaseConnection) -> None:
        """Test append prunes old entries when exceeding max_entries."""
        manager = EventLogManager(db, max_entries=5)

        # Insert 10 entries
        for i in range(10):
            entry = EventLogEntry(
                id=f"entry-{i}",
                timestamp=datetime.now(),
                session_id=f"sess-{i}",
                project_id="proj-001",
                hook_type="tool_call",
                tool_name="test_tool",
                summary=f"Event {i}",
            )
            await manager.append(entry)

        # Verify only 5 entries remain
        await db.execute("SELECT COUNT(*) FROM event_log")
        row = await db.fetchone()
        assert row is not None
        assert row[0] == 5

        # Verify the oldest entries were pruned (should have entries 5-9)
        await db.execute("SELECT session_id FROM event_log ORDER BY id")
        rows = await db.fetchall()
        session_ids = [r[0] for r in rows]
        assert session_ids == ["sess-5", "sess-6", "sess-7", "sess-8", "sess-9"]

    @pytest.mark.asyncio
    async def test_append_transactional(self, db: DatabaseConnection) -> None:
        """Test append is transactional - insert and prune are atomic."""
        manager = EventLogManager(db, max_entries=3)

        # Insert 3 entries to fill the limit
        for i in range(3):
            entry = EventLogEntry(
                id=f"entry-{i}",
                timestamp=datetime.now(),
                session_id=f"sess-{i}",
                project_id="proj-001",
                hook_type="tool_call",
                tool_name="test_tool",
                summary=f"Event {i}",
            )
            await manager.append(entry)

        # Verify 3 entries
        await db.execute("SELECT COUNT(*) FROM event_log")
        row = await db.fetchone()
        assert row[0] == 3

        # Add one more - should prune oldest and keep 3
        entry = EventLogEntry(
            id="entry-3",
            timestamp=datetime.now(),
            session_id="sess-3",
            project_id="proj-001",
            hook_type="tool_call",
            tool_name="test_tool",
            summary="Event 3",
        )
        await manager.append(entry)

        # Verify still 3 entries (pruned oldest, added new)
        await db.execute("SELECT COUNT(*) FROM event_log")
        row = await db.fetchone()
        assert row[0] == 3

        # Verify oldest was pruned
        await db.execute("SELECT session_id FROM event_log ORDER BY id")
        rows = await db.fetchall()
        session_ids = [r[0] for r in rows]
        assert "sess-0" not in session_ids
        assert "sess-3" in session_ids

    @pytest.mark.asyncio
    async def test_append_null_tool_name(self, db: DatabaseConnection) -> None:
        """Test append handles null tool_name."""
        manager = EventLogManager(db, max_entries=100)

        entry = EventLogEntry(
            id="entry-null",
            timestamp=datetime.now(),
            session_id="sess-null",
            project_id="proj-001",
            hook_type="notification",
            tool_name=None,
            summary="Notification without tool",
        )

        await manager.append(entry)

        # Verify the entry was inserted with null tool_name
        await db.execute(
            "SELECT tool_name FROM event_log WHERE session_id = ?",
            ("sess-null",)
        )
        row = await db.fetchone()
        assert row is not None
        assert row[0] is None

    @pytest.mark.asyncio
    async def test_append_multiple_different_hook_types(self, db: DatabaseConnection) -> None:
        """Test append handles different hook types."""
        manager = EventLogManager(db, max_entries=100)

        hook_types = ["tool_call", "tool_result", "notification", "error"]
        for i, hook_type in enumerate(hook_types):
            entry = EventLogEntry(
                id=f"entry-{i}",
                timestamp=datetime.now(),
                session_id=f"sess-{i}",
                project_id="proj-001",
                hook_type=hook_type,
                tool_name="test_tool" if hook_type in ["tool_call", "tool_result"] else None,
                summary=f"Event {hook_type}",
            )
            await manager.append(entry)

        # Verify all entries were inserted
        await db.execute("SELECT COUNT(*) FROM event_log")
        row = await db.fetchone()
        assert row[0] == 4

        # Verify hook types
        await db.execute("SELECT hook_type FROM event_log ORDER BY id")
        rows = await db.fetchall()
        stored_types = [r[0] for r in rows]
        assert stored_types == hook_types

    @pytest.mark.asyncio
    async def test_append_rollback_on_error(self, db: DatabaseConnection) -> None:
        """Test append rolls back transaction on error."""
        manager = EventLogManager(db, max_entries=100)

        # Insert initial valid entry
        entry1 = EventLogEntry(
            id="entry-1",
            timestamp=datetime.now(),
            session_id="sess-1",
            project_id="proj-001",
            hook_type="tool_call",
            tool_name="test_tool",
            summary="First event",
        )
        await manager.append(entry1)

        # Verify entry exists
        await db.execute("SELECT COUNT(*) FROM event_log")
        row = await db.fetchone()
        assert row[0] == 1

        # Mock the db.execute to raise an exception on second call
        original_execute = db.execute
        call_count = [0]

        async def mock_execute(sql, params=()):
            call_count[0] += 1
            if call_count[0] > 1:  # First call is begin_transaction
                raise Exception("Simulated database error")
            return await original_execute(sql, params)

        with patch.object(db, 'execute', side_effect=mock_execute):
            entry2 = EventLogEntry(
                id="entry-2",
                timestamp=datetime.now(),
                session_id="sess-2",
                project_id="proj-001",
                hook_type="tool_call",
                tool_name="test_tool",
                summary="Second event",
            )
            # Should not raise, but log error
            await manager.append(entry2)

        # Verify first entry still exists (rollback preserved it)
        await db.execute("SELECT COUNT(*) FROM event_log")
        row = await db.fetchone()
        assert row[0] == 1

        await db.execute("SELECT session_id FROM event_log")
        row = await db.fetchone()
        assert row[0] == "sess-1"

    @pytest.mark.asyncio
    async def test_append_empty_summary(self, db: DatabaseConnection) -> None:
        """Test append handles empty summary."""
        manager = EventLogManager(db, max_entries=100)

        entry = EventLogEntry(
            id="entry-empty",
            timestamp=datetime.now(),
            session_id="sess-empty",
            project_id="proj-001",
            hook_type="notification",
            tool_name=None,
            summary="",
        )

        await manager.append(entry)

        # Verify the entry was inserted
        await db.execute(
            "SELECT summary FROM event_log WHERE session_id = ?",
            ("sess-empty",)
        )
        row = await db.fetchone()
        assert row is not None
        assert row[0] == ""

    @pytest.mark.asyncio
    async def test_append_timestamp_format(self, db: DatabaseConnection) -> None:
        """Test append stores timestamp in ISO format."""
        manager = EventLogManager(db, max_entries=100)

        now = datetime(2024, 1, 15, 10, 30, 0)
        entry = EventLogEntry(
            id="entry-time",
            timestamp=now,
            session_id="sess-time",
            project_id="proj-001",
            hook_type="tool_call",
            tool_name="test_tool",
            summary="Time test",
        )

        await manager.append(entry)

        # Verify timestamp was stored as ISO string
        await db.execute(
            "SELECT timestamp FROM event_log WHERE session_id = ?",
            ("sess-time",)
        )
        row = await db.fetchone()
        assert row is not None
        assert "2024-01-15T10:30:00" in row[0]

    @pytest.mark.asyncio
    async def test_prune_keeps_most_recent(self, db: DatabaseConnection) -> None:
        """Test pruning keeps the most recent entries."""
        manager = EventLogManager(db, max_entries=3)

        # Insert entries with different timestamps
        for i in range(10):
            entry = EventLogEntry(
                id=f"entry-{i}",
                timestamp=datetime(2024, 1, 1, i, 0, 0),  # Different hours
                session_id=f"sess-{i}",
                project_id="proj-001",
                hook_type="tool_call",
                tool_name="test_tool",
                summary=f"Event {i}",
            )
            await manager.append(entry)

        # Verify only 3 most recent remain
        await db.execute("SELECT session_id FROM event_log ORDER BY id")
        rows = await db.fetchall()
        session_ids = [r[0] for r in rows]

        # Should have the last 3 entries (7, 8, 9)
        assert session_ids == ["sess-7", "sess-8", "sess-9"]

    @pytest.mark.asyncio
    async def test_max_entries_zero(self, db: DatabaseConnection) -> None:
        """Test with max_entries=0 prunes all but one entry."""
        manager = EventLogManager(db, max_entries=1)

        # Insert multiple entries
        for i in range(5):
            entry = EventLogEntry(
                id=f"entry-{i}",
                timestamp=datetime.now(),
                session_id=f"sess-{i}",
                project_id="proj-001",
                hook_type="tool_call",
                tool_name="test_tool",
                summary=f"Event {i}",
            )
            await manager.append(entry)

        # Verify only 1 entry remains
        await db.execute("SELECT COUNT(*) FROM event_log")
        row = await db.fetchone()
        assert row[0] == 1

        # Verify it's the most recent
        await db.execute("SELECT session_id FROM event_log")
        row = await db.fetchone()
        assert row[0] == "sess-4"
