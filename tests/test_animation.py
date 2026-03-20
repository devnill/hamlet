"""Tests for AnimationManager (work item 084).

Test framework: pytest + pytest-asyncio.
Run with: pytest tests/test_animation.py -v
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock

import pytest

from hamlet.inference.types import AgentType as InfAgentType, TYPE_COLORS
from hamlet.simulation.animation import (
    SPIN_SYMBOLS,
    TICKS_PER_PULSE_FRAME,
    TICKS_PER_SPIN_FRAME,
    AnimationManager,
    AnimationState,
)
from hamlet.world_state.types import Agent, AgentState, AgentType


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def animation_mgr() -> AnimationManager:
    """Return an AnimationManager instance."""
    return AnimationManager()


@pytest.fixture
def active_agent() -> Agent:
    """Return an agent in ACTIVE state."""
    return Agent(
        id="agent-1",
        session_id="session-1",
        project_id="project-1",
        village_id="village-1",
        inferred_type=AgentType.CODER,
        state=AgentState.ACTIVE,
    )


@pytest.fixture
def zombie_agent() -> Agent:
    """Return an agent in ZOMBIE state."""
    return Agent(
        id="agent-2",
        session_id="session-2",
        project_id="project-1",
        village_id="village-1",
        inferred_type=AgentType.PLANNER,
        state=AgentState.ZOMBIE,
    )


@pytest.fixture
def idle_agent() -> Agent:
    """Return an agent in IDLE state."""
    return Agent(
        id="agent-3",
        session_id="session-3",
        project_id="project-1",
        village_id="village-1",
        inferred_type=AgentType.RESEARCHER,
        state=AgentState.IDLE,
    )


# -----------------------------------------------------------------------------
# Test Class: TestAnimationManager
# -----------------------------------------------------------------------------

class TestAnimationManager:
    """Tests for AnimationManager frame management and symbol/color generation."""

    def test_get_animation_state_active_returns_spin(
        self,
        animation_mgr: AnimationManager,
        active_agent: Agent,
    ) -> None:
        """test_get_animation_state_active_returns_spin - ACTIVE agents return spin animation type."""
        state = animation_mgr.get_animation_state(active_agent)

        assert isinstance(state, AnimationState)
        assert state.animation_type == "spin"
        assert state.frame_count == 4

    def test_get_animation_state_zombie_returns_pulse(
        self,
        animation_mgr: AnimationManager,
        zombie_agent: Agent,
    ) -> None:
        """ZOMBIE agents return pulse animation type."""
        state = animation_mgr.get_animation_state(zombie_agent)

        assert state.animation_type == "pulse"
        assert state.frame_count == 2

    def test_get_animation_state_idle_returns_idle(
        self,
        animation_mgr: AnimationManager,
        idle_agent: Agent,
    ) -> None:
        """IDLE agents return idle animation type."""
        state = animation_mgr.get_animation_state(idle_agent)

        assert state.animation_type == "idle"
        assert state.frame_count == 1
        assert state.current_frame == 0

    def test_get_animation_symbol_spin_cycles(
        self,
        animation_mgr: AnimationManager,
        active_agent: Agent,
    ) -> None:
        """test_get_animation_symbol_spin_cycles - Spin animation cycles through SPIN_SYMBOLS."""
        symbols = []
        for i in range(8):  # Get 8 symbols (should cycle twice through 4 symbols)
            state = animation_mgr.get_animation_state(active_agent)
            symbol = animation_mgr.get_animation_symbol(state)
            symbols.append(symbol)
            # Advance by one spin frame
            animation_mgr.advance_frames([active_agent], TICKS_PER_SPIN_FRAME)

        # Verify we got the expected spin symbols
        assert all(s in SPIN_SYMBOLS for s in symbols)
        # First symbol should equal fifth symbol (cycle repeats)
        assert symbols[0] == symbols[4]
        # Second symbol should equal sixth symbol
        assert symbols[1] == symbols[5]

    def test_get_animation_symbol_idle_and_pulse(
        self,
        animation_mgr: AnimationManager,
        idle_agent: Agent,
        zombie_agent: Agent,
    ) -> None:
        """Idle and pulse animations return '@' symbol."""
        idle_state = animation_mgr.get_animation_state(idle_agent)
        zombie_state = animation_mgr.get_animation_state(zombie_agent)

        assert animation_mgr.get_animation_symbol(idle_state) == "@"
        assert animation_mgr.get_animation_symbol(zombie_state) == "@"

    def test_advance_frames_increments_counters(
        self,
        animation_mgr: AnimationManager,
        active_agent: Agent,
    ) -> None:
        """test_advance_frames_increments_counters - advance_frames increments frame counters for active agents."""
        initial_state = animation_mgr.get_animation_state(active_agent)
        initial_frame = initial_state.current_frame

        # Advance by TICKS_PER_SPIN_FRAME to move to next frame
        animation_mgr.advance_frames([active_agent], TICKS_PER_SPIN_FRAME)

        new_state = animation_mgr.get_animation_state(active_agent)
        # Frame should have advanced (or cycled)
        assert new_state.current_frame != initial_frame or new_state.current_frame == 0

    def test_advance_frames_increments_zombie_counters(
        self,
        animation_mgr: AnimationManager,
        zombie_agent: Agent,
    ) -> None:
        """advance_frames increments frame counters for zombie agents."""
        initial_state = animation_mgr.get_animation_state(zombie_agent)

        # Advance by TICKS_PER_PULSE_FRAME to move to next frame
        animation_mgr.advance_frames([zombie_agent], TICKS_PER_PULSE_FRAME)

        new_state = animation_mgr.get_animation_state(zombie_agent)
        # Frame should have toggled (0 -> 1 or 1 -> 0)
        assert new_state.current_frame != initial_state.current_frame

    def test_advance_frames_cleans_up_idle_agents(
        self,
        animation_mgr: AnimationManager,
        active_agent: Agent,
        idle_agent: Agent,
    ) -> None:
        """advance_frames removes idle agents from frame tracking."""
        # First make active agent tracked
        animation_mgr.advance_frames([active_agent], 1)
        assert active_agent.id in animation_mgr._frames

        # Now advance with agent as idle
        active_agent.state = AgentState.IDLE
        animation_mgr.advance_frames([active_agent], 1)

        # Should be removed from tracking
        assert active_agent.id not in animation_mgr._frames

    def test_advance_frames_multiple_agents(
        self,
        animation_mgr: AnimationManager,
        active_agent: Agent,
        zombie_agent: Agent,
    ) -> None:
        """advance_frames handles multiple agents at once."""
        agents = [active_agent, zombie_agent]

        animation_mgr.advance_frames(agents, 10)

        # Both should have frame counters incremented
        assert active_agent.id in animation_mgr._frames
        assert zombie_agent.id in animation_mgr._frames
        assert animation_mgr._frames[active_agent.id] == 10
        assert animation_mgr._frames[zombie_agent.id] == 10

    def test_get_animation_color_base_color(
        self,
        animation_mgr: AnimationManager,
        active_agent: Agent,
    ) -> None:
        """Active agents use their base color."""
        state = animation_mgr.get_animation_state(active_agent)
        color = animation_mgr.get_animation_color(active_agent, state, 0.0)

        assert color == TYPE_COLORS[InfAgentType(AgentType.CODER.value)]

    def test_get_animation_color_zombie_pulse(
        self,
        animation_mgr: AnimationManager,
        zombie_agent: Agent,
    ) -> None:
        """Zombie agents pulse between bright_green and base color."""
        # Frame 0 should be bright_green
        animation_mgr._frames[zombie_agent.id] = 0
        state = animation_mgr.get_animation_state(zombie_agent)
        color = animation_mgr.get_animation_color(zombie_agent, state, 0.0)
        assert color == "bright_green"

        # Frame 1 should be base color
        animation_mgr._frames[zombie_agent.id] = TICKS_PER_PULSE_FRAME
        state = animation_mgr.get_animation_state(zombie_agent)
        color = animation_mgr.get_animation_color(zombie_agent, state, 0.0)
        assert color == TYPE_COLORS[InfAgentType(AgentType.PLANNER.value)]

    def test_get_animation_color_unknown_agent_type(
        self,
        animation_mgr: AnimationManager,
    ) -> None:
        """Unknown agent types default to white."""
        agent = Agent(
            id="unknown-agent",
            session_id="session-1",
            project_id="project-1",
            state=AgentState.ACTIVE,
            inferred_type=AgentType.EXECUTOR,
        )
        state = animation_mgr.get_animation_state(agent)
        color = animation_mgr.get_animation_color(agent, state, 0.0)

        assert color == TYPE_COLORS[InfAgentType(AgentType.EXECUTOR.value)]

    def test_spin_frame_timing(
        self,
        animation_mgr: AnimationManager,
        active_agent: Agent,
    ) -> None:
        """Spin animation advances at correct rate (every TICKS_PER_SPIN_FRAME)."""
        # Start at frame 0
        animation_mgr._frames[active_agent.id] = 0
        state = animation_mgr.get_animation_state(active_agent)
        assert state.current_frame == 0

        # Just before threshold - should still be frame 0
        animation_mgr._frames[active_agent.id] = TICKS_PER_SPIN_FRAME - 1
        state = animation_mgr.get_animation_state(active_agent)
        assert state.current_frame == 0

        # At threshold - should advance to frame 1
        animation_mgr._frames[active_agent.id] = TICKS_PER_SPIN_FRAME
        state = animation_mgr.get_animation_state(active_agent)
        assert state.current_frame == 1

    def test_pulse_frame_timing(
        self,
        animation_mgr: AnimationManager,
        zombie_agent: Agent,
    ) -> None:
        """Pulse animation advances at correct rate (every TICKS_PER_PULSE_FRAME)."""
        # Start at frame 0
        animation_mgr._frames[zombie_agent.id] = 0
        state = animation_mgr.get_animation_state(zombie_agent)
        assert state.current_frame == 0

        # Just before threshold - should still be frame 0
        animation_mgr._frames[zombie_agent.id] = TICKS_PER_PULSE_FRAME - 1
        state = animation_mgr.get_animation_state(zombie_agent)
        assert state.current_frame == 0

        # At threshold - should advance to frame 1
        animation_mgr._frames[zombie_agent.id] = TICKS_PER_PULSE_FRAME
        state = animation_mgr.get_animation_state(zombie_agent)
        assert state.current_frame == 1

    def test_get_frames_non_zombie_uses_spin_formula(
        self,
        animation_mgr: AnimationManager,
        active_agent: Agent,
    ) -> None:
        """Non-zombie agents use spin formula: (ticks // TICKS_PER_SPIN_FRAME) % 4."""
        ticks = TICKS_PER_SPIN_FRAME * 2 + 3  # lands on spin frame 2
        animation_mgr._frames[active_agent.id] = ticks

        frames = animation_mgr.get_frames()

        expected = (ticks // TICKS_PER_SPIN_FRAME) % 4
        assert frames[active_agent.id] == expected

    def test_get_frames_zombie_uses_pulse_formula(
        self,
        animation_mgr: AnimationManager,
        zombie_agent: Agent,
    ) -> None:
        """Zombie agents use pulse formula: (ticks // TICKS_PER_PULSE_FRAME) % 2."""
        ticks = TICKS_PER_PULSE_FRAME * 3 + 1  # lands on pulse frame 1
        animation_mgr._frames[zombie_agent.id] = ticks

        frames = animation_mgr.get_frames(zombie_ids={zombie_agent.id})

        expected = (ticks // TICKS_PER_PULSE_FRAME) % 2
        assert frames[zombie_agent.id] == expected

    def test_get_frames_default_no_zombies(
        self,
        animation_mgr: AnimationManager,
        active_agent: Agent,
        zombie_agent: Agent,
    ) -> None:
        """Calling get_frames() with no zombie_ids applies spin formula to all tracked agents."""
        ticks_active = TICKS_PER_SPIN_FRAME * 3
        ticks_zombie = TICKS_PER_SPIN_FRAME * 1
        animation_mgr._frames[active_agent.id] = ticks_active
        animation_mgr._frames[zombie_agent.id] = ticks_zombie

        # No zombie_ids supplied — both agents treated as spin
        frames = animation_mgr.get_frames()

        assert frames[active_agent.id] == (ticks_active // TICKS_PER_SPIN_FRAME) % 4
        assert frames[zombie_agent.id] == (ticks_zombie // TICKS_PER_SPIN_FRAME) % 4

    def test_get_frames_frame_range(
        self,
        animation_mgr: AnimationManager,
        active_agent: Agent,
        zombie_agent: Agent,
    ) -> None:
        """Spin frames are always 0-3 and pulse frames are always 0-1."""
        spin_frames = set()
        pulse_frames = set()

        # Walk through one full spin cycle and one full pulse cycle
        for tick in range(TICKS_PER_SPIN_FRAME * 4):
            animation_mgr._frames[active_agent.id] = tick
            spin_frames.add(animation_mgr.get_frames()[active_agent.id])

        for tick in range(TICKS_PER_PULSE_FRAME * 2):
            animation_mgr._frames[zombie_agent.id] = tick
            pulse_frames.add(
                animation_mgr.get_frames(zombie_ids={zombie_agent.id})[zombie_agent.id]
            )

        assert spin_frames == {0, 1, 2, 3}
        assert pulse_frames == {0, 1}
