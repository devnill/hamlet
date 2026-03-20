"""Tests for MCP server serializers (serialize_state, serialize_events)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from hamlet.mcp_server.serializers import serialize_state
from hamlet.simulation.animation import AnimationManager, TICKS_PER_PULSE_FRAME, TICKS_PER_SPIN_FRAME
from hamlet.world_state.types import Agent, AgentState, AgentType


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _make_world_state(agents: list, structures: list | None = None,
                       villages: list | None = None, projects: list | None = None) -> MagicMock:
    """Return a minimal async world_state mock."""
    ws = MagicMock()
    ws.get_all_agents = AsyncMock(return_value=agents)
    ws.get_all_structures = AsyncMock(return_value=structures or [])
    ws.get_all_villages = AsyncMock(return_value=villages or [])
    ws.get_projects = AsyncMock(return_value=projects or [])
    return ws


def _make_agent(agent_id: str, state: AgentState) -> MagicMock:
    """Return a lightweight agent mock with the required fields."""
    agent = MagicMock()
    agent.id = agent_id
    agent.session_id = "session-1"
    agent.project_id = "project-1"
    agent.village_id = "village-1"
    agent.inferred_type = MagicMock()
    agent.inferred_type.value = AgentType.CODER.value
    agent.color = "white"
    agent.position = MagicMock()
    agent.position.x = 0
    agent.position.y = 0
    agent.last_seen = MagicMock()
    agent.last_seen.isoformat = MagicMock(return_value="2026-01-01T00:00:00")
    agent.state = state
    agent.parent_id = None
    agent.current_activity = None
    agent.total_work_units = 0
    agent.created_at = MagicMock()
    agent.created_at.isoformat = MagicMock(return_value="2026-01-01T00:00:00")
    agent.updated_at = MagicMock()
    agent.updated_at.isoformat = MagicMock(return_value="2026-01-01T00:00:00")
    return agent


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

class TestSerializeState:
    """Tests for serialize_state()."""

    @pytest.mark.asyncio
    async def test_serialize_state_without_animation_manager(self) -> None:
        """serialize_state returns empty animation_frames when no animation_manager supplied."""
        ws = _make_world_state(agents=[])

        result = await serialize_state(ws)

        assert result["animation_frames"] == {}

    @pytest.mark.asyncio
    async def test_serialize_state_zombie_ids_passed_to_get_frames(self) -> None:
        """serialize_state identifies zombie agents and passes their IDs to get_frames()."""
        spin_agent = _make_agent("spin-1", AgentState.ACTIVE)
        zombie_agent = _make_agent("zombie-1", AgentState.ZOMBIE)

        animation_mgr = AnimationManager()
        # Set raw tick counts so we can predict the computed frame values.
        animation_mgr._frames["spin-1"] = TICKS_PER_SPIN_FRAME * 2   # spin frame 2
        animation_mgr._frames["zombie-1"] = TICKS_PER_PULSE_FRAME * 1  # pulse frame 1

        ws = _make_world_state(agents=[spin_agent, zombie_agent])

        result = await serialize_state(ws, animation_manager=animation_mgr)

        animation_frames = result["animation_frames"]

        # Non-zombie agent should use spin formula
        expected_spin = (TICKS_PER_SPIN_FRAME * 2 // TICKS_PER_SPIN_FRAME) % 4
        assert animation_frames["spin-1"] == expected_spin

        # Zombie agent should use pulse formula (0-1 range)
        expected_pulse = (TICKS_PER_PULSE_FRAME * 1 // TICKS_PER_PULSE_FRAME) % 2
        assert animation_frames["zombie-1"] == expected_pulse
        assert animation_frames["zombie-1"] in (0, 1)

    @pytest.mark.asyncio
    async def test_serialize_state_zombie_gets_pulse_range_frames(self) -> None:
        """Zombie agents in serialized output always produce frames in 0-1 range."""
        zombie_agent = _make_agent("zombie-2", AgentState.ZOMBIE)

        animation_mgr = AnimationManager()
        ws = _make_world_state(agents=[zombie_agent])

        observed_frames = set()
        for tick in range(TICKS_PER_PULSE_FRAME * 4):
            animation_mgr._frames["zombie-2"] = tick
            result = await serialize_state(ws, animation_manager=animation_mgr)
            observed_frames.add(result["animation_frames"]["zombie-2"])

        # Pulse frames must stay within [0, 1]
        assert observed_frames.issubset({0, 1})
        # Both pulse phases must appear across a full cycle
        assert observed_frames == {0, 1}

    @pytest.mark.asyncio
    async def test_serialize_state_no_zombies_uses_spin_only(self) -> None:
        """When there are no zombie agents, all animation frames use the spin formula."""
        active_agent = _make_agent("active-1", AgentState.ACTIVE)

        animation_mgr = AnimationManager()
        animation_mgr._frames["active-1"] = TICKS_PER_SPIN_FRAME * 3

        ws = _make_world_state(agents=[active_agent])

        result = await serialize_state(ws, animation_manager=animation_mgr)

        expected = (TICKS_PER_SPIN_FRAME * 3 // TICKS_PER_SPIN_FRAME) % 4
        assert result["animation_frames"]["active-1"] == expected
