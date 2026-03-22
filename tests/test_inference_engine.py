"""Tests for AgentInferenceEngine._handle_stop stop_reason behavioural differentiation (WI-222)."""
from __future__ import annotations

from datetime import UTC, datetime
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


def _make_engine() -> tuple[AgentInferenceEngine, MagicMock]:
    world_state = MagicMock()
    world_state.update_agent = AsyncMock()
    world_state.despawn_agent = AsyncMock()
    engine = AgentInferenceEngine(world_state=world_state)
    return engine, world_state




async def test_stop_reason_tool_transitions_to_zombie() -> None:
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


async def test_stop_reason_stop_calls_despawn() -> None:
    engine, world_state = _make_engine()
    session_id = str(uuid4())
    agent_id = str(uuid4())
    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
        active_tools=0,
    )
    engine._state.last_seen[agent_id] = datetime.now(UTC)
    event = _make_stop_event(session_id, "stop")
    await engine._handle_stop(event)
    world_state.despawn_agent.assert_awaited_once_with(agent_id)
    world_state.update_agent.assert_not_awaited()
    assert agent_id not in engine._state.last_seen


async def test_stop_reason_end_turn_calls_despawn() -> None:
    engine, world_state = _make_engine()
    session_id = str(uuid4())
    agent_id = str(uuid4())
    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
        active_tools=0,
    )
    engine._state.last_seen[agent_id] = datetime.now(UTC)
    event = _make_stop_event(session_id, "end_turn")
    await engine._handle_stop(event)
    world_state.despawn_agent.assert_awaited_once_with(agent_id)
    world_state.update_agent.assert_not_awaited()
    assert agent_id not in engine._state.last_seen


async def test_stop_reason_none_no_state_change() -> None:
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
    world_state.despawn_agent.assert_not_awaited()
    world_state.update_agent.assert_not_awaited()
