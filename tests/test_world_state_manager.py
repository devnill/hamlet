"""Tests for WorldStateManager CRUD, loading, and queries (work item 088).

Run with: pytest tests/test_world_state_manager.py -v
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from hamlet.world_state.manager import WorldStateManager
from hamlet.world_state.state import WorldState
from hamlet.world_state.types import (
    Agent,
    AgentState,
    AgentType,
    Bounds,
    Position,
    Project,
    Session,
    Village,
)


class TestWorldStateManager:
    """Test suite for WorldStateManager CRUD operations and queries."""

    @pytest.fixture
    def mock_persistence(self) -> MagicMock:
        """Return a mock persistence object."""
        p = MagicMock()
        p.queue_write = AsyncMock()
        p.load_state = AsyncMock()
        return p

    @pytest.fixture
    def manager(self, mock_persistence: MagicMock) -> WorldStateManager:
        """Return a WorldStateManager with mocked persistence."""
        return WorldStateManager(mock_persistence)

    async def test_load_from_persistence_restores_state(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """load_from_persistence() restores all entities from persistence data."""
        now = datetime.now(UTC)
        project_id = "proj-1"
        village_id = "village-1"
        session_id = "session-1"
        agent_id = "agent-1"

        # Create mock data structure
        mock_data = MagicMock()
        mock_data.projects = [
            {
                "id": project_id,
                "name": "Test Project",
                "village_id": village_id,
                "config_json": {"key": "value"},
            }
        ]
        mock_data.villages = [
            {
                "id": village_id,
                "project_id": project_id,
                "name": "Test Village",
                "center_x": 10,
                "center_y": 20,
                "bounds_min_x": 0,
                "bounds_min_y": 0,
                "bounds_max_x": 100,
                "bounds_max_y": 100,
            }
        ]
        mock_data.sessions = [
            {
                "id": session_id,
                "project_id": project_id,
            }
        ]
        mock_data.agents = [
            {
                "id": agent_id,
                "session_id": session_id,
                "project_id": project_id,
                "village_id": village_id,
                "inferred_type": "researcher",
                "color": "blue",
                "position_x": 15,
                "position_y": 25,
                "last_seen": now,
                "state": "active",
            }
        ]
        mock_data.structures = []
        mock_data.metadata = {}

        mock_persistence.load_state.return_value = mock_data

        await manager.load_from_persistence()

        # Verify projects restored
        assert project_id in manager._state.projects
        project = manager._state.projects[project_id]
        assert project.name == "Test Project"
        assert project.village_id == village_id

        # Verify villages restored
        assert village_id in manager._state.villages
        village = manager._state.villages[village_id]
        assert village.name == "Test Village"
        assert village.center == Position(10, 20)
        assert village.bounds == Bounds(0, 0, 100, 100)

        # Verify sessions restored
        assert session_id in manager._state.sessions
        session = manager._state.sessions[session_id]
        assert session.project_id == project_id

        # Verify agents restored and placed in grid
        assert agent_id in manager._state.agents
        agent = manager._state.agents[agent_id]
        assert agent.position == Position(15, 25)
        assert manager._grid.is_occupied(Position(15, 25))
        assert manager._grid.get_entity_at(Position(15, 25)) == agent_id

    async def test_get_or_create_project_creates_new(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """get_or_create_project() creates a new project with village when not exists."""
        project_id = "new-project"
        project_name = "New Test Project"

        project = await manager.get_or_create_project(project_id, project_name)

        # Verify project created
        assert project.id == project_id
        assert project.name == project_name
        assert project.village_id != ""

        # Verify village was also created
        assert project.village_id in manager._state.villages
        village = manager._state.villages[project.village_id]
        assert village.project_id == project_id
        assert village.name == f"{project_name} village"

        # Verify persistence was queued
        mock_persistence.queue_write.assert_any_call(
            "project", project_id, project
        )
        mock_persistence.queue_write.assert_any_call(
            "village", project.village_id, village
        )

    async def test_get_or_create_agent_spawns_new(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """get_or_create_agent() spawns a new agent when session has none."""
        # Set up project, village, and session
        project_id = "proj-1"
        village_id = "village-1"
        session_id = "session-1"

        manager._state.projects[project_id] = Project(
            id=project_id, name="Test Project", village_id=village_id
        )
        manager._state.villages[village_id] = Village(
            id=village_id,
            project_id=project_id,
            name="Test Village",
            center=Position(0, 0),
            bounds=Bounds(0, 0, 0, 0),
        )
        manager._state.sessions[session_id] = Session(
            id=session_id, project_id=project_id
        )

        agent = await manager.get_or_create_agent(session_id)

        # Verify agent created
        assert agent.session_id == session_id
        assert agent.project_id == project_id
        assert agent.village_id == village_id
        assert agent.state == AgentState.ACTIVE

        # Verify agent is in session
        assert agent.id in manager._state.sessions[session_id].agent_ids

        # Verify agent is in village
        assert agent.id in manager._state.villages[village_id].agent_ids

        # Verify persistence was queued
        mock_persistence.queue_write.assert_called_with(
            "agent", agent.id, agent
        )

    async def test_update_agent_modifies_fields(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """update_agent() modifies valid agent fields and persists changes."""
        # Create an agent
        agent_id = "agent-1"
        agent = Agent(
            id=agent_id,
            session_id="session-1",
            project_id="proj-1",
            village_id="village-1",
            color="white",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.GENERAL,
        )
        manager._state.agents[agent_id] = agent

        # Update the agent
        await manager.update_agent(agent_id, color="red", state=AgentState.IDLE)

        # Verify fields modified
        assert agent.color == "red"
        assert agent.state == AgentState.IDLE

        # Verify persistence was queued
        mock_persistence.queue_write.assert_called_with(
            "agent", agent_id, agent
        )

    async def test_update_agent_skips_invalid_fields(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """update_agent() skips invalid fields and logs warning."""
        agent_id = "agent-1"
        agent = Agent(
            id=agent_id,
            session_id="session-1",
            project_id="proj-1",
            village_id="village-1",
            color="white",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.GENERAL,
        )
        manager._state.agents[agent_id] = agent

        # Try to update with invalid field
        await manager.update_agent(agent_id, color="blue", invalid_field="ignored")

        # Verify valid field changed, invalid field ignored
        assert agent.color == "blue"
        assert not hasattr(agent, "invalid_field")

    async def test_update_agent_handles_missing_agent(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """update_agent() logs debug and returns when agent not found."""
        # Should not raise, just log and return
        await manager.update_agent("nonexistent", color="red")

        # Verify no persistence call
        mock_persistence.queue_write.assert_not_called()

    async def test_get_agents_in_view_returns_bounded(
        self, manager: WorldStateManager
    ) -> None:
        """get_agents_in_view() returns only agents within bounds."""
        # Create agents at various positions
        agent_in_bounds = Agent(
            id="agent-in",
            session_id="session-1",
            project_id="proj-1",
            village_id="village-1",
            position=Position(10, 10),
            color="white",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.GENERAL,
        )
        agent_outside = Agent(
            id="agent-out",
            session_id="session-1",
            project_id="proj-1",
            village_id="village-1",
            position=Position(100, 100),
            color="white",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.GENERAL,
        )
        agent_edge = Agent(
            id="agent-edge",
            session_id="session-1",
            project_id="proj-1",
            village_id="village-1",
            position=Position(20, 30),
            color="white",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.GENERAL,
        )

        manager._state.agents[agent_in_bounds.id] = agent_in_bounds
        manager._state.agents[agent_outside.id] = agent_outside
        manager._state.agents[agent_edge.id] = agent_edge

        # Define bounds that include agent_in and agent_edge but not agent_out
        bounds = Bounds(min_x=5, min_y=5, max_x=20, max_y=30)

        result = await manager.get_agents_in_view(bounds)

        # Verify only agents within bounds returned
        result_ids = {a.id for a in result}
        assert agent_in_bounds.id in result_ids
        assert agent_edge.id in result_ids
        assert agent_outside.id not in result_ids

    async def test_get_or_create_project_returns_existing(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """get_or_create_project() returns existing project if already exists."""
        project_id = "existing-project"
        existing_project = Project(
            id=project_id, name="Existing Project", village_id="village-1"
        )
        manager._state.projects[project_id] = existing_project

        result = await manager.get_or_create_project(project_id, "New Name")

        # Verify existing project returned, not a new one
        assert result is existing_project
        assert result.name == "Existing Project"  # Name unchanged

        # Verify no persistence calls for existing
        mock_persistence.queue_write.assert_not_called()

    async def test_get_or_create_agent_returns_existing(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """get_or_create_agent() returns existing primary agent if session has one."""
        session_id = "session-1"
        existing_agent = Agent(
            id="existing-agent",
            session_id=session_id,
            project_id="proj-1",
            village_id="village-1",
            color="white",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.GENERAL,
        )
        manager._state.agents[existing_agent.id] = existing_agent
        manager._state.sessions[session_id] = Session(
            id=session_id,
            project_id="proj-1",
            agent_ids=[existing_agent.id],
        )

        result = await manager.get_or_create_agent(session_id)

        # Verify existing agent returned
        assert result is existing_agent

        # Verify no new persistence calls
        mock_persistence.queue_write.assert_not_called()

    # -------------------------------------------------------------------------
    # v0.4.0 event-branch tests (WI-187)
    # -------------------------------------------------------------------------

    async def test_handle_event_session_start_creates_project_and_session(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """SessionStart event causes project and session to be created in state."""
        from hamlet.event_processing.internal_event import HookType, InternalEvent
        from datetime import UTC, datetime

        event = InternalEvent(
            id="evt-session-start",
            sequence=1,
            received_at=datetime.now(UTC),
            session_id="s1",
            project_id="p1",
            project_name="P1",
            hook_type=HookType.SessionStart,
            source="cli",
        )

        await manager.handle_event(event)

        projects = await manager.get_projects()
        project_ids = {p.id for p in projects}
        assert "p1" in project_ids, "Project 'p1' should have been created"

        agents = await manager.get_all_agents()
        assert agents == [], "No agents should have been created by SessionStart alone"

    async def test_handle_event_session_end_sets_agents_idle(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """SessionEnd event marks all agents for the session as IDLE."""
        from hamlet.event_processing.internal_event import HookType, InternalEvent
        from hamlet.world_state.types import AgentState
        from datetime import UTC, datetime

        # Pre-populate a session and agent
        await manager.get_or_create_session("s1", "p1")
        await manager.get_or_create_agent("s1")

        agents_before = await manager.get_all_agents()
        assert len(agents_before) >= 1, "At least one agent should exist"

        event = InternalEvent(
            id="evt-session-end",
            sequence=2,
            received_at=datetime.now(UTC),
            session_id="s1",
            project_id="p1",
            project_name="P1",
            hook_type=HookType.SessionEnd,
            reason="user_exit",
        )

        await manager.handle_event(event)

        agents = await manager.get_all_agents()
        session_agents = [a for a in agents if a.session_id == "s1"]
        assert len(session_agents) >= 1, "Should still have agents for the session"
        for agent in session_agents:
            assert agent.state == AgentState.IDLE, (
                f"Agent {agent.id} should be IDLE after SessionEnd, got {agent.state}"
            )

    async def test_handle_event_stop_end_turn_sets_agents_idle(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """Stop event with stop_reason='end_turn' marks all session agents IDLE."""
        from hamlet.event_processing.internal_event import HookType, InternalEvent
        from hamlet.world_state.types import AgentState

        # Pre-populate a session and agent
        await manager.get_or_create_session("s2", "p2")
        await manager.get_or_create_agent("s2")

        # Verify agent starts non-IDLE so the assertion below is meaningful
        agents_before = await manager.get_all_agents()
        session_agents_before = [a for a in agents_before if a.session_id == "s2"]
        assert len(session_agents_before) >= 1, "Should have at least one agent before the event"
        assert all(a.state != AgentState.IDLE for a in session_agents_before), (
            "Agents should not start IDLE"
        )

        event = InternalEvent(
            id="evt-stop-end-turn",
            sequence=1,
            received_at=datetime.now(UTC),
            session_id="s2",
            project_id="p2",
            project_name="P2",
            hook_type=HookType.Stop,
            stop_reason="end_turn",
        )

        await manager.handle_event(event)

        agents = await manager.get_all_agents()
        session_agents = [a for a in agents if a.session_id == "s2"]
        assert len(session_agents) >= 1, "Should have at least one agent for the session"
        for agent in session_agents:
            assert agent.state == AgentState.IDLE, (
                f"Agent {agent.id} should be IDLE after Stop/end_turn, got {agent.state}"
            )

    async def test_handle_event_subagent_start_creates_agent(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """SubagentStart event results in an agent existing for the session."""
        from hamlet.event_processing.internal_event import HookType, InternalEvent
        from datetime import UTC, datetime

        # Create project and session so there is a village to spawn into
        await manager.get_or_create_project("p1", "P1")
        await manager.get_or_create_session("s1", "p1")

        event = InternalEvent(
            id="evt-subagent-start",
            sequence=3,
            received_at=datetime.now(UTC),
            session_id="s1",
            project_id="p1",
            project_name="P1",
            hook_type=HookType.SubagentStart,
            agent_id="a1",
            agent_type="coder",
        )

        await manager.handle_event(event)

        agents = await manager.get_all_agents()
        assert len(agents) >= 1, "At least one agent should have been created by SubagentStart"
        session_agents = [a for a in agents if a.session_id == "s1"]
        assert len(session_agents) >= 1, "Agent should belong to session 's1'"

    async def test_handle_event_task_completed_calls_add_work_units(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """TaskCompleted event triggers add_work_units for an agent with a village."""
        from hamlet.event_processing.internal_event import HookType, InternalEvent
        from unittest.mock import AsyncMock, patch
        from datetime import UTC, datetime

        # Create project, session, and agent with a valid village_id
        await manager.get_or_create_project("p1", "P1")
        await manager.get_or_create_session("s1", "p1")
        await manager.get_or_create_agent("s1")

        agents = await manager.get_all_agents()
        assert len(agents) >= 1, "Need at least one agent with a village_id for TaskCompleted"

        event = InternalEvent(
            id="evt-task-completed",
            sequence=4,
            received_at=datetime.now(UTC),
            session_id="s1",
            project_id="p1",
            project_name="P1",
            hook_type=HookType.TaskCompleted,
            task_id="t1",
            task_subject="Build feature",
            task_description="Implement the feature",
            teammate_name="alice",
        )

        with patch.object(manager, "add_work_units", wraps=manager.add_work_units) as spy:
            await manager.handle_event(event)
            spy.assert_awaited_once()

    @pytest.mark.parametrize(
        "notification_type, expected_prefix",
        [
            ("warning", "Notification [type=warning]:"),
            ("error", "Notification [type=error]:"),
        ],
    )
    async def test_handle_event_notification_non_generic_type(
        self,
        manager: WorldStateManager,
        mock_persistence: MagicMock,
        notification_type: str,
        expected_prefix: str,
    ) -> None:
        """Non-generic notification_type produces a differentiated summary string."""
        from hamlet.event_processing.internal_event import HookType, InternalEvent

        event = InternalEvent(
            id="evt-notif-typed",
            sequence=1,
            received_at=datetime.now(UTC),
            session_id="s1",
            project_id="p1",
            project_name="P1",
            hook_type=HookType.Notification,
            notification_message="disk almost full",
            notification_type=notification_type,
        )
        await manager.handle_event(event)

        log = await manager.get_event_log()
        assert log, "Event log should not be empty"
        assert log[-1].summary.startswith(expected_prefix)

    async def test_handle_event_notification_generic_type_fallback(
        self,
        manager: WorldStateManager,
        mock_persistence: MagicMock,
    ) -> None:
        """notification_type='generic' uses the plain Notification: summary."""
        from hamlet.event_processing.internal_event import HookType, InternalEvent

        event = InternalEvent(
            id="evt-notif-generic",
            sequence=1,
            received_at=datetime.now(UTC),
            session_id="s1",
            project_id="p1",
            project_name="P1",
            hook_type=HookType.Notification,
            notification_message="hello",
            notification_type="generic",
        )
        await manager.handle_event(event)

        log = await manager.get_event_log()
        assert log, "Event log should not be empty"
        assert log[-1].summary.startswith("Notification:")
        assert "[type=" not in log[-1].summary

    async def test_handle_event_notification_none_type_fallback(
        self,
        manager: WorldStateManager,
        mock_persistence: MagicMock,
    ) -> None:
        """notification_type=None falls back to plain Notification: summary."""
        from hamlet.event_processing.internal_event import HookType, InternalEvent

        event = InternalEvent(
            id="evt-notif-none",
            sequence=1,
            received_at=datetime.now(UTC),
            session_id="s1",
            project_id="p1",
            project_name="P1",
            hook_type=HookType.Notification,
            notification_message="hello",
            notification_type=None,
        )
        await manager.handle_event(event)

        log = await manager.get_event_log()
        assert log, "Event log should not be empty"
        assert log[-1].summary.startswith("Notification:")
        assert "[type=" not in log[-1].summary
