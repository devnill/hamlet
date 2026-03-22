"""Tests for StateLoader entity loading (work item 081).

Run with: pytest tests/test_persistence_loader.py -v
"""
from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone

from hamlet.persistence.connection import DatabaseConnection
from hamlet.persistence.migrations import run_migrations
from hamlet.persistence.loader import StateLoader


@pytest.fixture
async def db():
    """Create an in-memory database with migrations applied."""
    db = DatabaseConnection(":memory:")
    await db.__aenter__()
    await run_migrations(db)
    yield db
    await db.__aexit__(None, None, None)


class TestStateLoader:
    """Test suite for StateLoader entity loading."""

    @pytest.mark.asyncio
    async def test_load_state_returns_world_state_data(self, db: DatabaseConnection) -> None:
        """Test load_state returns WorldStateData with all entities."""
        now = datetime.now().isoformat()

        # Insert test data into all tables
        await db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-001", "Test Project", '{"key": "value"}', now, now)
        )
        await db.execute(
            "INSERT INTO sessions (id, project_id, started_at, last_activity, agent_ids_json) VALUES (?, ?, ?, ?, ?)",
            ("sess-001", "proj-001", now, now, '["agent-001"]')
        )
        await db.execute(
            "INSERT INTO villages (id, project_id, name, center_x, center_y, bounds_min_x, bounds_min_y, bounds_max_x, bounds_max_y, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("village-001", "proj-001", "Test Village", 0, 0, -10, -10, 10, 10, now, now)
        )
        await db.execute(
            "INSERT INTO agents (id, session_id, village_id, parent_id, inferred_type, color, position_x, position_y, last_seen, state, current_activity, total_work_units, created_at, updated_at, project_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("agent-001", "sess-001", "village-001", None, "builder", "blue", 5, 5, now, "active", "building", 10, now, now, "proj-001")
        )
        await db.execute(
            "INSERT INTO structures (id, village_id, type, position_x, position_y, stage, material, work_units, work_required, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("struct-001", "village-001", "house", 3, 4, 1, "wood", 5, 100, now, now)
        )
        await db.execute(
            "INSERT INTO world_metadata (key, value) VALUES (?, ?)",
            ("version", "1.0")
        )
        await db.commit()

        # Load state
        loader = StateLoader(db)
        state = await loader.load_state()

        # Verify all entities loaded
        assert len(state.projects) == 1
        assert len(state.sessions) == 1
        assert len(state.villages) == 1
        assert len(state.agents) == 1
        assert len(state.structures) == 1
        assert state.metadata == {"version": "1.0"}

        # Verify project data
        project = state.projects[0]
        assert project["id"] == "proj-001"
        assert project["name"] == "Test Project"

        # Verify session data
        session = state.sessions[0]
        assert session["id"] == "sess-001"
        assert session["project_id"] == "proj-001"

        # Verify village data
        village = state.villages[0]
        assert village["id"] == "village-001"
        assert village["name"] == "Test Village"
        assert village["center_x"] == 0
        assert village["bounds_min_x"] == -10

        # Verify agent data
        agent = state.agents[0]
        assert agent["id"] == "agent-001"
        assert agent["inferred_type"] == "builder"
        assert agent["position_x"] == 5
        assert agent["project_id"] == "proj-001"

        # Verify structure data
        structure = state.structures[0]
        assert structure["id"] == "struct-001"
        assert structure["type"] == "house"
        assert structure["stage"] == 1

    @pytest.mark.asyncio
    async def test_load_projects_parses_config_json(self, db: DatabaseConnection) -> None:
        """Test load_state parses config_json from string to dict."""
        now = datetime.now().isoformat()

        # Insert project with complex config
        config = {"settings": {"difficulty": "hard"}, "features": ["a", "b"]}
        await db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-json", "JSON Test", json.dumps(config), now, now)
        )
        await db.commit()

        # Load state
        loader = StateLoader(db)
        state = await loader.load_state()

        # Verify config_json was parsed
        assert len(state.projects) == 1
        project = state.projects[0]
        assert project["config_json"] == config
        assert isinstance(project["config_json"], dict)

    @pytest.mark.asyncio
    async def test_load_graceful_on_missing_table(self, db: DatabaseConnection) -> None:
        """Test load_state returns empty list when table is missing (GP-7)."""
        # Drop the projects table
        await db.execute("DROP TABLE projects")
        await db.commit()

        # Load state - should not raise
        loader = StateLoader(db)
        state = await loader.load_state()

        # Verify projects is empty list, not exception
        assert state.projects == []

        # Verify other tables still load
        assert state.sessions == []
        assert state.villages == []
        assert state.agents == []
        assert state.structures == []
        assert state.metadata == {}

    @pytest.mark.asyncio
    async def test_load_sessions_parses_agent_ids_json(self, db: DatabaseConnection) -> None:
        """Test load_state parses agent_ids_json from string to list."""
        now = datetime.now().isoformat()

        # Insert required project
        await db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-sess", "Session Test", "{}", now, now)
        )

        # Insert session with agent IDs
        agent_ids = ["agent-1", "agent-2", "agent-3"]
        await db.execute(
            "INSERT INTO sessions (id, project_id, started_at, last_activity, agent_ids_json) VALUES (?, ?, ?, ?, ?)",
            ("sess-json", "proj-sess", now, now, json.dumps(agent_ids))
        )
        await db.commit()

        # Load state
        loader = StateLoader(db)
        state = await loader.load_state()

        # Verify agent_ids_json was parsed
        assert len(state.sessions) == 1
        session = state.sessions[0]
        assert session["agent_ids_json"] == agent_ids
        assert isinstance(session["agent_ids_json"], list)

    @pytest.mark.asyncio
    async def test_load_empty_database(self, db: DatabaseConnection) -> None:
        """Test load_state returns empty collections for empty database."""
        loader = StateLoader(db)
        state = await loader.load_state()

        assert state.projects == []
        assert state.sessions == []
        assert state.villages == []
        assert state.agents == []
        assert state.structures == []
        assert state.metadata == {}

    @pytest.mark.asyncio
    async def test_load_multiple_projects(self, db: DatabaseConnection) -> None:
        """Test load_state handles multiple projects."""
        now = datetime.now().isoformat()

        for i in range(3):
            await db.execute(
                "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (f"proj-{i}", f"Project {i}", "{}", now, now)
            )
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        assert len(state.projects) == 3
        project_ids = {p["id"] for p in state.projects}
        assert project_ids == {"proj-0", "proj-1", "proj-2"}

    @pytest.mark.asyncio
    async def test_load_config_json_none(self, db: DatabaseConnection) -> None:
        """Test load_state handles NULL config_json."""
        now = datetime.now().isoformat()

        # Insert project with NULL config_json (shouldn't happen but test defensively)
        await db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-null", "Null Config", "null", now, now)
        )
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        assert len(state.projects) == 1
        # NULL config_json should result in empty dict
        assert state.projects[0]["config_json"] == {}

    @pytest.mark.asyncio
    async def test_load_invalid_config_json(self, db: DatabaseConnection) -> None:
        """Test load_state handles invalid JSON gracefully."""
        now = datetime.now().isoformat()

        # Insert project with invalid JSON
        await db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-invalid", "Invalid JSON", "not valid json", now, now)
        )
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        # Should still load, with empty config
        assert len(state.projects) == 1
        assert state.projects[0]["config_json"] == {}

    @pytest.mark.asyncio
    async def test_load_agent_ids_json_none(self, db: DatabaseConnection) -> None:
        """Test load_state handles NULL agent_ids_json."""
        now = datetime.now().isoformat()

        # Insert required project
        await db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-null-ids", "Null IDs Test", "{}", now, now)
        )

        # Insert session with JSON null agent_ids_json
        await db.execute(
            "INSERT INTO sessions (id, project_id, started_at, last_activity, agent_ids_json) VALUES (?, ?, ?, ?, ?)",
            ("sess-null", "proj-null-ids", now, now, "null")
        )
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        assert len(state.sessions) == 1
        # NULL agent_ids_json should result in empty list
        assert state.sessions[0]["agent_ids_json"] == []

    @pytest.mark.asyncio
    async def test_load_invalid_agent_ids_json(self, db: DatabaseConnection) -> None:
        """Test load_state handles invalid agent_ids_json gracefully."""
        now = datetime.now().isoformat()

        # Insert required project
        await db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-invalid-ids", "Invalid IDs Test", "{}", now, now)
        )

        # Insert session with invalid JSON
        await db.execute(
            "INSERT INTO sessions (id, project_id, started_at, last_activity, agent_ids_json) VALUES (?, ?, ?, ?, ?)",
            ("sess-invalid", "proj-invalid-ids", now, now, "not valid json")
        )
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        # Should still load, with empty list
        assert len(state.sessions) == 1
        assert state.sessions[0]["agent_ids_json"] == []

    @pytest.mark.asyncio
    async def test_load_graceful_on_missing_sessions_table(self, db: DatabaseConnection) -> None:
        """Test load_state handles missing sessions table gracefully."""
        await db.execute("DROP TABLE sessions")
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        assert state.sessions == []

    @pytest.mark.asyncio
    async def test_load_graceful_on_missing_villages_table(self, db: DatabaseConnection) -> None:
        """Test load_state handles missing villages table gracefully."""
        await db.execute("DROP TABLE villages")
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        assert state.villages == []

    @pytest.mark.asyncio
    async def test_load_graceful_on_missing_agents_table(self, db: DatabaseConnection) -> None:
        """Test load_state handles missing agents table gracefully."""
        await db.execute("DROP TABLE agents")
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        assert state.agents == []

    @pytest.mark.asyncio
    async def test_load_graceful_on_missing_structures_table(self, db: DatabaseConnection) -> None:
        """Test load_state handles missing structures table gracefully."""
        await db.execute("DROP TABLE structures")
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        assert state.structures == []

    @pytest.mark.asyncio
    async def test_load_graceful_on_missing_metadata_table(self, db: DatabaseConnection) -> None:
        """Test load_state handles missing world_metadata table gracefully."""
        await db.execute("DROP TABLE world_metadata")
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        assert state.metadata == {}

    @pytest.mark.asyncio
    async def test_timestamp_fields_are_timezone_aware(self, db: DatabaseConnection) -> None:
        """Test that all timestamp fields returned by load_state are timezone-aware datetimes."""
        now = datetime.now().isoformat()

        await db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-tz", "TZ Project", "{}", now, now)
        )
        await db.execute(
            "INSERT INTO sessions (id, project_id, started_at, last_activity, agent_ids_json) VALUES (?, ?, ?, ?, ?)",
            ("sess-tz", "proj-tz", now, now, "[]")
        )
        await db.execute(
            "INSERT INTO villages (id, project_id, name, center_x, center_y, bounds_min_x, bounds_min_y, bounds_max_x, bounds_max_y, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("village-tz", "proj-tz", "TZ Village", 0, 0, -10, -10, 10, 10, now, now)
        )
        await db.execute(
            "INSERT INTO agents (id, session_id, village_id, parent_id, inferred_type, color, position_x, position_y, last_seen, state, current_activity, total_work_units, created_at, updated_at, project_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("agent-tz", "sess-tz", "village-tz", None, "worker", "red", 1, 1, now, "active", "idle", 0, now, now, "proj-tz")
        )
        await db.execute(
            "INSERT INTO structures (id, village_id, type, position_x, position_y, stage, material, work_units, work_required, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("struct-tz", "village-tz", "wall", 2, 3, 0, "stone", 0, 50, now, now)
        )
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        # Projects: created_at and updated_at must be timezone-aware
        project = state.projects[0]
        assert isinstance(project["created_at"], datetime)
        assert project["created_at"].tzinfo is not None
        assert isinstance(project["updated_at"], datetime)
        assert project["updated_at"].tzinfo is not None

        # Sessions: started_at and last_activity must be timezone-aware
        session = state.sessions[0]
        assert isinstance(session["started_at"], datetime)
        assert session["started_at"].tzinfo is not None
        assert isinstance(session["last_activity"], datetime)
        assert session["last_activity"].tzinfo is not None

        # Villages: created_at and updated_at must be timezone-aware
        village = state.villages[0]
        assert isinstance(village["created_at"], datetime)
        assert village["created_at"].tzinfo is not None
        assert isinstance(village["updated_at"], datetime)
        assert village["updated_at"].tzinfo is not None

        # Agents: last_seen, created_at and updated_at must be timezone-aware
        agent = state.agents[0]
        assert isinstance(agent["last_seen"], datetime)
        assert agent["last_seen"].tzinfo is not None
        assert isinstance(agent["created_at"], datetime)
        assert agent["created_at"].tzinfo is not None
        assert isinstance(agent["updated_at"], datetime)
        assert agent["updated_at"].tzinfo is not None

        # Structures: created_at and updated_at must be timezone-aware
        structure = state.structures[0]
        assert isinstance(structure["created_at"], datetime)
        assert structure["created_at"].tzinfo is not None
        assert isinstance(structure["updated_at"], datetime)
        assert structure["updated_at"].tzinfo is not None

    @pytest.mark.asyncio
    async def test_load_structure_size_tier(self, db: DatabaseConnection) -> None:
        """Test load_state loads size_tier from structures table."""
        now = datetime.now().isoformat()

        await db.execute(
            "INSERT INTO projects (id, name, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-st", "Size Tier Project", "{}", now, now)
        )
        await db.execute(
            "INSERT INTO villages (id, project_id, name, center_x, center_y, bounds_min_x, bounds_min_y, bounds_max_x, bounds_max_y, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("village-st", "proj-st", "Test Village", 0, 0, -10, -10, 10, 10, now, now)
        )
        await db.execute(
            "INSERT INTO structures (id, village_id, type, position_x, position_y, stage, material, work_units, work_required, size_tier, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("struct-st", "village-st", "house", 1, 2, 0, "wood", 0, 100, 3, now, now)
        )
        await db.commit()

        loader = StateLoader(db)
        state = await loader.load_state()

        assert len(state.structures) == 1
        structure = state.structures[0]
        assert structure["size_tier"] == 3
