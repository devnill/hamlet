"""Tests for AgentInferenceEngine handler behaviour (WI-222, WI-296)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from hamlet.event_processing.internal_event import HookType, InternalEvent
from hamlet.inference.engine import AgentInferenceEngine
from hamlet.inference.types import PendingTool, SessionState
from hamlet.world_state.types import AgentState


def _make_stop_event(session_id: str, stop_reason: str | None) -> InternalEvent:
    return InternalEvent(
        id=str(uuid4()),
        sequence=1,
        received_at=datetime.now(UTC),
        session_id=session_id,
        project_id="proj-1",
        project_name="proj-1",
        hook_type=HookType.Stop,
        stop_reason=stop_reason,
    )


def _make_engine(despawn_threshold_seconds: int | None = None) -> tuple[AgentInferenceEngine, MagicMock]:
    world_state = MagicMock()
    world_state.update_agent = AsyncMock()
    world_state.despawn_agent = AsyncMock()
    kwargs = {}
    if despawn_threshold_seconds is not None:
        kwargs["despawn_threshold_seconds"] = despawn_threshold_seconds
    engine = AgentInferenceEngine(world_state=world_state, **kwargs)
    return engine, world_state


async def test_stop_reason_tool_transitions_to_zombie() -> None:
    """stop_reason='tool' transitions agents to ZOMBIE and clears pending tools."""
    engine, world_state = _make_engine()
    session_id = str(uuid4())
    agent_id = str(uuid4())
    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
        active_tools=1,
    )
    pt_key = str(uuid4())
    engine._state.pending_tools[pt_key] = PendingTool(session_id=session_id, tool_name="Read")
    event = _make_stop_event(session_id, "tool")
    await engine._handle_stop(event)
    world_state.update_agent.assert_awaited_once_with(agent_id, state=AgentState.ZOMBIE)
    world_state.despawn_agent.assert_not_awaited()
    assert agent_id in engine._state.zombie_since
    assert pt_key not in engine._state.pending_tools


async def test_stop_clean_reason_despawns() -> None:
    """stop_reason='stop' despawns session agents without touching pending tools."""
    engine, world_state = _make_engine()
    session_id = str(uuid4())
    agent_id = str(uuid4())
    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
        active_tools=0,
    )
    # Pre-seed last_seen and zombie_since for the agent
    engine._state.last_seen[agent_id] = datetime.now(UTC)
    engine._state.zombie_since[agent_id] = datetime.now(UTC)
    # Add a pending tool that should NOT be evicted (clean stop)
    pt_key = str(uuid4())
    engine._state.pending_tools[pt_key] = PendingTool(session_id=session_id, tool_name="Read")

    event = _make_stop_event(session_id, "stop")
    await engine._handle_stop(event)

    # Pending tools not touched on clean stop
    assert pt_key in engine._state.pending_tools
    # Agent despawned
    world_state.despawn_agent.assert_awaited_once_with(agent_id)
    # Inference state cleaned up for this agent
    assert agent_id not in engine._state.last_seen
    assert agent_id not in engine._state.zombie_since


async def test_stop_end_turn_reason_despawns() -> None:
    """stop_reason='end_turn' despawns session agents (normal Claude Code session end)."""
    engine, world_state = _make_engine()
    session_id = str(uuid4())
    agent_id = str(uuid4())
    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
        active_tools=0,
    )
    # Pre-seed last_seen and zombie_since for the agent
    engine._state.last_seen[agent_id] = datetime.now(UTC)
    engine._state.zombie_since[agent_id] = datetime.now(UTC)
    # Pending tool should NOT be evicted — end_turn is a clean stop, not an interrupted tool
    pt_key = str(uuid4())
    engine._state.pending_tools[pt_key] = PendingTool(session_id=session_id, tool_name="Read")

    event = _make_stop_event(session_id, "end_turn")
    await engine._handle_stop(event)

    # Pending tools not touched (end_turn is not a tool interruption)
    assert pt_key in engine._state.pending_tools
    # Agent despawned
    world_state.despawn_agent.assert_awaited_once_with(agent_id)
    # Inference state cleaned up for this agent
    assert agent_id not in engine._state.last_seen
    assert agent_id not in engine._state.zombie_since


async def test_stop_no_reason_does_not_despawn() -> None:
    """stop_reason=None does NOT despawn agents — zombie TTL handles them."""
    engine, world_state = _make_engine()
    session_id = str(uuid4())
    agent_id = str(uuid4())
    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
        active_tools=0,
    )
    event = _make_stop_event(session_id, None)
    await engine._handle_stop(event)

    # No despawn, no IDLE transition
    world_state.despawn_agent.assert_not_awaited()
    world_state.update_agent.assert_not_awaited()


async def test_stop_despawns_all_session_agents() -> None:
    """Session end despawns all agents associated with the session."""
    engine, world_state = _make_engine()
    session_id = str(uuid4())
    agent_id_1 = str(uuid4())
    agent_id_2 = str(uuid4())

    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id_1, agent_id_2],
        active_tools=0,
    )
    # Seed last_seen and zombie_since for the agents
    engine._state.last_seen[agent_id_1] = datetime.now(UTC)
    engine._state.last_seen[agent_id_2] = datetime.now(UTC)
    engine._state.zombie_since[agent_id_1] = datetime.now(UTC)

    event = _make_stop_event(session_id, "end_turn")
    await engine._handle_stop(event)

    # Both agents despawned
    despawned_ids = {call.args[0] for call in world_state.despawn_agent.await_args_list}
    assert agent_id_1 in despawned_ids
    assert agent_id_2 in despawned_ids
    # Inference state cleaned up for both agents
    assert agent_id_1 not in engine._state.last_seen
    assert agent_id_2 not in engine._state.last_seen
    assert agent_id_1 not in engine._state.zombie_since


async def test_zombie_ttl_despawn() -> None:
    """Agents in zombie_since past DESPAWN_THRESHOLD_SECONDS are despawned on tick."""
    engine, world_state = _make_engine(despawn_threshold_seconds=300)
    agent_id = str(uuid4())

    # Put agent in zombie_since with an old timestamp (well past threshold)
    old_time = datetime.now(UTC) - timedelta(seconds=400)
    engine._state.zombie_since[agent_id] = old_time
    engine._state.last_seen[agent_id] = old_time

    await engine.tick()

    world_state.despawn_agent.assert_awaited_once_with(agent_id)
    assert agent_id not in engine._state.last_seen
    assert agent_id not in engine._state.zombie_since


async def test_zombie_ttl_no_despawn_for_recent_zombie() -> None:
    """Agents that became zombies recently are NOT despawned during tick."""
    engine, world_state = _make_engine(despawn_threshold_seconds=300)
    agent_id = str(uuid4())

    # Put agent in zombie_since with a very recent timestamp
    recent_time = datetime.now(UTC) - timedelta(seconds=10)
    engine._state.zombie_since[agent_id] = recent_time
    # Make last_seen old enough to be a zombie but not old enough for despawn
    engine._state.last_seen[agent_id] = datetime.now(UTC) - timedelta(seconds=400)

    await engine.tick()

    world_state.despawn_agent.assert_not_awaited()
    assert agent_id in engine._state.zombie_since


async def test_zombie_ttl_records_zombie_since_on_first_detection() -> None:
    """_update_zombie_states records zombie_since when an agent first becomes ZOMBIE."""
    engine, world_state = _make_engine()
    agent_id = str(uuid4())

    # Agent has stale last_seen (qualifies as zombie)
    stale_time = datetime.now(UTC) - timedelta(seconds=400)
    engine._state.last_seen[agent_id] = stale_time

    # zombie_since is empty initially
    assert agent_id not in engine._state.zombie_since

    await engine._update_zombie_states()

    world_state.update_agent.assert_awaited_once_with(agent_id, state=AgentState.ZOMBIE)
    assert agent_id in engine._state.zombie_since


async def test_zombie_ttl_does_not_overwrite_existing_zombie_since() -> None:
    """zombie_since is not overwritten if agent was already marked zombie."""
    engine, world_state = _make_engine()
    agent_id = str(uuid4())

    # Agent has stale last_seen (qualifies as zombie)
    stale_time = datetime.now(UTC) - timedelta(seconds=400)
    engine._state.last_seen[agent_id] = stale_time

    # zombie_since already set
    original_zombie_time = datetime.now(UTC) - timedelta(seconds=50)
    engine._state.zombie_since[agent_id] = original_zombie_time

    await engine._update_zombie_states()

    # zombie_since not overwritten
    assert engine._state.zombie_since.get(agent_id) == original_zombie_time


async def test_resurrection_after_despawn() -> None:
    """After despawn, a new PreToolUse for the same session creates a new agent."""
    engine, world_state = _make_engine()
    session_id = str(uuid4())
    agent_id = str(uuid4())
    new_agent_id = str(uuid4())

    # Set up a mock agent returned by get_or_create_agent
    mock_agent = MagicMock()
    mock_agent.id = new_agent_id
    world_state.get_or_create_project = AsyncMock()
    world_state.get_or_create_session = AsyncMock()
    world_state.get_or_create_agent = AsyncMock(return_value=mock_agent)
    world_state.get_agents_by_session = AsyncMock(return_value=[])

    # Simulate despawn — engine state is cleared for agent
    engine._state.last_seen.pop(agent_id, None)
    engine._state.zombie_since.pop(agent_id, None)
    # Session is also gone (despawn clears the world, new session starts fresh)
    # Do not add the old session to engine._state.sessions

    # Send a new PreToolUse for the same session
    pre_tool_event = InternalEvent(
        id=str(uuid4()),
        sequence=2,
        received_at=datetime.now(UTC),
        session_id=session_id,
        project_id="proj-1",
        project_name="proj-1",
        hook_type=HookType.PreToolUse,
        tool_name="Read",
        tool_input={"path": "/tmp/foo"},
    )
    await engine._handle_pre_tool_use(pre_tool_event)

    # A new agent was created
    world_state.get_or_create_agent.assert_awaited_once()
    # New agent is tracked in the session
    session = engine._state.sessions.get(session_id)
    assert session is not None
    assert new_agent_id in session.agent_ids


async def test_startup_seeds_zombie_since_from_world_state() -> None:
    """startup() seeds zombie_since from ZOMBIE agents already loaded in world state."""
    engine, world_state = _make_engine()

    zombie_time = datetime.now(UTC) - timedelta(seconds=200)
    active_time = datetime.now(UTC) - timedelta(seconds=10)

    zombie_agent = MagicMock()
    zombie_agent.id = str(uuid4())
    zombie_agent.state = AgentState.ZOMBIE
    zombie_agent.last_seen = zombie_time

    active_agent = MagicMock()
    active_agent.id = str(uuid4())
    active_agent.state = AgentState.ACTIVE
    active_agent.last_seen = active_time

    world_state.get_all_agents = AsyncMock(return_value=[zombie_agent, active_agent])

    await engine.startup()

    # ZOMBIE agent is seeded into zombie_since
    assert engine._state.zombie_since.get(zombie_agent.id) == zombie_time
    # ACTIVE agent is not seeded
    assert active_agent.id not in engine._state.zombie_since


# ---------------------------------------------------------------------------
# WI-296: newer hook type handlers
# ---------------------------------------------------------------------------


def _make_event(
    session_id: str,
    hook_type: HookType,
    project_id: str = "proj-1",
    project_name: str = "proj-1",
    agent_id: str | None = None,
    stop_reason: str | None = None,
) -> InternalEvent:
    return InternalEvent(
        id=str(uuid4()),
        sequence=1,
        received_at=datetime.now(UTC),
        session_id=session_id,
        project_id=project_id,
        project_name=project_name,
        hook_type=hook_type,
        agent_id=agent_id,
        stop_reason=stop_reason,
    )


def _make_engine_with_world_state() -> tuple[AgentInferenceEngine, MagicMock]:
    """Return an engine with a fully-mocked world state."""
    world_state = MagicMock()
    world_state.update_agent = AsyncMock()
    world_state.despawn_agent = AsyncMock()
    world_state.get_or_create_project = AsyncMock()
    world_state.get_or_create_session = AsyncMock()
    world_state.get_agents_by_session = AsyncMock(return_value=[])
    # Default: get_or_create_agent returns a mock agent with a stable id
    mock_agent = MagicMock()
    mock_agent.id = str(uuid4())
    world_state.get_or_create_agent = AsyncMock(return_value=mock_agent)
    engine = AgentInferenceEngine(world_state=world_state)
    return engine, world_state


async def test_session_start_creates_session_state_and_materialises_agent() -> None:
    """SessionStart creates session state, materialises agent, and updates last_seen."""
    engine, world_state = _make_engine_with_world_state()
    session_id = str(uuid4())
    event = _make_event(session_id, HookType.SessionStart)

    await engine.process_event(event)

    # Session state should now exist
    session = engine._state.sessions.get(session_id)
    assert session is not None
    assert session.session_id == session_id

    # World state materialisation calls must have been made
    world_state.get_or_create_project.assert_awaited_once()
    world_state.get_or_create_session.assert_awaited_once()
    world_state.get_or_create_agent.assert_awaited_once()

    # last_seen should be updated for the spawned agent
    agent_id = world_state.get_or_create_agent.return_value.id
    assert agent_id in engine._state.last_seen


async def test_session_start_idempotent_for_existing_session() -> None:
    """SessionStart on an already-tracked session does not duplicate agent_ids."""
    engine, world_state = _make_engine_with_world_state()
    session_id = str(uuid4())
    agent_id = world_state.get_or_create_agent.return_value.id

    # Pre-seed the session with the agent already in agent_ids.
    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
    )

    event = _make_event(session_id, HookType.SessionStart)
    await engine.process_event(event)

    session = engine._state.sessions[session_id]
    # agent_id should appear exactly once
    assert session.agent_ids.count(agent_id) == 1


async def test_session_end_marks_agents_zombie() -> None:
    """SessionEnd marks all session agents as ZOMBIE and records zombie_since."""
    engine, world_state = _make_engine_with_world_state()
    session_id = str(uuid4())
    agent_id_1 = str(uuid4())
    agent_id_2 = str(uuid4())

    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id_1, agent_id_2],
    )

    event = _make_event(session_id, HookType.SessionEnd)
    await engine.process_event(event)

    # Both agents should have been zombified
    zombied_ids = {call.args[0] for call in world_state.update_agent.await_args_list}
    assert agent_id_1 in zombied_ids
    assert agent_id_2 in zombied_ids

    # zombie_since should be recorded for both
    assert agent_id_1 in engine._state.zombie_since
    assert agent_id_2 in engine._state.zombie_since

    # despawn should NOT be called
    world_state.despawn_agent.assert_not_awaited()


async def test_session_end_no_session_is_noop() -> None:
    """SessionEnd for an unknown session does nothing (no crash, no world state calls)."""
    engine, world_state = _make_engine_with_world_state()
    session_id = str(uuid4())

    event = _make_event(session_id, HookType.SessionEnd)
    await engine.process_event(event)

    world_state.update_agent.assert_not_awaited()
    world_state.despawn_agent.assert_not_awaited()


async def test_subagent_start_spawns_agent_with_parent() -> None:
    """SubagentStart materialises a new agent using the session's primary as parent."""
    engine, world_state = _make_engine_with_world_state()
    session_id = str(uuid4())
    parent_agent_id = str(uuid4())

    # Set up a parent agent in the world state for get_agents_by_session
    parent_mock = MagicMock()
    parent_mock.id = parent_agent_id
    parent_mock.last_seen = datetime.now(UTC)
    world_state.get_agents_by_session = AsyncMock(return_value=[parent_mock])

    # New agent returned by get_or_create_agent
    new_agent_id = str(uuid4())
    new_agent_mock = MagicMock()
    new_agent_mock.id = new_agent_id
    world_state.get_or_create_agent = AsyncMock(return_value=new_agent_mock)

    event = _make_event(session_id, HookType.SubagentStart, agent_id=str(uuid4()))
    await engine.process_event(event)

    # Session should now exist
    session = engine._state.sessions.get(session_id)
    assert session is not None

    # Agent was created with parent_id
    world_state.get_or_create_agent.assert_awaited_once_with(session_id, parent_agent_id)

    # New agent in session.agent_ids
    assert new_agent_id in session.agent_ids

    # last_seen updated
    assert new_agent_id in engine._state.last_seen


async def test_subagent_stop_despawns_agent() -> None:
    """SubagentStop despawns the agent identified by event.agent_id."""
    engine, world_state = _make_engine_with_world_state()
    session_id = str(uuid4())
    agent_id = str(uuid4())

    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
    )
    engine._state.last_seen[agent_id] = datetime.now(UTC)
    engine._state.zombie_since[agent_id] = datetime.now(UTC)

    event = _make_event(session_id, HookType.SubagentStop, agent_id=agent_id)
    await engine.process_event(event)

    world_state.despawn_agent.assert_awaited_once_with(agent_id)
    assert agent_id not in engine._state.last_seen
    assert agent_id not in engine._state.zombie_since

    # Also removed from session.agent_ids
    session = engine._state.sessions[session_id]
    assert agent_id not in session.agent_ids


async def test_subagent_stop_no_agent_id_is_noop() -> None:
    """SubagentStop with no agent_id does nothing."""
    engine, world_state = _make_engine_with_world_state()
    session_id = str(uuid4())

    event = _make_event(session_id, HookType.SubagentStop, agent_id=None)
    await engine.process_event(event)

    world_state.despawn_agent.assert_not_awaited()


async def test_teammate_idle_updates_last_seen() -> None:
    """TeammateIdle refreshes last_seen for session agents."""
    engine, world_state = _make_engine_with_world_state()
    session_id = str(uuid4())
    agent_id = str(uuid4())

    old_time = datetime.now(UTC) - timedelta(seconds=60)
    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
    )
    engine._state.last_seen[agent_id] = old_time

    event = _make_event(session_id, HookType.TeammateIdle)
    await engine.process_event(event)

    # last_seen should have been refreshed to event.received_at
    assert engine._state.last_seen[agent_id] == event.received_at
    assert engine._state.last_seen[agent_id] > old_time


async def test_passthrough_hooks_update_last_seen() -> None:
    """Passthrough hook types (TaskCompleted, etc.) update last_seen for session agents."""
    engine, world_state = _make_engine_with_world_state()
    session_id = str(uuid4())
    agent_id = str(uuid4())

    old_time = datetime.now(UTC) - timedelta(seconds=120)
    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
    )
    engine._state.last_seen[agent_id] = old_time

    passthrough_types = [
        HookType.TaskCompleted,
        HookType.PostToolUseFailure,
        HookType.UserPromptSubmit,
        HookType.PreCompact,
        HookType.PostCompact,
        HookType.StopFailure,
    ]
    for hook_type in passthrough_types:
        event = _make_event(session_id, hook_type)
        await engine.process_event(event)
        assert engine._state.last_seen[agent_id] == event.received_at, (
            f"last_seen not updated for {hook_type}"
        )
