"""Tests for AgentUpdater (work item 083).

Test framework: pytest + pytest-asyncio.
Run with: pytest tests/test_agent_updater.py -v
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from hamlet.simulation.agent_updater import AgentUpdater
from hamlet.simulation.config import SimulationConfig
from hamlet.world_state.types import Agent, AgentState


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def config() -> SimulationConfig:
    """Return a default simulation config."""
    return SimulationConfig()


@pytest.fixture
def updater(config: SimulationConfig) -> AgentUpdater:
    """Return an AgentUpdater with default config."""
    return AgentUpdater(config)


@pytest.fixture
def world_state() -> MagicMock:
    """Return a mock WorldStateManager."""
    ws = MagicMock()
    ws.update_agent = AsyncMock()
    return ws


def _make_agent(
    state: AgentState = AgentState.ACTIVE,
    last_seen: datetime | None = None,
) -> Agent:
    """Create an Agent with given state and last_seen time."""
    return Agent(
        id=str(uuid4()),
        session_id=str(uuid4()),
        project_id=str(uuid4()),
        state=state,
        last_seen=last_seen or datetime.now(UTC),
    )


# -----------------------------------------------------------------------------
# Test Class: TestAgentUpdater
# -----------------------------------------------------------------------------

class TestAgentUpdater:
    """Tests for AgentUpdater state transition logic."""

    @pytest.mark.asyncio
    async def test_active_agent_stays_active(
        self, updater: AgentUpdater, world_state: MagicMock
    ) -> None:
        """test_active_agent_stays_active - Active agent seen recently stays active."""
        agent = _make_agent(
            state=AgentState.ACTIVE,
            last_seen=datetime.now(UTC),  # Just seen
        )

        await updater.update_agents([agent], world_state)

        # Should not call update_agent since state hasn't changed
        world_state.update_agent.assert_not_awaited()
        assert agent.state == AgentState.ACTIVE

    @pytest.mark.asyncio
    async def test_idle_agent_after_60_seconds(
        self, updater: AgentUpdater, world_state: MagicMock
    ) -> None:
        """test_idle_agent_after_60_seconds - Agent becomes IDLE after 60 seconds."""
        agent = _make_agent(
            state=AgentState.ACTIVE,
            last_seen=datetime.now(UTC) - timedelta(seconds=61),  # 61 seconds ago
        )

        await updater.update_agents([agent], world_state)

        world_state.update_agent.assert_awaited_once_with(agent.id, state=AgentState.IDLE)

    @pytest.mark.asyncio
    async def test_active_to_idle_at_exactly_60_seconds(
        self, updater: AgentUpdater, world_state: MagicMock
    ) -> None:
        """Agent becomes IDLE at exactly 60 seconds threshold."""
        agent = _make_agent(
            state=AgentState.ACTIVE,
            last_seen=datetime.now(UTC) - timedelta(seconds=60),
        )

        await updater.update_agents([agent], world_state)

        world_state.update_agent.assert_awaited_once_with(agent.id, state=AgentState.IDLE)

    @pytest.mark.asyncio
    async def test_active_agent_at_59_seconds_stays_active(
        self, updater: AgentUpdater, world_state: MagicMock
    ) -> None:
        """Agent at 59 seconds stays ACTIVE (just under threshold)."""
        agent = _make_agent(
            state=AgentState.ACTIVE,
            last_seen=datetime.now(UTC) - timedelta(seconds=59),
        )

        await updater.update_agents([agent], world_state)

        # Should not transition
        world_state.update_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_multiple_agents_different_states(
        self, updater: AgentUpdater, world_state: MagicMock
    ) -> None:
        """Multiple agents with different states are updated correctly."""
        now = datetime.now(UTC)

        active_agent = _make_agent(
            state=AgentState.ACTIVE,
            last_seen=now,  # Just seen
        )
        idle_agent = _make_agent(
            state=AgentState.ACTIVE,
            last_seen=now - timedelta(seconds=65),  # Should become idle
        )

        await updater.update_agents([active_agent, idle_agent], world_state)

        # Only idle_agent should trigger an update
        assert world_state.update_agent.await_count == 1
        world_state.update_agent.assert_awaited_once_with(idle_agent.id, state=AgentState.IDLE)

    @pytest.mark.asyncio
    async def test_empty_agent_list(self, updater: AgentUpdater, world_state: MagicMock) -> None:
        """Empty agent list does nothing."""
        await updater.update_agents([], world_state)

        world_state.update_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_update_when_state_unchanged(
        self, updater: AgentUpdater, world_state: MagicMock
    ) -> None:
        """No update call when agent is already in the correct state."""
        agent = _make_agent(
            state=AgentState.IDLE,
            last_seen=datetime.now(UTC) - timedelta(seconds=65),
        )

        await updater.update_agents([agent], world_state)

        # Agent should already be IDLE, so no update needed
        world_state.update_agent.assert_not_awaited()

    async def test_zombie_agent_is_skipped(
        self, updater: AgentUpdater, world_state: MagicMock
    ) -> None:
        """ZOMBIE agents are not touched by AgentUpdater; zombie lifecycle belongs to AgentInferenceEngine."""
        agent = _make_agent(
            state=AgentState.ZOMBIE,
            last_seen=datetime.now(UTC) - timedelta(seconds=600),
        )

        await updater.update_agents([agent], world_state)

        world_state.update_agent.assert_not_awaited()
