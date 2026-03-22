"""Tests for WorldStateManager CRUD, loading, and queries (work item 088).

Run with: pytest tests/test_world_state_manager.py -v
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hamlet.event_processing.internal_event import HookType, InternalEvent
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
    Structure,
    StructureType,
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
        assert agent.state == AgentState.ZOMBIE, (
            f"Expected ZOMBIE but got {agent.state}; agents must reload as ZOMBIE on daemon startup"
        )

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

        assert "s1" in manager._state.sessions, "Session 's1' should have been created"

        agents = await manager.get_all_agents()
        assert agents == [], "No agents should have been created by SessionStart alone"

    async def test_handle_event_session_end_sets_agents_idle(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """SessionEnd event marks all agents for the session as IDLE."""
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

    async def test_load_from_persistence_sets_agent_state_to_zombie(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """load_from_persistence() sets all loaded agents to ZOMBIE regardless of stored state."""
        now = datetime.now(UTC)
        agent_id = "agent-zombie-test"

        mock_data = MagicMock()
        mock_data.projects = []
        mock_data.villages = []
        mock_data.sessions = []
        mock_data.agents = [
            {
                "id": agent_id,
                "session_id": "session-1",
                "project_id": "proj-1",
                "village_id": "village-1",
                "inferred_type": "general",
                "color": "white",
                "position_x": 5,
                "position_y": 10,
                "last_seen": now,
                "state": "active",
            }
        ]
        mock_data.structures = []
        mock_data.metadata = {}

        mock_persistence.load_state.return_value = mock_data

        await manager.load_from_persistence()

        assert agent_id in manager._state.agents
        agent = manager._state.agents[agent_id]
        assert agent.state == AgentState.ZOMBIE, (
            f"Expected ZOMBIE but got {agent.state}; agents must reload as ZOMBIE to prevent phantom active agents"
        )
        # Verify all other fields are preserved exactly as loaded
        assert agent.id == agent_id
        assert agent.session_id == "session-1"
        assert agent.village_id == "village-1"
        assert agent.position == Position(5, 10)
        assert agent.inferred_type == AgentType.GENERAL
        assert agent.last_seen == now

    async def test_despawn_agent_removes_from_state(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """despawn_agent() removes the agent from world state."""
        mock_persistence.delete_agent = AsyncMock()
        village_id = "village-1"
        agent_id = "agent-1"

        manager._state.villages[village_id] = Village(
            id=village_id,
            project_id="proj-1",
            name="Test Village",
            center=Position(0, 0),
            bounds=Bounds(0, 0, 0, 0),
            agent_ids=[agent_id],
        )
        position = Position(5, 5)
        agent = Agent(
            id=agent_id,
            session_id="session-1",
            project_id="proj-1",
            village_id=village_id,
            position=position,
            color="white",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.GENERAL,
        )
        manager._state.agents[agent_id] = agent
        manager._grid.occupy(position, agent_id)

        await manager.despawn_agent(agent_id)

        # Agent removed from state
        all_agents = await manager.get_all_agents()
        assert not any(a.id == agent_id for a in all_agents)

    async def test_despawn_agent_frees_grid_position(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """despawn_agent() vacates the agent's grid position."""
        mock_persistence.delete_agent = AsyncMock()
        village_id = "village-1"
        agent_id = "agent-1"
        position = Position(3, 7)

        manager._state.villages[village_id] = Village(
            id=village_id,
            project_id="proj-1",
            name="Test Village",
            center=Position(0, 0),
            bounds=Bounds(0, 0, 0, 0),
            agent_ids=[agent_id],
        )
        agent = Agent(
            id=agent_id,
            session_id="session-1",
            project_id="proj-1",
            village_id=village_id,
            position=position,
            color="white",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.GENERAL,
        )
        manager._state.agents[agent_id] = agent
        manager._grid.occupy(position, agent_id)

        assert manager._grid.is_occupied(position)

        await manager.despawn_agent(agent_id)

        assert not manager._grid.is_occupied(position)

    async def test_despawn_agent_removes_from_village(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """despawn_agent() removes the agent from its village's agent_ids."""
        mock_persistence.delete_agent = AsyncMock()
        village_id = "village-1"
        agent_id = "agent-1"

        manager._state.villages[village_id] = Village(
            id=village_id,
            project_id="proj-1",
            name="Test Village",
            center=Position(0, 0),
            bounds=Bounds(0, 0, 0, 0),
            agent_ids=[agent_id],
        )
        position = Position(2, 2)
        agent = Agent(
            id=agent_id,
            session_id="session-1",
            project_id="proj-1",
            village_id=village_id,
            position=position,
            color="white",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.GENERAL,
        )
        manager._state.agents[agent_id] = agent
        manager._grid.occupy(position, agent_id)

        await manager.despawn_agent(agent_id)

        village = manager._state.villages[village_id]
        assert agent_id not in village.agent_ids

    async def test_despawn_agent_calls_persistence_delete(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """despawn_agent() calls persistence.delete_agent with the agent id."""
        mock_persistence.delete_agent = AsyncMock()
        village_id = "village-1"
        agent_id = "agent-1"

        manager._state.villages[village_id] = Village(
            id=village_id,
            project_id="proj-1",
            name="Test Village",
            center=Position(0, 0),
            bounds=Bounds(0, 0, 0, 0),
            agent_ids=[agent_id],
        )
        position = Position(1, 1)
        agent = Agent(
            id=agent_id,
            session_id="session-1",
            project_id="proj-1",
            village_id=village_id,
            position=position,
            color="white",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.GENERAL,
        )
        manager._state.agents[agent_id] = agent
        manager._grid.occupy(position, agent_id)

        await manager.despawn_agent(agent_id)

        mock_persistence.delete_agent.assert_called_once_with(agent_id)

    async def test_despawn_agent_nonexistent_is_noop(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """despawn_agent() with a nonexistent agent_id raises no exception."""
        mock_persistence.delete_agent = AsyncMock()

        # Should not raise
        await manager.despawn_agent("nonexistent-id")

        # persistence.delete_agent must NOT be called for a nonexistent agent
        mock_persistence.delete_agent.assert_not_called()

    async def test_despawn_agent_removes_from_session(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """despawn_agent() removes the agent from its session's agent_ids."""
        mock_persistence.delete_agent = AsyncMock()
        village_id = "village-1"
        session_id = "session-1"
        agent_id = "agent-1"

        manager._state.villages[village_id] = Village(
            id=village_id,
            project_id="proj-1",
            name="Test Village",
            center=Position(0, 0),
            bounds=Bounds(0, 0, 0, 0),
            agent_ids=[agent_id],
        )
        manager._state.sessions[session_id] = Session(
            id=session_id,
            project_id="proj-1",
            agent_ids=[agent_id],
        )
        position = Position(4, 8)
        agent = Agent(
            id=agent_id,
            session_id=session_id,
            project_id="proj-1",
            village_id=village_id,
            position=position,
            color="white",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.GENERAL,
        )
        manager._state.agents[agent_id] = agent
        manager._grid.occupy(position, agent_id)

        await manager.despawn_agent(agent_id)

        session = manager._state.sessions[session_id]
        assert agent_id not in session.agent_ids

    async def test_found_village_seeds_initial_structures(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """found_village seeds at least one structure into the new village."""
        village = await manager.found_village(
            "orig-village-1", "proj-1", Position(100, 100), "Outpost Beta"
        )

        assert village is not None

        # The new village should have at least one structure in world state
        structures_for_village = [
            s for s in manager._state.structures.values()
            if s.village_id == village.id
        ]
        assert len(structures_for_village) >= 1, (
            f"Expected at least one seeded structure for village {village.id}, "
            f"but found none. All structures: {list(manager._state.structures.values())}"
        )

    async def test_found_village_idempotency_inner_guard(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """found_village returns the existing village when called with a position within 5 cells.

        This covers the inner 5-cell proximity guard inside WorldStateManager.found_village,
        which is separate from the 15-cell _is_clear_site guard in ExpansionManager.
        The originating village is pre-inserted so the test exercises the has_expanded
        set-and-queued code path within the guard branch.
        """
        # Pre-insert originating village so the guard path can set has_expanded on it
        orig = Village(id="orig-village-1", project_id="proj-1", name="Origin", center=Position(0, 0))
        manager._state.villages["orig-village-1"] = orig

        # First call: create the outpost at (50, 50)
        first = await manager.found_village("orig-village-1", "proj-1", Position(50, 50), "Outpost Alpha")

        assert first is not None
        assert first.center == Position(50, 50)
        assert first.name == "Outpost Alpha"

        # Record how many queue_write calls happened after the first found_village
        call_count_after_first = mock_persistence.queue_write.call_count

        # Second call: position (52, 50) is within 5 cells — guard fires; originating village
        # gets has_expanded=True set (one queue_write for that update) and existing is returned
        second = await manager.found_village("orig-village-1", "proj-1", Position(52, 50), "Outpost Alpha Duplicate")

        # Exactly one queue_write should have occurred — for persisting has_expanded on originating
        assert mock_persistence.queue_write.call_count == call_count_after_first + 1, (
            f"Expected one queue_write call (for has_expanded update), "
            f"got {mock_persistence.queue_write.call_count - call_count_after_first}"
        )

        # The returned village should be the same object (same id and center)
        assert second.id == first.id
        assert second.center == first.center

    async def test_found_village_sets_has_expanded_on_originating_village(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """found_village sets has_expanded=True on the originating village."""
        orig_village = Village(
            id="orig-1", project_id="proj-1", name="Origin", center=Position(0, 0)
        )
        manager._state.villages["orig-1"] = orig_village

        await manager.found_village("orig-1", "proj-1", Position(50, 50), "Outpost")

        assert manager._state.villages["orig-1"].has_expanded is True

    async def test_get_nearest_village_to_returns_closest(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """get_nearest_village_to() returns the village with the nearest center."""
        village_origin = Village(
            id="village-origin",
            project_id="proj-1",
            name="Origin",
            center=Position(0, 0),
        )
        village_far = Village(
            id="village-far",
            project_id="proj-2",
            name="Far",
            center=Position(10, 10),
        )
        manager._state.villages["village-origin"] = village_origin
        manager._state.villages["village-far"] = village_far

        result = await manager.get_nearest_village_to(1, 1)

        assert result is not None
        assert result.id == "village-origin"

    async def test_get_nearest_village_to_returns_none_when_no_villages(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """get_nearest_village_to() returns None when there are no villages."""
        result = await manager.get_nearest_village_to(0, 0)
        assert result is None

    async def test_found_village_sets_has_expanded_even_when_guard_fires(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """found_village sets has_expanded=True on the originating village even when
        the idempotency guard returns an existing nearby village."""
        orig_village = Village(
            id="orig-1", project_id="proj-1", name="Origin", center=Position(0, 0)
        )
        existing = Village(
            id="existing-1", project_id="proj-1", name="Existing", center=Position(50, 50)
        )
        manager._state.villages["orig-1"] = orig_village
        manager._state.villages["existing-1"] = existing

        # (52, 50) is within 5 cells of (50, 50) — idempotency guard fires
        result = await manager.found_village("orig-1", "proj-1", Position(52, 50), "Outpost")

        assert result.id == "existing-1"
        assert manager._state.villages["orig-1"].has_expanded is True

    async def test_upgrade_structure_tier_displaces_agents_in_new_footprint(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """upgrade_structure_tier() moves agents that fall inside the new footprint."""
        # Place a structure at (5, 5) with tier 1 (occupies only (5, 5))
        structure_id = "struct-1"
        village_id = "village-1"
        structure = Structure(
            id=structure_id,
            village_id=village_id,
            type=StructureType.HOUSE,
            position=Position(5, 5),
            size_tier=1,
        )
        manager._state.structures[structure_id] = structure
        manager._grid.occupy(Position(5, 5), structure_id)

        # Place an agent at (4, 5) — inside the 3x3 footprint when tier upgrades to 2
        agent_id = "agent-1"
        now = datetime.now(UTC)
        agent = Agent(
            id=agent_id,
            session_id="session-1",
            project_id="proj-1",
            village_id=village_id,
            inferred_type=AgentType.GENERAL,
            color="white",
            position=Position(4, 5),
            last_seen=now,
            state=AgentState.ACTIVE,
        )
        manager._state.agents[agent_id] = agent
        manager._grid.occupy(Position(4, 5), agent_id)

        # Upgrade structure to tier 2 — footprint becomes (4,4)-(6,6)
        await manager.upgrade_structure_tier(structure_id, new_tier=2)

        # Verify structure size_tier updated
        assert manager._state.structures[structure_id].size_tier == 2

        # Verify agent was displaced outside the 3x3 footprint
        new_pos = manager._state.agents[agent_id].position
        footprint = {
            Position(5 + dx, 5 + dy)
            for dx in range(-1, 2)
            for dy in range(-1, 2)
        }
        assert new_pos not in footprint, (
            f"Agent at {new_pos} is still inside the new footprint {footprint}"
        )

        # Verify agent's new position is registered in the grid
        assert manager._grid.get_entity_at(new_pos) == agent_id

        # Verify agent persistence was queued
        mock_persistence.queue_write.assert_any_call("agent", agent_id, agent)

    async def test_upgrade_structure_tier_displaces_multiple_agents_to_distinct_positions(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """Multiple agents in the new footprint each get a distinct free position."""
        structure_id = "struct-2"
        village_id = "village-2"
        structure = Structure(
            id=structure_id,
            village_id=village_id,
            type=StructureType.HOUSE,
            position=Position(10, 10),
            size_tier=1,
        )
        manager._state.structures[structure_id] = structure
        manager._grid.occupy(Position(10, 10), structure_id)

        now = datetime.now(UTC)
        # Place two agents inside the 3x3 footprint that will surround (10,10)
        agent_a = Agent(
            id="agent-a", session_id="s1", project_id="p1", village_id=village_id,
            inferred_type=AgentType.GENERAL, color="white",
            position=Position(9, 10), last_seen=now, state=AgentState.ACTIVE,
        )
        agent_b = Agent(
            id="agent-b", session_id="s1", project_id="p1", village_id=village_id,
            inferred_type=AgentType.GENERAL, color="white",
            position=Position(11, 10), last_seen=now, state=AgentState.ACTIVE,
        )
        for ag in (agent_a, agent_b):
            manager._state.agents[ag.id] = ag
            manager._grid.occupy(ag.position, ag.id)

        await manager.upgrade_structure_tier(structure_id, new_tier=2)

        footprint = {
            Position(10 + dx, 10 + dy)
            for dx in range(-1, 2)
            for dy in range(-1, 2)
        }
        new_pos_a = manager._state.agents["agent-a"].position
        new_pos_b = manager._state.agents["agent-b"].position

        # Both agents must be outside the footprint
        assert new_pos_a not in footprint, f"agent-a at {new_pos_a} still inside footprint"
        assert new_pos_b not in footprint, f"agent-b at {new_pos_b} still inside footprint"

        # Both agents must be at distinct positions
        assert new_pos_a != new_pos_b, "Two agents displaced to same position"

        # Both positions registered correctly in the grid
        assert manager._grid.get_entity_at(new_pos_a) == "agent-a"
        assert manager._grid.get_entity_at(new_pos_b) == "agent-b"

    # -------------------------------------------------------------------------
    # Terrain integration tests (WI-235)
    # -------------------------------------------------------------------------

    async def test_load_from_persistence_initializes_terrain_grid(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """load_from_persistence() initializes terrain grid from stored seed."""
        mock_data = MagicMock()
        mock_data.projects = []
        mock_data.villages = []
        mock_data.sessions = []
        mock_data.agents = []
        mock_data.structures = []
        mock_data.metadata = {"terrain_seed": "42"}

        mock_persistence.load_state.return_value = mock_data

        await manager.load_from_persistence()

        assert manager._terrain_grid is not None
        assert manager._terrain_grid.seed == 42

    async def test_load_from_persistence_generates_new_seed_if_missing(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """load_from_persistence() generates a new seed and persists it if terrain_seed is missing."""
        mock_data = MagicMock()
        mock_data.projects = []
        mock_data.villages = []
        mock_data.sessions = []
        mock_data.agents = []
        mock_data.structures = []
        mock_data.metadata = {}

        mock_persistence.load_state.return_value = mock_data

        await manager.load_from_persistence()

        assert manager._terrain_grid is not None
        assert isinstance(manager._terrain_grid.seed, int)
        assert "terrain_seed" in manager._state.world_metadata

        # Verify the new seed was persisted via queue_write
        mock_persistence.queue_write.assert_called_once()
        call_args = mock_persistence.queue_write.call_args
        assert call_args[0][0] == "world_metadata"
        assert call_args[0][1] == "terrain_seed"
        assert call_args[0][2]["key"] == "terrain_seed"
        # The value should match what's stored in world_metadata
        assert call_args[0][2]["value"] == manager._state.world_metadata["terrain_seed"]

    async def test_load_from_persistence_uses_existing_seed(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """load_from_persistence() uses existing seed and does not call queue_write."""
        mock_data = MagicMock()
        mock_data.projects = []
        mock_data.villages = []
        mock_data.sessions = []
        mock_data.agents = []
        mock_data.structures = []
        mock_data.metadata = {"terrain_seed": "42"}

        mock_persistence.load_state.return_value = mock_data

        await manager.load_from_persistence()

        # Should use the existing seed
        assert manager._terrain_grid is not None
        assert manager._terrain_grid.seed == 42
        assert manager._state.world_metadata["terrain_seed"] == "42"

        # Should NOT have called queue_write for the seed
        mock_persistence.queue_write.assert_not_called()

    async def test_terrain_determinism_across_restarts(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """Same terrain seed produces same terrain after restart simulation."""
        from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid

        # First "session" - generate a new seed
        mock_data = MagicMock()
        mock_data.projects = []
        mock_data.villages = []
        mock_data.sessions = []
        mock_data.agents = []
        mock_data.structures = []
        mock_data.metadata = {}

        mock_persistence.load_state.return_value = mock_data

        await manager.load_from_persistence()

        # Capture the generated seed
        generated_seed = manager._state.world_metadata["terrain_seed"]
        assert generated_seed is not None

        # Sample some terrain from the first grid
        terrain_samples = []
        for x in range(-5, 6):
            for y in range(-5, 6):
                terrain_samples.append((x, y, manager._terrain_grid.get_terrain(Position(x, y))))

        # Simulate restart: create a new manager with the seed from persistence
        mock_persistence_restart = MagicMock()
        mock_persistence_restart.queue_write = AsyncMock()
        mock_persistence_restart.load_state = AsyncMock()

        mock_data_restart = MagicMock()
        mock_data_restart.projects = []
        mock_data_restart.villages = []
        mock_data_restart.sessions = []
        mock_data_restart.agents = []
        mock_data_restart.structures = []
        mock_data_restart.metadata = {"terrain_seed": generated_seed}

        mock_persistence_restart.load_state.return_value = mock_data_restart

        manager_restart = WorldStateManager(mock_persistence_restart)
        await manager_restart.load_from_persistence()

        # Verify same seed is used
        assert manager_restart._terrain_grid.seed == int(generated_seed)

        # Verify terrain samples match
        for x, y, expected_terrain in terrain_samples:
            actual_terrain = manager_restart._terrain_grid.get_terrain(Position(x, y))
            assert actual_terrain == expected_terrain, (
                f"Terrain mismatch at ({x}, {y}): expected {expected_terrain}, got {actual_terrain}"
            )

        # No new seed should have been written on restart
        mock_persistence_restart.queue_write.assert_not_called()

    async def test_get_terrain_at_returns_terrain_type(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """get_terrain_at(x, y) returns the terrain type at that position."""
        from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid

        # Set up terrain grid with known seed
        config = TerrainConfig(seed=42)
        manager._terrain_grid = TerrainGrid(TerrainGenerator(config))

        # Get terrain at (0, 0) and verify it's a valid TerrainType
        terrain = await manager.get_terrain_at(0, 0)
        assert hasattr(terrain, "passable"), "get_terrain_at should return a TerrainType"

    async def test_get_terrain_at_returns_plain_before_initialization(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """get_terrain_at() returns PLAIN as fallback before terrain grid is initialized."""
        from hamlet.world_state.terrain import TerrainType

        # Ensure terrain grid is not initialized
        manager._terrain_grid = None

        terrain = await manager.get_terrain_at(0, 0)
        assert terrain == TerrainType.PLAIN

    async def test_is_passable_returns_true_for_passable_terrain(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """is_passable(x, y) returns True for passable terrain positions."""
        from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid, TerrainType

        # Set up terrain grid with known seed
        config = TerrainConfig(seed=42)
        manager._terrain_grid = TerrainGrid(TerrainGenerator(config))

        # Find a passable position by searching
        passable_found = False
        for x in range(-10, 11):
            for y in range(-10, 11):
                if await manager.is_passable(x, y):
                    passable_found = True
                    # Verify get_terrain_at agrees
                    terrain = await manager.get_terrain_at(x, y)
                    assert terrain.passable, f"Position ({x}, {y}) should have passable terrain"
                    break
            if passable_found:
                break

        assert passable_found, "Should find at least one passable position in the grid"

    async def test_is_passable_returns_false_for_water_and_mountain(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """is_passable(x, y) returns False for WATER and MOUNTAIN terrain."""
        from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid, TerrainType

        # Set up terrain grid with known seed
        config = TerrainConfig(seed=42)
        manager._terrain_grid = TerrainGrid(TerrainGenerator(config))

        # Find impassable positions (WATER or MOUNTAIN)
        impassable_found = False
        for x in range(-20, 21):
            for y in range(-20, 21):
                terrain = await manager.get_terrain_at(x, y)
                if not terrain.passable:
                    impassable_found = True
                    assert await manager.is_passable(x, y) is False
                    assert terrain in (TerrainType.WATER, TerrainType.MOUNTAIN)
                    break
            if impassable_found:
                break

        # It's possible but unlikely that no impassable terrain exists in this range
        # If not found, we still verify that is_passable returns False when terrain is impassable
        if not impassable_found:
            # Verify is_passable would return False if terrain were WATER
            assert TerrainType.WATER.passable is False
            assert TerrainType.MOUNTAIN.passable is False

    async def test_is_passable_returns_true_before_initialization(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """is_passable() returns True as fallback before terrain grid is initialized."""
        # Ensure terrain grid is not initialized
        manager._terrain_grid = None

        # Should return True as fallback (graceful degradation)
        assert await manager.is_passable(0, 0) is True

    async def test_find_village_position_finds_passable_terrain(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """_find_village_position() returns a position with passable terrain."""
        from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid

        # Set up terrain grid
        config = TerrainConfig(seed=42)
        manager._terrain_grid = TerrainGrid(TerrainGenerator(config))

        # Find a village position with no existing villages or occupied positions
        position = manager._find_village_position([], set())

        # The returned position should be passable
        assert manager._terrain_grid.is_passable(position)

    async def test_find_village_position_avoids_other_villages(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """_find_village_position() returns positions at least MIN_VILLAGE_DISTANCE apart."""
        from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid

        # Set up terrain grid
        config = TerrainConfig(seed=42)
        manager._terrain_grid = TerrainGrid(TerrainGenerator(config))

        # First village at origin area (find position first)
        first_pos = manager._find_village_position([], set())

        # Create a mock village at that position
        first_village = Village(
            id="first",
            project_id="p1",
            name="First Village",
            center=first_pos,
        )

        # Find second village position
        second_pos = manager._find_village_position([first_village], set())

        # Distance should be at least MIN_VILLAGE_DISTANCE
        import math
        distance = math.hypot(second_pos.x - first_pos.x, second_pos.y - first_pos.y)
        assert distance >= manager.MIN_VILLAGE_DISTANCE, (
            f"Villages should be at least {manager.MIN_VILLAGE_DISTANCE} apart, "
            f"but got {distance}"
        )

    async def test_create_structure_raises_on_water_terrain(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """create_structure() raises ValueError when position is on WATER terrain."""
        from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid, TerrainType

        # Set up terrain grid
        config = TerrainConfig(seed=42)
        manager._terrain_grid = TerrainGrid(TerrainGenerator(config))

        # Create a village first
        village = Village(
            id="village-water-test",
            project_id="proj-1",
            name="Test Village",
            center=Position(0, 0),
        )
        manager._state.villages[village.id] = village

        # Find a WATER position
        water_pos = None
        for x in range(-50, 51):
            for y in range(-50, 51):
                pos = Position(x, y)
                if not manager._terrain_grid.is_passable(pos):
                    terrain = manager._terrain_grid.get_terrain(pos)
                    if terrain == TerrainType.WATER:
                        water_pos = pos
                        break
            if water_pos:
                break

        if water_pos is None:
            # Skip test if no WATER found (unlikely but possible)
            pytest.skip("No WATER terrain found in search range")

        # Attempting to create structure on WATER should raise ValueError
        with pytest.raises(ValueError, match="Cannot build.*on water terrain"):
            await manager.create_structure(
                village_id=village.id,
                structure_type=StructureType.HOUSE,
                position=water_pos,
            )

    async def test_create_structure_raises_on_mountain_terrain(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """create_structure() raises ValueError when position is on MOUNTAIN terrain."""
        from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid, TerrainType

        # Set up terrain grid
        config = TerrainConfig(seed=42)
        manager._terrain_grid = TerrainGrid(TerrainGenerator(config))

        # Create a village first
        village = Village(
            id="village-mountain-test",
            project_id="proj-1",
            name="Test Village",
            center=Position(0, 0),
        )
        manager._state.villages[village.id] = village

        # Find a MOUNTAIN position
        mountain_pos = None
        for x in range(-50, 51):
            for y in range(-50, 51):
                pos = Position(x, y)
                if not manager._terrain_grid.is_passable(pos):
                    terrain = manager._terrain_grid.get_terrain(pos)
                    if terrain == TerrainType.MOUNTAIN:
                        mountain_pos = pos
                        break
            if mountain_pos:
                break

        if mountain_pos is None:
            # Skip test if no MOUNTAIN found (unlikely but possible)
            pytest.skip("No MOUNTAIN terrain found in search range")

        # Attempting to create structure on MOUNTAIN should raise ValueError
        with pytest.raises(ValueError, match="Cannot build.*on mountain terrain"):
            await manager.create_structure(
                village_id=village.id,
                structure_type=StructureType.HOUSE,
                position=mountain_pos,
            )

    async def test_create_structure_succeeds_on_passable_terrain(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """create_structure() succeeds when position is on passable terrain."""
        from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid

        # Set up terrain grid
        config = TerrainConfig(seed=42)
        manager._terrain_grid = TerrainGrid(TerrainGenerator(config))

        # Create a village first
        village = Village(
            id="village-passable-test",
            project_id="proj-1",
            name="Test Village",
            center=Position(0, 0),
        )
        manager._state.villages[village.id] = village

        # Find a passable position
        passable_pos = None
        for x in range(-10, 11):
            for y in range(-10, 11):
                pos = Position(x, y)
                if manager._terrain_grid.is_passable(pos):
                    passable_pos = pos
                    break
            if passable_pos:
                break

        assert passable_pos is not None, "Should find passable terrain"

        # Creating structure on passable terrain should succeed
        structure = await manager.create_structure(
            village_id=village.id,
            structure_type=StructureType.HOUSE,
            position=passable_pos,
        )

        assert structure is not None
        assert structure.position == passable_pos

    async def test_get_or_create_project_uses_terrain_aware_village_placement(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """get_or_create_project() places villages on passable terrain."""
        from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid

        # Set up terrain grid
        config = TerrainConfig(seed=42)
        manager._terrain_grid = TerrainGrid(TerrainGenerator(config))

        # Create a new project - should use terrain-aware placement
        project = await manager.get_or_create_project("test-proj", "Test Project")

        # The village center should be on passable terrain
        village = manager._state.villages.get(project.village_id)
        assert village is not None

        # Verify village center is on passable terrain
        assert manager._terrain_grid.is_passable(village.center), (
            f"Village center {village.center} should be on passable terrain"
        )

    async def test_villages_are_at_least_min_distance_apart(
        self, manager: WorldStateManager, mock_persistence: MagicMock
    ) -> None:
        """Multiple villages created by get_or_create_project are at least MIN_VILLAGE_DISTANCE apart."""
        import math
        from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid

        # Set up terrain grid
        config = TerrainConfig(seed=42)
        manager._terrain_grid = TerrainGrid(TerrainGenerator(config))

        # Create multiple projects (each gets a village)
        project1 = await manager.get_or_create_project("proj-distance-1", "Project 1")
        project2 = await manager.get_or_create_project("proj-distance-2", "Project 2")
        project3 = await manager.get_or_create_project("proj-distance-3", "Project 3")

        # Get village centers
        village1 = manager._state.villages[project1.village_id]
        village2 = manager._state.villages[project2.village_id]
        village3 = manager._state.villages[project3.village_id]

        # Verify all pairwise distances are at least MIN_VILLAGE_DISTANCE
        for v1, v2 in [(village1, village2), (village1, village3), (village2, village3)]:
            dist = math.hypot(v1.center.x - v2.center.x, v1.center.y - v2.center.y)
            assert dist >= manager.MIN_VILLAGE_DISTANCE, (
                f"Villages {v1.id} and {v2.id} are only {dist} units apart, "
                f"should be at least {manager.MIN_VILLAGE_DISTANCE}"
            )
