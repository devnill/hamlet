"""Simulation engine — runs the game tick loop."""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .config import SimulationConfig
from .state import SimulationState

if TYPE_CHECKING:
    from hamlet.protocols import InferenceEngineProtocol, WorldStateProtocol

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Core simulation engine that drives the game tick loop.

    Runs as a background asyncio task. Each tick updates agent states,
    structure progression, animations, and village expansion.
    """

    def __init__(
        self,
        world_state: "WorldStateProtocol",
        config: SimulationConfig | None = None,
        agent_updater: Any = None,
        structure_updater: Any = None,
        expansion_manager: Any = None,
        animation_manager: Any = None,
        agent_inference: "InferenceEngineProtocol | None" = None,
    ) -> None:
        # world_state: WorldStateManager (defined in world_state module, imported at runtime)
        self._world_state = world_state
        self._config = config or SimulationConfig()
        self._state = SimulationState()
        self._task: asyncio.Task | None = None
        self._agent_updater = agent_updater
        self._structure_updater = structure_updater
        self._expansion_manager = expansion_manager
        self._animation_manager = animation_manager
        self._agent_inference = agent_inference

    async def start(self) -> None:
        """Start the simulation tick loop as a background task."""
        if self._task is not None and not self._task.done():
            return
        self._state.running = True
        self._task = asyncio.create_task(self._tick_loop())
        logger.info("SimulationEngine started at %.1f ticks/s", self._config.tick_rate)

    async def stop(self) -> None:
        """Stop the simulation tick loop and await cleanup."""
        self._state.running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("SimulationEngine stopped after %d ticks", self._state.tick_count)

    def set_tick_rate(self, rate: float) -> None:
        """Update the tick rate (ticks per second). Must be positive."""
        if rate <= 0:
            raise ValueError(f"tick_rate must be positive, got {rate}")
        self._config.tick_rate = rate

    async def _tick_loop(self) -> None:
        """Background tick loop. Runs while running flag is set."""
        while self._state.running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error in simulation tick — continuing")
            if self._state.running:
                await asyncio.sleep(max(1.0 / self._config.tick_rate, 0.001))

    async def _tick(self) -> None:
        """Execute one simulation tick."""
        self._state.tick_count += 1
        self._state.last_tick_at = datetime.now(UTC)

        # Collect world state data for this tick via public accessors
        all_agents = await self._world_state.get_all_agents()
        all_structures = await self._world_state.get_all_structures()

        # 1. Agent updates
        if self._agent_updater is not None:
            try:
                await self._agent_updater.update_agents(all_agents, self._world_state)
            except Exception:
                logger.exception("Error in agent update — continuing")

        # 2. Structure updates
        if self._structure_updater is not None:
            try:
                await self._structure_updater.update_structures(all_structures, self._world_state)
            except Exception:
                logger.exception("Error in structure update — continuing")

        # 3. Expansion check (once per tick)
        if self._expansion_manager is not None:
            try:
                await self._expansion_manager.process_expansion(self._world_state)
            except Exception:
                logger.exception("Error in expansion check — continuing")

        # 4. Animation advance
        if self._animation_manager is not None:
            try:
                self._animation_manager.advance_frames(all_agents, delta_ticks=1)
            except Exception:
                logger.exception("Error in animation advance — continuing")

        # 5. Zombie detection
        if self._agent_inference is not None:
            try:
                await self._agent_inference.tick()
            except Exception:
                logger.exception("Error in zombie detection — continuing")

    def get_state(self) -> SimulationState:
        """Return a snapshot of the current simulation state."""
        return self._state
