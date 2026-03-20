"""Tests for spawn detection in AgentInferenceEngine (work item 023).

Test framework: pytest + pytest-asyncio (see pyproject.toml dev dependencies).
Run with: pytest tests/test_spawn_detection.py -v
"""
from __future__ import annotations

from datetime import datetime, UTC
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from hamlet.event_processing.internal_event import HookType, InternalEvent
from hamlet.inference.engine import AgentInferenceEngine
from hamlet.inference.types import InferenceAction, SessionState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    session_id: str | None = None,
    project_id: str = "proj-1",
    hook_type: HookType = HookType.PreToolUse,
    tool_name: str = "Bash",
    event_id: str | None = None,
) -> InternalEvent:
    """Return a minimal InternalEvent for testing."""
    return InternalEvent(
        id=event_id or str(uuid4()),
        sequence=1,
        received_at=datetime.now(UTC),
        session_id=session_id or str(uuid4()),
        project_id=project_id,
        project_name="test-project",
        hook_type=hook_type,
        tool_name=tool_name,
        tool_input={"command": "ls"},
    )


def _make_world_state(agents: list[Any] | None = None) -> MagicMock:
    """Return a mock WorldStateManager with sensible defaults."""
    ws = MagicMock()
    mock_session = MagicMock()
    mock_session.id = str(uuid4())

    mock_agent = MagicMock()
    mock_agent.id = str(uuid4())
    mock_agent.last_seen = datetime.now(UTC)

    ws.get_or_create_project = AsyncMock()
    ws.get_or_create_session = AsyncMock(return_value=mock_session)
    ws.get_or_create_agent = AsyncMock(return_value=mock_agent)
    ws.get_agents_by_session = AsyncMock(
        return_value=agents if agents is not None else [mock_agent]
    )
    return ws


# ---------------------------------------------------------------------------
# Tests: _detect_spawn
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_detect_spawn_new_session_returns_spawn_with_no_parent():
    """First PreToolUse for an unseen session spawns an agent with parent_id=None."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)

    event = _make_event()
    state = engine.get_inference_state()

    # Session must not exist yet.
    assert event.session_id not in state.sessions

    result = await engine._detect_spawn(event, state)

    assert result is not None
    assert result.action == InferenceAction.SPAWN
    assert result.parent_id is None


@pytest.mark.asyncio
async def test_detect_spawn_existing_session_no_active_tools_returns_none():
    """PreToolUse for a known session with no active tools does not spawn."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    state = engine.get_inference_state()

    session_id = str(uuid4())
    state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        active_tools=0,
    )

    event = _make_event(session_id=session_id)
    result = await engine._detect_spawn(event, state)

    assert result is None


@pytest.mark.asyncio
async def test_detect_spawn_concurrent_pre_tool_use_spawns_with_parent():
    """PreToolUse while session has active tools triggers a spawn with parent inference."""
    parent_agent = MagicMock()
    parent_agent.id = "parent-agent-id"
    parent_agent.last_seen = datetime.now(UTC)

    ws = _make_world_state(agents=[parent_agent])
    engine = AgentInferenceEngine(ws)
    state = engine.get_inference_state()

    session_id = str(uuid4())
    state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        active_tools=1,  # simulates an in-flight tool
    )

    event = _make_event(session_id=session_id)
    result = await engine._detect_spawn(event, state)

    assert result is not None
    assert result.action == InferenceAction.SPAWN
    assert result.parent_id == "parent-agent-id"


# ---------------------------------------------------------------------------
# Tests: _get_primary_agent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_primary_agent_returns_most_recent():
    """_get_primary_agent returns the agent with the latest last_seen."""
    old_agent = MagicMock()
    old_agent.id = "old"
    old_agent.last_seen = datetime(2025, 1, 1, tzinfo=UTC)

    new_agent = MagicMock()
    new_agent.id = "new"
    new_agent.last_seen = datetime(2025, 6, 1, tzinfo=UTC)

    ws = _make_world_state(agents=[old_agent, new_agent])
    engine = AgentInferenceEngine(ws)

    primary = await engine._get_primary_agent("any-session")
    assert primary.id == "new"


@pytest.mark.asyncio
async def test_get_primary_agent_no_agents_returns_none():
    """_get_primary_agent returns None when the world state has no agents."""
    ws = _make_world_state(agents=[])
    engine = AgentInferenceEngine(ws)

    primary = await engine._get_primary_agent("any-session")
    assert primary is None


# ---------------------------------------------------------------------------
# Tests: _handle_pre_tool_use (integration-level)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_pre_tool_use_adds_new_session_to_state():
    """Processing a PreToolUse for an unknown session adds it to inference state."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)

    event = _make_event()
    await engine._handle_pre_tool_use(event)

    state = engine.get_inference_state()
    assert event.session_id in state.sessions


@pytest.mark.asyncio
async def test_handle_pre_tool_use_increments_active_tools():
    """Each PreToolUse call increments the session's active_tools counter."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)

    session_id = str(uuid4())
    event1 = _make_event(session_id=session_id, event_id=str(uuid4()))
    event2 = _make_event(session_id=session_id, event_id=str(uuid4()))

    await engine._handle_pre_tool_use(event1)
    await engine._handle_pre_tool_use(event2)

    state = engine.get_inference_state()
    assert state.sessions[session_id].active_tools == 2


@pytest.mark.asyncio
async def test_handle_pre_tool_use_records_pending_tool():
    """PreToolUse records a PendingTool keyed by event id."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)

    event = _make_event()
    await engine._handle_pre_tool_use(event)

    state = engine.get_inference_state()
    assert event.id in state.pending_tools
    pt = state.pending_tools[event.id]
    assert pt.session_id == event.session_id
    assert pt.tool_name == event.tool_name


@pytest.mark.asyncio
async def test_handle_pre_tool_use_calls_world_state_on_spawn():
    """When a spawn is detected, both get_or_create_session and get_or_create_agent are called."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)

    event = _make_event()
    await engine._handle_pre_tool_use(event)

    ws.get_or_create_session.assert_awaited_once_with(event.session_id, event.project_id)
    ws.get_or_create_agent.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_pre_tool_use_new_session_spawns_with_no_parent():
    """First PreToolUse for a new session spawns an agent with parent_id=None."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)

    event = _make_event()
    await engine._handle_pre_tool_use(event)

    # parent_id=None must be passed to get_or_create_agent for the primary agent
    ws.get_or_create_agent.assert_awaited_once_with(event.session_id, None)
