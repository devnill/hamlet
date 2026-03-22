"""Tests for WriteExecutor batch operations (work item 081).

Run with: pytest tests/test_persistence_writer.py -v
"""
from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from hamlet.persistence.connection import DatabaseConnection
from hamlet.persistence.migrations import run_migrations
from hamlet.persistence.writer import WriteExecutor
from hamlet.persistence.types import WriteOperation


@pytest.fixture
async def executor():
    """Create a WriteExecutor with an in-memory database."""
    db = DatabaseConnection(":memory:")
    await db.__aenter__()
    await run_migrations(db)
    yield WriteExecutor(db)
    await db.__aexit__(None, None, None)


class TestWriteExecutor:
    """Test suite for WriteExecutor batch operations."""

    @pytest.mark.asyncio
    async def test_execute_batch_project_insert(self, executor: WriteExecutor) -> None:
        """Test batch execution inserts project with config_json."""
        now = datetime.now().isoformat()
        operations = [
            WriteOperation(
                entity_type="project",
                entity_id="proj-001",
                operation="insert",
                data={
                    "id": "proj-001",
                    "name": "Test Project",
                    "config_json": {"key": "value", "number": 42},
                    "created_at": now,
                    "updated_at": now,
                },
            )
        ]

        await executor.execute_batch(operations)

        # Verify the project was inserted
        await executor._db.execute(
            "SELECT id, name, config_json FROM projects WHERE id = ?",
            ("proj-001",)
        )
        row = await executor._db.fetchone()
        assert row is not None
        assert row[0] == "proj-001"
        assert row[1] == "Test Project"
        # config_json should be stored as JSON string
        import json
        config = json.loads(row[2])
        assert config == {"key": "value", "number": 42}

    @pytest.mark.asyncio
    async def test_execute_batch_rollback_on_error(self, executor: WriteExecutor) -> None:
        """Test batch execution rolls back on error."""
        now = datetime.now().isoformat()

        # First insert a valid project
        await executor._db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("existing-proj", "Existing", "{}", now, now)
        )
        await executor._db.commit()

        # Create operations where the second one will fail (invalid data)
        operations = [
            WriteOperation(
                entity_type="project",
                entity_id="proj-002",
                operation="insert",
                data={
                    "id": "proj-002",
                    "name": "Should Not Exist",
                    "config_json": {},
                    "created_at": now,
                    "updated_at": now,
                },
            ),
            WriteOperation(
                entity_type="project",
                entity_id="proj-003",
                operation="insert",
                data={
                    "id": "proj-003",
                    "name": None,  # This will cause an error (NOT NULL constraint)
                    "config_json": {},
                    "created_at": now,
                    "updated_at": now,
                },
            ),
        ]

        # Execute batch - should fail but not raise
        await executor.execute_batch(operations)

        # Verify neither project was inserted (transaction rolled back)
        await executor._db.execute(
            "SELECT COUNT(*) FROM projects WHERE id IN (?, ?)",
            ("proj-002", "proj-003")
        )
        row = await executor._db.fetchone()
        assert row is not None
        assert row[0] == 0

        # Verify the existing project is still there
        await executor._db.execute(
            "SELECT id FROM projects WHERE id = ?",
            ("existing-proj",)
        )
        row = await executor._db.fetchone()
        assert row is not None
        assert row[0] == "existing-proj"

    @pytest.mark.asyncio
    async def test_execute_batch_session_insert(self, executor: WriteExecutor) -> None:
        """Test batch execution inserts session with agent_ids_json."""
        now = datetime.now().isoformat()

        # First create a project (required for foreign key)
        await executor._db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-session", "Session Test Project", "{}", now, now)
        )
        await executor._db.commit()

        operations = [
            WriteOperation(
                entity_type="session",
                entity_id="sess-001",
                operation="insert",
                data={
                    "id": "sess-001",
                    "project_id": "proj-session",
                    "started_at": now,
                    "last_activity": now,
                    "agent_ids_json": ["agent-1", "agent-2"],
                },
            )
        ]

        await executor.execute_batch(operations)

        # Verify the session was inserted
        await executor._db.execute(
            "SELECT id, project_id, agent_ids_json FROM sessions WHERE id = ?",
            ("sess-001",)
        )
        row = await executor._db.fetchone()
        assert row is not None
        assert row[0] == "sess-001"
        assert row[1] == "proj-session"
        import json
        agent_ids = json.loads(row[2])
        assert agent_ids == ["agent-1", "agent-2"]

    @pytest.mark.asyncio
    async def test_execute_batch_agent_insert(self, executor: WriteExecutor) -> None:
        """Test batch execution inserts agent with all fields."""
        now = datetime.now().isoformat()

        # Create required parent records
        await executor._db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-agent", "Agent Test Project", "{}", now, now)
        )
        await executor._db.execute(
            "INSERT INTO sessions (id, project_id, started_at, last_activity, agent_ids_json) VALUES (?, ?, ?, ?, ?)",
            ("sess-agent", "proj-agent", now, now, "[]")
        )
        await executor._db.execute(
            "INSERT INTO villages (id, project_id, name, center_x, center_y, bounds_min_x, bounds_min_y, bounds_max_x, bounds_max_y, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("village-agent", "proj-agent", "Test Village", 0, 0, -10, -10, 10, 10, now, now)
        )
        await executor._db.commit()

        operations = [
            WriteOperation(
                entity_type="agent",
                entity_id="agent-001",
                operation="insert",
                data={
                    "id": "agent-001",
                    "session_id": "sess-agent",
                    "village_id": "village-agent",
                    "parent_id": None,
                    "inferred_type": "builder",
                    "color": "blue",
                    "position_x": 5,
                    "position_y": 10,
                    "last_seen": now,
                    "state": "active",
                    "current_activity": "building",
                    "total_work_units": 100,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        ]

        await executor.execute_batch(operations)

        # Verify the agent was inserted
        await executor._db.execute(
            "SELECT id, session_id, village_id, inferred_type, color, position_x, position_y, state, current_activity, total_work_units FROM agents WHERE id = ?",
            ("agent-001",)
        )
        row = await executor._db.fetchone()
        assert row is not None
        assert row[0] == "agent-001"
        assert row[1] == "sess-agent"
        assert row[2] == "village-agent"
        assert row[3] == "builder"
        assert row[4] == "blue"
        assert row[5] == 5
        assert row[6] == 10
        assert row[7] == "active"
        assert row[8] == "building"
        assert row[9] == 100

    @pytest.mark.asyncio
    async def test_execute_batch_structure_insert(self, executor: WriteExecutor) -> None:
        """Test batch execution inserts structure with stage and material."""
        now = datetime.now().isoformat()

        # Create required parent records
        await executor._db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-struct", "Structure Test Project", "{}", now, now)
        )
        await executor._db.execute(
            "INSERT INTO villages (id, project_id, name, center_x, center_y, bounds_min_x, bounds_min_y, bounds_max_x, bounds_max_y, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("village-struct", "proj-struct", "Test Village", 0, 0, -10, -10, 10, 10, now, now)
        )
        await executor._db.commit()

        operations = [
            WriteOperation(
                entity_type="structure",
                entity_id="struct-001",
                operation="insert",
                data={
                    "id": "struct-001",
                    "village_id": "village-struct",
                    "type": "house",
                    "position_x": 3,
                    "position_y": 4,
                    "stage": 2,
                    "material": "stone",
                    "work_units": 50,
                    "work_required": 100,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        ]

        await executor.execute_batch(operations)

        # Verify the structure was inserted
        await executor._db.execute(
            "SELECT id, village_id, type, stage, material, work_units, work_required FROM structures WHERE id = ?",
            ("struct-001",)
        )
        row = await executor._db.fetchone()
        assert row is not None
        assert row[0] == "struct-001"
        assert row[1] == "village-struct"
        assert row[2] == "house"
        assert row[3] == 2
        assert row[4] == "stone"
        assert row[5] == 50
        assert row[6] == 100

    @pytest.mark.asyncio
    async def test_execute_batch_village_insert(self, executor: WriteExecutor) -> None:
        """Test batch execution inserts village with bounds."""
        now = datetime.now().isoformat()

        # Create required parent project
        await executor._db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-village", "Village Test Project", "{}", now, now)
        )
        await executor._db.commit()

        operations = [
            WriteOperation(
                entity_type="village",
                entity_id="village-001",
                operation="insert",
                data={
                    "id": "village-001",
                    "project_id": "proj-village",
                    "name": "Test Village",
                    "center_x": 0,
                    "center_y": 0,
                    "bounds_min_x": -50,
                    "bounds_min_y": -50,
                    "bounds_max_x": 50,
                    "bounds_max_y": 50,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        ]

        await executor.execute_batch(operations)

        # Verify the village was inserted
        await executor._db.execute(
            "SELECT id, project_id, name, center_x, center_y, bounds_min_x, bounds_min_y, bounds_max_x, bounds_max_y FROM villages WHERE id = ?",
            ("village-001",)
        )
        row = await executor._db.fetchone()
        assert row is not None
        assert row[0] == "village-001"
        assert row[1] == "proj-village"
        assert row[2] == "Test Village"
        assert row[3] == 0
        assert row[4] == 0
        assert row[5] == -50
        assert row[6] == -50
        assert row[7] == 50
        assert row[8] == 50

    @pytest.mark.asyncio
    async def test_execute_batch_delete_via_table_map(self, executor: WriteExecutor) -> None:
        """Test DELETE operations via _TABLE_MAP."""
        now = datetime.now().isoformat()

        # Insert a project first
        await executor._db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-delete", "Delete Test", "{}", now, now)
        )
        await executor._db.commit()

        # Verify it exists
        await executor._db.execute("SELECT id FROM projects WHERE id = ?", ("proj-delete",))
        row = await executor._db.fetchone()
        assert row is not None

        # Delete via WriteOperation
        operations = [
            WriteOperation(
                entity_type="project",
                entity_id="proj-delete",
                operation="delete",
                data={},
            )
        ]

        await executor.execute_batch(operations)

        # Verify it was deleted
        await executor._db.execute("SELECT id FROM projects WHERE id = ?", ("proj-delete",))
        row = await executor._db.fetchone()
        assert row is None

    @pytest.mark.asyncio
    async def test_execute_batch_empty_list(self, executor: WriteExecutor) -> None:
        """Test batch execution with empty list does nothing."""
        # Should complete without error
        await executor.execute_batch([])

    @pytest.mark.asyncio
    async def test_execute_batch_insert_or_replace(self, executor: WriteExecutor) -> None:
        """Test INSERT OR REPLACE updates existing records."""
        now = datetime.now().isoformat()

        # Insert initial project
        await executor._db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-replace", "Original Name", '{"version": 1}', now, now)
        )
        await executor._db.commit()

        # Update via INSERT OR REPLACE
        operations = [
            WriteOperation(
                entity_type="project",
                entity_id="proj-replace",
                operation="insert",
                data={
                    "id": "proj-replace",
                    "name": "Updated Name",
                    "config_json": {"version": 2},
                    "created_at": now,
                    "updated_at": now,
                },
            )
        ]

        await executor.execute_batch(operations)

        # Verify the project was updated
        await executor._db.execute(
            "SELECT name, config_json FROM projects WHERE id = ?",
            ("proj-replace",)
        )
        row = await executor._db.fetchone()
        assert row is not None
        assert row[0] == "Updated Name"
        import json
        assert json.loads(row[1]) == {"version": 2}

    @pytest.mark.asyncio
    async def test_execute_batch_config_json_string_handling(self, executor: WriteExecutor) -> None:
        """Test config_json handling when already a string."""
        now = datetime.now().isoformat()

        operations = [
            WriteOperation(
                entity_type="project",
                entity_id="proj-string",
                operation="insert",
                data={
                    "id": "proj-string",
                    "name": "String Config Test",
                    "config_json": '{"already": "string"}',
                    "created_at": now,
                    "updated_at": now,
                },
            )
        ]

        await executor.execute_batch(operations)

        # Verify the project was inserted with correct config
        await executor._db.execute(
            "SELECT config_json FROM projects WHERE id = ?",
            ("proj-string",)
        )
        row = await executor._db.fetchone()
        assert row is not None
        import json
        assert json.loads(row[0]) == {"already": "string"}

    @pytest.mark.asyncio
    async def test_execute_batch_structure_size_tier(self, executor: WriteExecutor) -> None:
        """Test batch execution writes and persists size_tier for structures."""
        now = datetime.now().isoformat()

        # Create required parent records
        await executor._db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-st", "Size Tier Project", "{}", now, now)
        )
        await executor._db.execute(
            "INSERT INTO villages (id, project_id, name, center_x, center_y, bounds_min_x, bounds_min_y, bounds_max_x, bounds_max_y, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("village-st", "proj-st", "Test Village", 0, 0, -10, -10, 10, 10, now, now)
        )
        await executor._db.commit()

        operations = [
            WriteOperation(
                entity_type="structure",
                entity_id="struct-st",
                operation="insert",
                data={
                    "id": "struct-st",
                    "village_id": "village-st",
                    "type": "house",
                    "position_x": 1,
                    "position_y": 2,
                    "stage": 0,
                    "material": "wood",
                    "work_units": 0,
                    "work_required": 100,
                    "size_tier": 2,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        ]

        await executor.execute_batch(operations)

        # Verify size_tier was written
        await executor._db.execute(
            "SELECT size_tier FROM structures WHERE id = ?",
            ("struct-st",)
        )
        row = await executor._db.fetchone()
        assert row is not None
        assert row[0] == 2

    @pytest.mark.asyncio
    async def test_execute_batch_agent_ids_json_string_handling(self, executor: WriteExecutor) -> None:
        """Test agent_ids_json handling when already a string."""
        now = datetime.now().isoformat()

        # Create required parent project
        await executor._db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-agent-ids", "Agent IDs Test Project", "{}", now, now)
        )
        await executor._db.commit()

        operations = [
            WriteOperation(
                entity_type="session",
                entity_id="sess-string",
                operation="insert",
                data={
                    "id": "sess-string",
                    "project_id": "proj-agent-ids",
                    "started_at": now,
                    "last_activity": now,
                    "agent_ids_json": '["a", "b", "c"]',
                },
            )
        ]

        await executor.execute_batch(operations)

        # Verify the session was inserted with correct agent_ids
        await executor._db.execute(
            "SELECT agent_ids_json FROM sessions WHERE id = ?",
            ("sess-string",)
        )
        row = await executor._db.fetchone()
        assert row is not None
        import json
        assert json.loads(row[0]) == ["a", "b", "c"]
