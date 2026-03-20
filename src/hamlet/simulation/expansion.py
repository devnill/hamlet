"""Village expansion and road building for the Hamlet simulation."""
from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

from hamlet.simulation.config import SimulationConfig
from hamlet.world_state.types import Position, StructureType

if TYPE_CHECKING:
    from hamlet.world_state.types import Agent, Village

logger = logging.getLogger(__name__)


class ExpansionManager:
    """Manages village expansion site selection and road construction."""

    def __init__(self, config: SimulationConfig) -> None:
        self._config = config

    def check_village_expansion(
        self,
        village: Village,
        agents: list[Agent],
        all_villages: list[Village],
    ) -> Position | None:
        """Return an expansion site Position if expansion is warranted, else None.

        Expansion is triggered when the number of agents meets or exceeds
        expansion_threshold. Sites are searched at 20–50 cells from the
        village center, stepping every 5 cells and every 15 degrees of arc.
        """
        if len(agents) < self._config.expansion_threshold:
            return None

        for distance in range(20, 51, 5):
            for angle_deg in range(0, 360, 15):
                angle_rad = math.radians(angle_deg)
                candidate = Position(
                    int(village.center.x + distance * math.cos(angle_rad)),
                    int(village.center.y + distance * math.sin(angle_rad)),
                )
                if self._is_clear_site(candidate, all_villages, min_distance=15):
                    return candidate

        return None

    def _is_clear_site(
        self,
        position: Position,
        all_villages: list[Village],
        min_distance: int = 15,
    ) -> bool:
        """Return True if *position* is at least *min_distance* from every village center."""
        for village in all_villages:
            dist = (
                (village.center.x - position.x) ** 2
                + (village.center.y - position.y) ** 2
            ) ** 0.5
            if dist < min_distance:
                return False
        return True

    async def process_expansion(self, world_state: Any) -> None:
        """Process expansion for all villages in world_state once per tick."""
        all_villages = await world_state.get_all_villages()
        all_agents_list = await world_state.get_all_agents()
        all_agents = {a.id: a for a in all_agents_list}
        for village in all_villages:
            try:
                village_agents = [
                    all_agents[aid]
                    for aid in village.agent_ids
                    if aid in all_agents
                ]
                site = self.check_village_expansion(village, village_agents, all_villages)
                if site is not None:
                    await self.create_road_between(
                        world_state, village.id, village.center, site
                    )
            except Exception:
                logger.exception(
                    "Error in expansion check for village %s — skipping", village.id
                )

    async def create_road_between(
        self,
        world_state: object,
        village_id: str,
        start: Position,
        end: Position,
    ) -> None:
        """Create stone road structures along a straight line from *start* to *end*.

        Uses Bresenham's line algorithm. Road segments are created with
        stage=3 and material="stone". If *world_state* does not expose a
        ``create_structure`` method the operation is silently skipped.
        """
        if not hasattr(world_state, "create_structure"):
            return

        for x, y in self._bresenham(start.x, start.y, end.x, end.y):
            position = Position(x, y)
            await world_state.create_structure(
                village_id,
                StructureType.ROAD,
                position,
            )

    @staticmethod
    def _bresenham(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
        """Return all integer grid points on the line from (x0, y0) to (x1, y1)."""
        points: list[tuple[int, int]] = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            points.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        return points


__all__ = ["ExpansionManager"]
