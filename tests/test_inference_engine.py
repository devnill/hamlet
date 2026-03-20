"""Tests for AgentInferenceEngine._handle_stop stop_reason behavioural differentiation (WI-197)."""
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
    engine = AgentInferenceEngine(world_state=world_state)
    return engine, world_state


async def test_stop_tool_reason_flushes_pending_and_marks_idle() -> None:
    """stop_reason='tool' evicts pending tools for the session and marks agents IDLE."""
    engine, world_state = _make_engine()
    session_id = str(uuid4())
    agent_id = str(uuid4())

    # Set up session with one agent and two pending tools
    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
        active_tools=2,
    )
    pt1_key = str(uuid4())
    pt2_key = str(uuid4())
    engine._state.pending_tools[pt1_key] = PendingTool(session_id=session_id, tool_name="Read")
    engine._state.pending_tools[pt2_key] = PendingTool(session_id=session_id, tool_name="Write")
    # Also add a pending tool for a different session (should not be evicted)
    other_session_key = str(uuid4())
    engine._state.pending_tools[other_session_key] = PendingTool(
        session_id=str(uuid4()), tool_name="Bash"
    )

    event = _make_stop_event(session_id, "tool")
    await engine._handle_stop(event)

    # Pending tools for this session are gone
    assert pt1_key not in engine._state.pending_tools
    assert pt2_key not in engine._state.pending_tools
    # Other session's pending tool is untouched
    assert other_session_key in engine._state.pending_tools
    # active_tools decremented to 0
    assert engine._state.sessions[session_id].active_tools == 0
    # Agent marked IDLE
    world_state.update_agent.assert_awaited_once_with(agent_id, state=AgentState.IDLE)


async def test_stop_clean_reason_marks_idle() -> None:
    """stop_reason='stop' marks session agents IDLE without touching pending tools."""
    engine, world_state = _make_engine()
    session_id = str(uuid4())
    agent_id = str(uuid4())

    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
        active_tools=0,
    )
    # Add a pending tool that should NOT be evicted (clean stop)
    pt_key = str(uuid4())
    engine._state.pending_tools[pt_key] = PendingTool(session_id=session_id, tool_name="Read")

    event = _make_stop_event(session_id, "stop")
    await engine._handle_stop(event)

    # Pending tools not touched on clean stop
    assert pt_key in engine._state.pending_tools
    # Agent marked IDLE
    world_state.update_agent.assert_awaited_once_with(agent_id, state=AgentState.IDLE)


async def test_stop_end_turn_reason_marks_idle() -> None:
    """stop_reason='end_turn' marks session agents IDLE (normal Claude Code session end)."""
    engine, world_state = _make_engine()
    session_id = str(uuid4())
    agent_id = str(uuid4())

    engine._state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
        active_tools=0,
    )
    # Pending tool should NOT be evicted — end_turn is a clean stop, not an interrupted tool
    pt_key = str(uuid4())
    engine._state.pending_tools[pt_key] = PendingTool(session_id=session_id, tool_name="Read")

    event = _make_stop_event(session_id, "end_turn")
    await engine._handle_stop(event)

    # Pending tools not touched (end_turn is not a tool interruption)
    assert pt_key in engine._state.pending_tools
    # Agent marked IDLE
    world_state.update_agent.assert_awaited_once_with(agent_id, state=AgentState.IDLE)


async def test_stop_no_reason_does_not_mark_idle() -> None:
    """stop_reason=None does NOT mark agents IDLE — zombie TTL handles them."""
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

    # No IDLE transition
    world_state.update_agent.assert_not_awaited()
