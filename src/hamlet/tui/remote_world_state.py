"""RemoteWorldState — read-only world state backed by HTTP-polled daemon data."""
from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

from hamlet.world_state.parsers import (
    parse_agent,
    parse_event_log_entry,
    parse_structure,
    parse_village,
    parse_project,
    try_parse,
)
from hamlet.world_state.state import EventLogEntry
from hamlet.world_state.terrain import TerrainType
from hamlet.world_state.types import (
    Agent,
    Position,
    Project,
    Session,
    Structure,
    StructureType,
    Village,
)

if TYPE_CHECKING:
    from hamlet.event_processing.internal_event import InternalEvent
    from hamlet.tui.remote_state import RemoteStateProvider, RemoteTerrainGrid

logger = logging.getLogger(__name__)

__all__ = ["RemoteWorldState"]


# ---------------------------------------------------------------------------
# RemoteWorldState
# ---------------------------------------------------------------------------

class RemoteWorldState:
    """Read-only world state populated by polling a remote Hamlet daemon.

    Implements the same async read interface as WorldStateManager so that
    HamletApp and its widgets can use either interchangeably.
    """

    def __init__(self, provider: "RemoteStateProvider") -> None:
        self._provider = provider

        # Cached state (updated by refresh())
        self._cached_state: dict = {}
        self._agents: list[Agent] = []
        self._structures: list[Structure] = []
        self._villages: list[Village] = []
        self._projects: list[Project] = []
        self._event_log: list[EventLogEntry] = []

        # Lazy-initialized terrain grid for remote queries
        self._terrain_grid: "RemoteTerrainGrid | None" = None

    @property
    def terrain_grid(self) -> "RemoteTerrainGrid":
        """Return the terrain grid for remote queries."""
        from hamlet.tui.remote_state import RemoteTerrainGrid

        if self._terrain_grid is None:
            self._terrain_grid = RemoteTerrainGrid(self._provider)
        return self._terrain_grid

    async def refresh(self) -> None:
        """Fetch fresh state from the daemon and update local caches."""
        try:
            state = await self._provider.fetch_state()
            self._cached_state = state

            self._agents = [
                a for d in state.get("agents", [])
                if (a := try_parse(parse_agent, d)) is not None
            ]
            self._structures = [
                s for d in state.get("structures", [])
                if (s := try_parse(parse_structure, d)) is not None
            ]
            self._villages = [
                v for d in state.get("villages", [])
                if (v := try_parse(parse_village, d)) is not None
            ]
            self._projects = [
                p for d in state.get("projects", [])
                if (p := try_parse(parse_project, d)) is not None
            ]
        except Exception as exc:
            logger.debug("RemoteWorldState.refresh: state fetch failed: %s", exc)

        try:
            events_raw = await self._provider.fetch_events()
            self._event_log = [
                e for d in events_raw
                if (e := try_parse(parse_event_log_entry, d)) is not None
            ]
        except Exception as exc:
            logger.debug("RemoteWorldState.refresh: events fetch failed: %s", exc)

    # ------------------------------------------------------------------
    # Read interface — matches WorldStateManager
    # ------------------------------------------------------------------

    async def get_all_agents(self) -> list[Agent]:
        """Return cached list of all agents."""
        return list(self._agents)

    async def get_all_structures(self) -> list[Structure]:
        """Return cached list of all structures."""
        return list(self._structures)

    async def get_all_villages(self) -> list[Village]:
        """Return cached list of all villages."""
        return list(self._villages)

    async def get_projects(self) -> list[Project]:
        """Return cached list of all projects."""
        return list(self._projects)

    async def get_event_log(self, limit: int = 100) -> list[EventLogEntry]:
        """Return the first ``limit`` entries from the cached event log."""
        return list(self._event_log[:limit])

    async def get_agents_in_view(self, bounds: Any) -> list[Agent]:
        """Return cached agents whose position falls within bounds."""
        return [
            a
            for a in self._agents
            if bounds.min_x <= a.position.x <= bounds.max_x
            and bounds.min_y <= a.position.y <= bounds.max_y
        ]

    async def get_nearest_village_to(self, x: int, y: int) -> Village | None:
        """Return nearest village by Euclidean distance from cached villages."""
        if not self._villages:
            return None
        return min(self._villages, key=lambda v: math.hypot(v.center.x - x, v.center.y - y))

    async def get_structures_in_view(self, bounds: Any) -> list[Structure]:
        """Return cached structures whose position falls within bounds."""
        return [
            s
            for s in self._structures
            if bounds.min_x <= s.position.x <= bounds.max_x
            and bounds.min_y <= s.position.y <= bounds.max_y
        ]

    def get_viewport_center(self) -> tuple[int, int] | None:
        """Viewer has no access to daemon's persisted viewport metadata; return None."""
        return None

    async def update_viewport_center(self, x: int, y: int) -> None:
        """No-op — viewer does not persist viewport position to the daemon."""

    async def despawn_agent(self, agent_id: str) -> None:
        """No-op — viewer does not control agent lifecycle; the daemon owns despawn."""

    # ------------------------------------------------------------------
    # Write-side stubs — viewer is read-only; daemon owns all mutations
    # ------------------------------------------------------------------

    async def handle_event(self, event: "InternalEvent") -> None:
        """No-op — viewer does not process raw hook events."""
        logger.warning("RemoteWorldState.handle_event called in viewer mode; ignoring")

    async def get_or_create_project(self, project_id: str, project_name: str) -> Project:
        """Not supported in viewer mode."""
        raise NotImplementedError("RemoteWorldState does not support get_or_create_project")

    async def get_or_create_session(self, session_id: str, project_id: str) -> Session:
        """Not supported in viewer mode."""
        raise NotImplementedError("RemoteWorldState does not support get_or_create_session")

    async def get_or_create_agent(
        self, session_id: str, parent_id: "str | None" = None
    ) -> Agent:
        """Not supported in viewer mode."""
        raise NotImplementedError("RemoteWorldState does not support get_or_create_agent")

    async def update_agent(self, agent_id: str, **kwargs: Any) -> None:
        """No-op — viewer does not mutate agent state."""
        logger.warning("RemoteWorldState.update_agent called in viewer mode; ignoring")

    async def add_work_units(
        self, agent_id: str, structure_type: Any, units: int
    ) -> None:
        """No-op — viewer does not accumulate work units."""
        logger.warning("RemoteWorldState.add_work_units called in viewer mode; ignoring")

    async def update_structure(self, structure_id: str, **fields: Any) -> None:
        """No-op — viewer is read-only and does not mutate structure state."""
        logger.warning("RemoteWorldState.update_structure called in viewer mode; ignoring")

    async def create_structure(
        self, village_id: str, structure_type: StructureType, position: Position
    ) -> Structure:
        """Not supported in viewer mode — viewer does not create structures."""
        raise NotImplementedError("RemoteWorldState does not support create_structure")

    async def found_village(
        self, originating_village_id: str, project_id: str, center: Any, name: str
    ) -> Village:
        """Not supported in viewer mode — viewer does not found villages."""
        raise NotImplementedError("RemoteWorldState does not support found_village")

    async def upgrade_structure_tier(self, structure_id: str, new_tier: int) -> None:
        """Not supported in viewer mode — viewer does not upgrade structure tiers."""
        raise NotImplementedError("RemoteWorldState does not support upgrade_structure_tier")

    async def get_agents_by_session(self, session_id: str) -> list[Agent]:
        """Return cached agents belonging to the given session."""
        return [a for a in self._agents if a.session_id == session_id]

    async def get_village_by_project(self, project_id: str) -> "Village | None":
        """Return the cached village for the given project, or None."""
        for v in self._villages:
            if v.project_id == project_id:
                return v
        return None

    def get_animation_frame(self, agent_id: str) -> int:
        """Return the cached animation frame for the given agent, or 0 if not tracked."""
        return self._cached_state.get("animation_frames", {}).get(agent_id, 0)

    # ------------------------------------------------------------------
    # Terrain queries — delegated to daemon via HTTP
    # ------------------------------------------------------------------

    async def get_terrain_at(self, x: int, y: int) -> TerrainType:
        """Return terrain type at position. RemoteWorldState fetches terrain from daemon."""
        data = await self._provider.fetch_terrain(x, y)
        terrain_str = data.get("terrain", "plain")
        return TerrainType(terrain_str)

    async def is_passable(self, x: int, y: int) -> bool:
        """Check if position is passable."""
        data = await self._provider.fetch_terrain(x, y)
        return data.get("passable", True)
