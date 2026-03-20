"""Animation state machine for agent display in the TUI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from hamlet.inference.types import AgentType, TYPE_COLORS
from hamlet.world_state.types import Agent, AgentState

AGENT_BASE_COLORS = TYPE_COLORS

SPIN_SYMBOLS = ["-", "\\", "|", "/"]
SPIN_FRAME_RATE = 4  # Hz — spin cycles per second
PULSE_RATE = 1  # Hz — zombie color changes per second (0.5Hz cycle = 2 changes/sec)
# Assumes 30fps tick rate. Each spin frame lasts ~8 ticks; each pulse frame lasts 30 ticks.
TICKS_PER_SPIN_FRAME = max(1, round(30 / SPIN_FRAME_RATE))   # = 8
TICKS_PER_PULSE_FRAME = max(1, round(30 / (PULSE_RATE * 2)))  # = 15 (0.5Hz cycle)

ZOMBIE_PULSE_COLOR = "bright_green"  # Distinct from base "dark_green" (used by PLANNER)


@dataclass
class AnimationState:
    """Current animation state for an agent."""
    animation_type: Literal["idle", "spin", "pulse"]
    current_frame: int
    frame_count: int


class AnimationManager:
    """Manages per-agent animation frames."""

    def __init__(self) -> None:
        self._frames: dict[str, int] = {}  # agent_id -> current frame

    def get_animation_state(self, agent: Agent) -> AnimationState:
        """Return current animation state for an agent."""
        if agent.state == AgentState.ACTIVE:
            raw = self._frames.get(agent.id, 0)
            frame = (raw // TICKS_PER_SPIN_FRAME) % 4
            return AnimationState(animation_type="spin", current_frame=frame, frame_count=4)
        elif agent.state == AgentState.ZOMBIE:
            raw = self._frames.get(agent.id, 0)
            frame = (raw // TICKS_PER_PULSE_FRAME) % 2
            return AnimationState(animation_type="pulse", current_frame=frame, frame_count=2)
        else:  # IDLE
            return AnimationState(animation_type="idle", current_frame=0, frame_count=1)

    def get_animation_symbol(self, state: AnimationState) -> str:
        """Return the display symbol for the given animation state."""
        if state.animation_type == "spin":
            return SPIN_SYMBOLS[state.current_frame % 4]
        return "@"  # idle and pulse both show @

    def get_animation_color(self, agent: Agent, state: AnimationState, current_time: float) -> str:
        """Return the display color for an agent at the given time."""
        base_color = AGENT_BASE_COLORS.get(agent.inferred_type, "white")
        if state.animation_type == "pulse":
            # Pulse at 0.5Hz — alternate between base color and bright_green.
            # bright_green is used (not plain green) so PLANNER zombies (base=green)
            # remain visually distinct between the two pulse phases.
            if state.current_frame == 0:
                return ZOMBIE_PULSE_COLOR
            return base_color
        return base_color

    def get_frames(self, zombie_ids: set[str] | None = None) -> dict[str, int]:
        """Return per-agent display frame indices.

        Args:
            zombie_ids: Set of agent IDs that are in the ZOMBIE state. These
                agents use the pulse formula ((ticks // TICKS_PER_PULSE_FRAME) % 2).
                All other agents use the spin formula ((ticks // TICKS_PER_SPIN_FRAME) % 4).
        """
        if zombie_ids is None:
            zombie_ids = set()
        result = {}
        for agent_id, ticks in self._frames.items():
            if agent_id in zombie_ids:
                result[agent_id] = (ticks // TICKS_PER_PULSE_FRAME) % 2
            else:
                result[agent_id] = (ticks // TICKS_PER_SPIN_FRAME) % 4
        return result

    def advance_frames(self, agents: list[Agent], delta_ticks: int) -> None:
        """Advance raw tick counters for all agents.

        Raw tick counts are stored in `_frames` and converted to display frames
        in `get_animation_state` using TICKS_PER_SPIN_FRAME / TICKS_PER_PULSE_FRAME.
        This gives correct 4Hz spin and 0.5Hz zombie pulse at 30fps tick rate.
        """
        for agent in agents:
            if agent.state in (AgentState.ACTIVE, AgentState.ZOMBIE):
                self._frames[agent.id] = self._frames.get(agent.id, 0) + delta_ticks
            # Clean up idle agents from dict
            elif agent.id in self._frames:
                del self._frames[agent.id]


__all__ = ["AnimationState", "AnimationManager", "AGENT_BASE_COLORS", "SPIN_SYMBOLS", "ZOMBIE_PULSE_COLOR"]
