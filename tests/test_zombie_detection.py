"""Tests for zombie detection in AgentInferenceEngine (work item 025).

Test framework: pytest + pytest-asyncio (see pyproject.toml dev dependencies).
Run with: pytest tests/test_zombie_detection.py -v
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from hamlet.inference.engine import AgentInferenceEngine
from hamlet.inference.types import SessionState
from hamlet.world_state.types import AgentState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_world_state() -> MagicMock:
    """Return a mock WorldStateManager with sensible defaults."""
    ws = MagicMock()
    mock_session = MagicMock()
    mock_session.id = str(uuid4())

    mock_agent = MagicMock()
    mock_agent.id = str(uuid4())
    mock_agent.last_seen = datetime.now(UTC)

    ws.get_or_create_session = AsyncMock(return_value=mock_session)
    ws.get_or_create_agent = AsyncMock(return_value=mock_agent)
    ws.get_agents_by_session = AsyncMock(return_value=[mock_agent])
    ws.update_agent = AsyncMock()
    return ws


def _make_agent(state: AgentState = AgentState.ACTIVE, color: str = "white") -> MagicMock:
    """Return a mock Agent with given state and color."""
    agent = MagicMock()
    agent.state = state
    agent.color = color
    return agent


# ---------------------------------------------------------------------------
# Tests: _check_zombie
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_zombie_returns_false_when_agent_not_in_last_seen():
    """_check_zombie returns False when the agent_id is not in last_seen."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)

    result = engine._check_zombie("unknown-agent-id")

    assert result is False


@pytest.mark.asyncio
async def test_check_zombie_returns_false_when_seen_within_threshold():
    """_check_zombie returns False when last_seen is within ZOMBIE_THRESHOLD_SECONDS."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    agent_id = str(uuid4())

    # Seen just 10 seconds ago — well within the 300-second threshold.
    engine._state.last_seen[agent_id] = datetime.now(UTC) - timedelta(seconds=10)

    result = engine._check_zombie(agent_id)

    assert result is False


@pytest.mark.asyncio
async def test_check_zombie_returns_true_when_elapsed_meets_threshold():
    """_check_zombie returns True when elapsed time >= ZOMBIE_THRESHOLD_SECONDS."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    agent_id = str(uuid4())

    # Seen exactly at the threshold boundary (300 seconds ago).
    engine._state.last_seen[agent_id] = datetime.now(UTC) - timedelta(
        seconds=engine._zombie_threshold_seconds
    )

    result = engine._check_zombie(agent_id)

    assert result is True


@pytest.mark.asyncio
async def test_check_zombie_returns_true_when_elapsed_exceeds_threshold():
    """_check_zombie returns True when elapsed time is well beyond the threshold."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    agent_id = str(uuid4())

    # Seen 10 minutes ago — clearly zombie.
    engine._state.last_seen[agent_id] = datetime.now(UTC) - timedelta(minutes=10)

    result = engine._check_zombie(agent_id)

    assert result is True


# ---------------------------------------------------------------------------
# Tests: _update_zombie_states
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_zombie_states_calls_update_agent_for_stale_agents():
    """_update_zombie_states calls update_agent with state=ZOMBIE for stale agents."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    agent_id = str(uuid4())

    # Mark the agent as seen 10 minutes ago — definitely stale.
    engine._state.last_seen[agent_id] = datetime.now(UTC) - timedelta(minutes=10)

    await engine._update_zombie_states()

    ws.update_agent.assert_awaited_once_with(agent_id, state=AgentState.ZOMBIE)


@pytest.mark.asyncio
async def test_update_zombie_states_does_not_call_update_agent_for_fresh_agents():
    """_update_zombie_states does not call update_agent for recently seen agents."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    agent_id = str(uuid4())

    # Seen 30 seconds ago — fresh.
    engine._state.last_seen[agent_id] = datetime.now(UTC) - timedelta(seconds=30)

    await engine._update_zombie_states()

    ws.update_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_zombie_states_handles_mixed_agents():
    """_update_zombie_states marks only stale agents as zombie, leaving fresh ones alone."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)

    stale_id = str(uuid4())
    fresh_id = str(uuid4())

    engine._state.last_seen[stale_id] = datetime.now(UTC) - timedelta(minutes=10)
    engine._state.last_seen[fresh_id] = datetime.now(UTC) - timedelta(seconds=30)

    await engine._update_zombie_states()

    ws.update_agent.assert_awaited_once_with(stale_id, state=AgentState.ZOMBIE)


@pytest.mark.asyncio
async def test_update_zombie_states_continues_on_world_state_error():
    """_update_zombie_states logs and continues when update_agent raises an exception."""
    ws = _make_world_state()
    ws.update_agent = AsyncMock(side_effect=RuntimeError("DB failure"))
    engine = AgentInferenceEngine(ws)

    stale_id = str(uuid4())
    engine._state.last_seen[stale_id] = datetime.now(UTC) - timedelta(minutes=10)

    # Should not raise even when update_agent fails.
    await engine._update_zombie_states()

