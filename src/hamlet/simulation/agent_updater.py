from __future__ import annotations

"""Agent state management for the Hamlet simulation.

This module provides :class:`AgentUpdater`, which computes the appropriate
:class:`~hamlet.world_state.types.AgentState` for each agent based on how
recently it was seen and applies any state transitions via the world state.
"""

__all__ = ["AgentUpdater"]

from datetime import UTC, datetime
from typing import Any

from hamlet.simulation.config import SimulationConfig
from hamlet.world_state.types import Agent, AgentState

_IDLE_THRESHOLD: float = 60.0  # seconds — fixed, not configurable


class AgentUpdater:
    """Updates agent states based on last-seen time."""

    def __init__(self, config: SimulationConfig) -> None:
        self._config = config

    async def update_agents(self, agents: list[Agent], world_state: Any) -> None:
        """Compute and apply state transitions for all agents.

        Args:
            agents: Current list of agents to evaluate.
            world_state: World state object; must expose
                ``async update_agent(agent_id, patch)`` method.
        """
        now = datetime.now(UTC)

        for agent in agents:
            time_since_seen = (now - agent.last_seen).total_seconds()

            if time_since_seen > self._config.zombie_threshold:
                new_state = AgentState.ZOMBIE
            elif time_since_seen > _IDLE_THRESHOLD:
                new_state = AgentState.IDLE
            else:
                new_state = AgentState.ACTIVE

            if agent.state != new_state:
                await world_state.update_agent(agent.id, state=new_state)
