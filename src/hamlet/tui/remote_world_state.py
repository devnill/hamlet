"""RemoteWorldState — read-only world state backed by HTTP-polled daemon data."""
from __future__ import annotations

import logging
import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from hamlet.world_state.state import EventLogEntry
from hamlet.world_state.types import (
    Agent,
    AgentState,
    AgentType,
    Bounds,
    Position,
    Project,
    Session,
    Structure,
    StructureType,
    Village,
)

if TYPE_CHECKING:
    from hamlet.event_processing.internal_event import InternalEvent
    from hamlet.tui.remote_state import RemoteStateProvider

logger = logging.getLogger(__name__)

__all__ = ["RemoteWorldState"]


# ---------------------------------------------------------------------------
# Deserialization helpers
# ---------------------------------------------------------------------------

def _parse_datetime(value: Any) -> datetime:
    """Parse an ISO timestamp string to a timezone-aware datetime, or return now."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            pass
    return datetime.now(UTC)


def _parse_position(value: Any) -> Position:
    """Parse a position dict {"x": int, "y": int} to a Position."""
    if isinstance(value, dict):
        return Position(x=int(value.get("x", 0)), y=int(value.get("y", 0)))
    return Position(x=0, y=0)


def _parse_bounds(value: Any) -> Bounds:
    """Parse a bounds dict to a Bounds object."""
    if isinstance(value, dict):
        return Bounds(
            min_x=int(value.get("min_x", 0)),
            min_y=int(value.get("min_y", 0)),
            max_x=int(value.get("max_x", 0)),
            max_y=int(value.get("max_y", 0)),
        )
    return Bounds(min_x=0, min_y=0, max_x=0, max_y=0)


def _parse_agent(d: dict) -> Agent:
    """Deserialize a dict to an Agent dataclass."""
    return Agent(
        id=d.get("id", ""),
        session_id=d.get("session_id", ""),
        project_id=d.get("project_id", ""),
        village_id=d.get("village_id", ""),
        inferred_type=AgentType(d.get("inferred_type", "general")),
        color=d.get("color", "white"),
        position=_parse_position(d.get("position", {})),
        last_seen=_parse_datetime(d.get("last_seen")),
        state=AgentState(d.get("state", "active")),
        parent_id=d.get("parent_id"),
        current_activity=d.get("current_activity"),
        total_work_units=int(d.get("total_work_units", 0)),
        created_at=_parse_datetime(d.get("created_at")),
        updated_at=_parse_datetime(d.get("updated_at")),
    )


def _parse_structure(d: dict) -> Structure:
    """Deserialize a dict to a Structure dataclass."""
    return Structure(
        id=d.get("id", ""),
        village_id=d.get("village_id", ""),
        type=StructureType(d.get("type", "house")),
        position=_parse_position(d.get("position", {})),
        stage=int(d.get("stage", 0)),
        material=d.get("material", "wood"),
        work_units=int(d.get("work_units", 0)),
        work_required=int(d.get("work_required", 100)),
        created_at=_parse_datetime(d.get("created_at")),
        updated_at=_parse_datetime(d.get("updated_at")),
    )


def _parse_village(d: dict) -> Village:
    """Deserialize a dict to a Village dataclass."""
    return Village(
        id=d.get("id", ""),
        project_id=d.get("project_id", ""),
        name=d.get("name", ""),
        center=_parse_position(d.get("center", {})),
        bounds=_parse_bounds(d.get("bounds", {})),
        structure_ids=list(d.get("structure_ids", [])),
        agent_ids=list(d.get("agent_ids", [])),
        has_expanded=bool(d.get("has_expanded", False)),
        created_at=_parse_datetime(d.get("created_at")),
        updated_at=_parse_datetime(d.get("updated_at")),
    )


def _parse_project(d: dict) -> Project:
    """Deserialize a dict to a Project dataclass."""
    return Project(
        id=d.get("id", ""),
        name=d.get("name", ""),
        village_id=d.get("village_id", ""),
        config=dict(d.get("config", {})),
        created_at=_parse_datetime(d.get("created_at")),
        updated_at=_parse_datetime(d.get("updated_at")),
    )


def _parse_event_log_entry(d: dict) -> EventLogEntry:
    """Deserialize a dict to an EventLogEntry dataclass."""
    return EventLogEntry(
        id=d.get("id", ""),
        timestamp=_parse_datetime(d.get("timestamp")),
        session_id=d.get("session_id", ""),
        project_id=d.get("project_id", ""),
        hook_type=d.get("hook_type", ""),
        tool_name=d.get("tool_name"),
        summary=d.get("summary", ""),
    )


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

    async def refresh(self) -> None:
        """Fetch fresh state from the daemon and update local caches."""
        try:
            state = await self._provider.fetch_state()
            self._cached_state = state

            self._agents = [
                _parse_agent(d)
                for d in state.get("agents", [])
            ]
            self._structures = [
                _parse_structure(d)
                for d in state.get("structures", [])
            ]
            self._villages = [
                _parse_village(d)
                for d in state.get("villages", [])
            ]
            self._projects = [
                _parse_project(d)
                for d in state.get("projects", [])
            ]
        except Exception as exc:
            logger.debug("RemoteWorldState.refresh: state fetch failed: %s", exc)

        try:
            events_raw = await self._provider.fetch_events()
            self._event_log = [_parse_event_log_entry(d) for d in events_raw]
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
