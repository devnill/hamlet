"""WorldStateManager — loads and maintains the in-memory world state from persistence."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from hamlet.event_processing.internal_event import HookType, InternalEvent

logger = logging.getLogger(__name__)

import dataclasses

from .grid import PositionGrid
from .rules import STRUCTURE_RULES

# Derived constants for test/external access
STAGE_THRESHOLDS: dict[str, list[int]] = {
    st.value: rules["thresholds"] for st, rules in STRUCTURE_RULES.items()
}
MATERIAL_STAGES: dict[int, str] = {i: m for i, m in enumerate(["wood", "wood", "stone", "brick"])}
from .state import EventLogEntry, WorldState
from hamlet.inference.types import TYPE_COLORS
from .types import (
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

__all__ = ["WorldStateManager"]


class WorldStateManager:
    """Manages the in-memory world state and synchronises it with persistence."""

    def __init__(self, persistence: Any) -> None:
        self._persistence = persistence
        self._lock = asyncio.Lock()
        self._state = WorldState()
        self._grid = PositionGrid()

    async def load_from_persistence(self) -> None:
        """Load all entities from persistence and rebuild in-memory state."""
        async with self._lock:
            data = await self._persistence.load_state()
            # Restore projects
            for d in data.projects:
                project = Project(
                    id=d["id"],
                    name=d["name"],
                    village_id=d.get("village_id", ""),
                    config=d.get("config_json", {}),
                )
                self._state.projects[project.id] = project

            # Restore villages
            for d in data.villages:
                village = Village(
                    id=d["id"],
                    project_id=d["project_id"],
                    name=d["name"],
                    center=Position(x=d.get("center_x", 0), y=d.get("center_y", 0)),
                    bounds=Bounds(
                        min_x=d.get("bounds_min_x", 0),
                        min_y=d.get("bounds_min_y", 0),
                        max_x=d.get("bounds_max_x", 0),
                        max_y=d.get("bounds_max_y", 0),
                    ),
                )
                self._state.villages[village.id] = village

            # Restore sessions
            for d in data.sessions:
                session = Session(
                    id=d["id"],
                    project_id=d["project_id"],
                )
                self._state.sessions[session.id] = session

            # Restore agents and register positions in grid
            for d in data.agents:
                position = Position(x=d["position_x"], y=d["position_y"])
                _inferred_type = AgentType(d.get("inferred_type", "general"))
                agent = Agent(
                    id=d["id"],
                    session_id=d["session_id"],
                    project_id=d.get("project_id", ""),
                    village_id=d.get("village_id", ""),
                    inferred_type=_inferred_type,
                    color=TYPE_COLORS.get(_inferred_type, "white"),
                    position=position,
                    last_seen=d["last_seen"],
                    state=AgentState(d.get("state", "active")),
                )
                self._state.agents[agent.id] = agent
                try:
                    self._grid.occupy(position, agent.id)
                except ValueError:
                    # Position conflict — entity remains in self._state without a grid slot.
                    # The first occupant's grid entry is kept; this entity is accessible
                    # via state lookup but not via spatial queries.
                    pass

            # Restore structures and register positions in grid
            for d in data.structures:
                position = Position(x=d["position_x"], y=d["position_y"])
                structure = Structure(
                    id=d["id"],
                    village_id=d["village_id"],
                    type=StructureType(d.get("type", "house")),
                    position=position,
                    stage=d.get("stage", 0),
                    material=d.get("material", "wood"),
                    work_units=d.get("work_units", 0),
                    work_required=d.get("work_required", 100),
                )
                self._state.structures[structure.id] = structure
                try:
                    self._grid.occupy(position, structure.id)
                except ValueError:
                    # Position conflict — entity remains in self._state without a grid slot.
                    # The first occupant's grid entry is kept; this entity is accessible
                    # via state lookup but not via spatial queries.
                    pass

            # Populate village back-references for structures
            for structure in self._state.structures.values():
                village = self._state.villages.get(structure.village_id)
                if village and structure.id not in village.structure_ids:
                    village.structure_ids.append(structure.id)

            # Restore world metadata (viewport center, etc.)
            self._state.world_metadata = dict(data.metadata)

    async def get_or_create_project(self, project_id: str, name: str) -> Project:
        """Return the existing project or create a new one with an associated village."""
        village_to_seed: Village | None = None
        async with self._lock:
            if project_id in self._state.projects:
                return self._state.projects[project_id]

            village_id = str(uuid.uuid4())
            now = datetime.now(UTC)

            project = Project(
                id=project_id,
                name=name,
                village_id=village_id,
                created_at=now,
                updated_at=now,
            )
            village = Village(
                id=village_id,
                project_id=project_id,
                name=f"{name} village",
                center=Position(0, 0),
                bounds=Bounds(0, 0, 0, 0),
            )

            self._state.projects[project_id] = project
            self._state.villages[village_id] = village

            try:
                await self._persistence.queue_write("project", project_id, project)
            except Exception as exc:
                logger.debug("Could not queue project write: %s", exc)
            try:
                await self._persistence.queue_write("village", village_id, village)
            except Exception as exc:
                logger.debug("Could not queue village write: %s", exc)

            village_to_seed = village

        # Outside the lock: _seed_initial_structures calls create_structure which
        # acquires self._lock itself; calling it inside would cause a deadlock.
        # Asyncio scheduling assumption: because this is a single-threaded event
        # loop, no other coroutine can run between the `async with self._lock`
        # block above and this await — so village_to_seed is still valid and the
        # village is already visible in self._state when seeding begins.
        if village_to_seed is not None:
            await self._seed_initial_structures(village_to_seed)

        return project

    def get_viewport_center(self) -> tuple[int, int] | None:
        """Return saved viewport center from world_metadata, or None if not present."""
        meta = self._state.world_metadata
        if "viewport_center_x" in meta and "viewport_center_y" in meta:
            try:
                return int(meta["viewport_center_x"]), int(meta["viewport_center_y"])
            except (ValueError, TypeError):
                return None
        return None

    async def update_viewport_center(self, x: int, y: int) -> None:
        """Persist viewport center to world_metadata table."""
        async with self._lock:
            self._state.world_metadata["viewport_center_x"] = str(x)
            self._state.world_metadata["viewport_center_y"] = str(y)
        try:
            await self._persistence.queue_write(
                "world_metadata", "viewport_center", {"viewport_center_x": x, "viewport_center_y": y}
            )
        except Exception:
            logger.debug("update_viewport_center: could not queue write")

    async def get_or_create_session(self, session_id: str, project_id: str) -> Session:
        """Return the existing session or create a new one for the given project."""
        async with self._lock:
            if session_id in self._state.sessions:
                return self._state.sessions[session_id]

            now = datetime.now(UTC)
            session = Session(
                id=session_id,
                project_id=project_id,
                started_at=now,
                last_activity=now,
            )

            self._state.sessions[session_id] = session

            try:
                await self._persistence.queue_write("session", session_id, session)
            except Exception as exc:
                logger.debug("Could not queue session write: %s", exc)

            return session

    async def get_village(self, village_id: str) -> Village | None:
        """Return the village with the given id, or None if not found."""
        async with self._lock:
            return self._state.villages.get(village_id)

    async def get_village_by_project(self, project_id: str) -> Village | None:
        """Return the village associated with the given project, or None."""
        async with self._lock:
            project = self._state.projects.get(project_id)
            if project is not None:
                return self._state.villages.get(project.village_id)
            for village in self._state.villages.values():
                if village.project_id == project_id:
                    return village
            return None

    def _expand_village_bounds(self, village: Village, position: Position) -> None:
        """Expand the village bounds to include position. Caller must hold the lock."""
        village.bounds.min_x = min(village.bounds.min_x, position.x)
        village.bounds.min_y = min(village.bounds.min_y, position.y)
        village.bounds.max_x = max(village.bounds.max_x, position.x)
        village.bounds.max_y = max(village.bounds.max_y, position.y)

    # ------------------------------------------------------------------
    # Agent CRUD
    # ------------------------------------------------------------------

    MAX_SPAWN_RADIUS = 3

    def _find_spawn_position(
        self, village: Village, parent: Agent | None, occupied: set[Position]
    ) -> Position:
        """Return the first unoccupied position near parent (or village center).

        Caller must hold the lock.  Visits positions in order of increasing
        Chebyshev distance from origin so the closest available cell is chosen.
        Raises RuntimeError if all cells within MAX_SPAWN_RADIUS are occupied.
        """
        origin = parent.position if parent is not None else village.center
        for radius in range(0, self.MAX_SPAWN_RADIUS + 1):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if max(abs(dx), abs(dy)) != radius:
                        continue  # inner cells already checked at smaller radii
                    candidate = Position(origin.x + dx, origin.y + dy)
                    if candidate not in occupied:
                        return candidate
        raise RuntimeError(
            f"No spawn position available within radius {self.MAX_SPAWN_RADIUS} of {origin}"
        )

    async def get_or_create_agent(
        self, session_id: str, parent_id: str | None = None
    ) -> Agent:
        """Return the primary agent for this session, or create one."""
        async with self._lock:
            session = self._state.sessions.get(session_id)
            project_id = session.project_id if session is not None else ""

            # Return primary (first) agent if session already has one
            if session is not None and session.agent_ids:
                primary_id = session.agent_ids[0]
                existing = self._state.agents.get(primary_id)
                if existing is not None:
                    return existing

            # Resolve village for spawn positioning
            project = self._state.projects.get(project_id)
            village: Village | None = None
            if project is not None:
                village = self._state.villages.get(project.village_id)
            if village is None:
                # Fall back to any village for this project_id
                for v in self._state.villages.values():
                    if v.project_id == project_id:
                        village = v
                        break

            # Need a village to spawn — create a placeholder if still None
            village_to_seed: Village | None = None
            if village is None:
                village_id = str(uuid.uuid4())
                village = Village(
                    id=village_id,
                    project_id=project_id,
                    name="village",
                    center=Position(0, 0),
                    bounds=Bounds(0, 0, 0, 0),
                )
                self._state.villages[village_id] = village
                try:
                    await self._persistence.queue_write("village", village_id, village)
                except Exception as exc:
                    logger.debug("Could not queue village write: %s", exc)
                village_to_seed = village

            # Resolve parent agent
            parent: Agent | None = None
            if parent_id is not None:
                parent = self._state.agents.get(parent_id)

            occupied = self._grid.get_occupied_positions()
            position = self._find_spawn_position(village, parent, occupied)

            agent_id = str(uuid.uuid4())
            now = datetime.now(UTC)
            inferred_type = AgentType.GENERAL
            color = TYPE_COLORS.get(inferred_type, "white")
            agent = Agent(
                id=agent_id,
                session_id=session_id,
                project_id=project_id,
                village_id=village.id,
                inferred_type=inferred_type,
                color=color,
                position=position,
                last_seen=now,
                state=AgentState.ACTIVE,
                parent_id=parent_id,
                created_at=now,
                updated_at=now,
            )

            try:
                self._grid.occupy(position, agent.id)
            except ValueError:
                logger.warning(
                    "Position %s already occupied; agent %s placed without grid slot",
                    position,
                    agent_id,
                )

            self._expand_village_bounds(village, position)

            if session is not None and agent.id not in session.agent_ids:
                session.agent_ids.append(agent.id)
            elif session is None:
                logger.warning(
                    "get_or_create_agent: no session found for session_id=%s; "
                    "agent will not be tracked in session",
                    session_id,
                )
            if agent.id not in village.agent_ids:
                village.agent_ids.append(agent.id)

            self._state.agents[agent.id] = agent

            try:
                await self._persistence.queue_write("agent", agent.id, agent)
            except Exception as exc:
                logger.debug("Could not queue agent write: %s", exc)

        # Outside the lock: _seed_initial_structures calls create_structure which
        # acquires self._lock itself; calling it inside would cause a deadlock.
        # Asyncio scheduling assumption: because this is a single-threaded event
        # loop, no other coroutine can run between the `async with self._lock`
        # block above and this await — so village_to_seed is still valid and the
        # village is already visible in self._state when seeding begins.
        if village_to_seed is not None:
            await self._seed_initial_structures(village_to_seed)

        return agent

    async def update_agent(self, agent_id: str, **fields: Any) -> None:
        """Update the given agent's fields and queue a persistence write."""
        async with self._lock:
            agent = self._state.agents.get(agent_id)
            if agent is None:
                logger.debug("update_agent: agent %s not found", agent_id)
                return
            valid_fields = {f.name for f in dataclasses.fields(agent)}
            for key, value in fields.items():
                if key not in valid_fields:
                    logger.warning("update_agent: unknown field %r — skipping", key)
                    continue
                setattr(agent, key, value)
            try:
                await self._persistence.queue_write("agent", agent.id, agent)
            except Exception as exc:
                logger.debug("Could not queue agent write: %s", exc)

    async def get_agents_by_session(self, session_id: str) -> list[Agent]:
        """Return all agents that belong to the given session."""
        async with self._lock:
            return [
                a for a in self._state.agents.values() if a.session_id == session_id
            ]

    async def get_agents_by_village(self, village_id: str) -> list[Agent]:
        """Return all agents that belong to the given village."""
        async with self._lock:
            village = self._state.villages.get(village_id)
            if village is None:
                return []
            return [
                self._state.agents[aid]
                for aid in village.agent_ids
                if aid in self._state.agents
            ]

    # ------------------------------------------------------------------
    # Structure CRUD
    # ------------------------------------------------------------------

    async def _create_structure_locked(
        self, village_id: str, structure_type: StructureType, position: Position
    ) -> Structure:
        """Create a structure without acquiring the lock. Caller must hold self._lock."""
        now = datetime.now(UTC)
        structure_id = str(uuid.uuid4())
        rules = STRUCTURE_RULES.get(structure_type)
        if rules is None:
            logger.warning("create_structure: no rules defined for %s", structure_type)
            raise ValueError(f"No structure rules for {structure_type}")
        thresholds = rules["thresholds"]
        structure = Structure(
            id=structure_id,
            village_id=village_id,
            type=structure_type,
            position=position,
            stage=0,
            material=rules["materials"][0],
            work_units=0,
            work_required=thresholds[0],
            created_at=now,
            updated_at=now,
        )
        self._state.structures[structure.id] = structure
        try:
            self._grid.occupy(position, structure.id)
        except ValueError:
            logger.warning(
                "Position %s already occupied; structure %s placed without grid slot",
                position,
                structure_id,
            )
        village = self._state.villages.get(village_id)
        if village is not None:
            if structure.id not in village.structure_ids:
                village.structure_ids.append(structure.id)
            self._expand_village_bounds(village, position)
        try:
            await self._persistence.queue_write("structure", structure.id, structure)
        except Exception as exc:
            logger.debug("Could not queue structure write: %s", exc)
        return structure

    async def _seed_initial_structures(self, village: Village) -> None:
        """Create one LIBRARY, WORKSHOP, and FORGE near the village center.

        Must be called WITHOUT holding self._lock — delegates to create_structure
        which acquires the lock itself. Skips positions already occupied. Logs
        and continues on failure so village creation is never blocked.
        """
        center = village.center
        offsets = [(1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)]
        types_to_seed = [StructureType.LIBRARY, StructureType.WORKSHOP, StructureType.FORGE]
        placed = 0
        for dx, dy in offsets:
            if placed >= len(types_to_seed):
                break
            pos = Position(x=center.x + dx, y=center.y + dy)
            if self._grid.is_occupied(pos):
                continue
            structure_type = types_to_seed[placed]
            try:
                await self.create_structure(
                    village_id=village.id,
                    structure_type=structure_type,
                    position=pos,
                )
                placed += 1
            except Exception as exc:
                logger.warning(
                    "_seed_initial_structures: failed to create %s at %s: %s",
                    structure_type,
                    pos,
                    exc,
                )
        if placed < len(types_to_seed):
            logger.warning(
                "Village %s: only seeded %d/%d initial structures — not enough unoccupied adjacent positions",
                village.id, placed, len(types_to_seed)
            )

    async def create_structure(
        self, village_id: str, structure_type: StructureType, position: Position
    ) -> Structure:
        """Create a new structure in the given village at position."""
        async with self._lock:
            return await self._create_structure_locked(village_id, structure_type, position)

    async def update_structure(self, structure_id: str, **fields: Any) -> None:
        """Update the given structure's fields and queue persistence."""
        async with self._lock:
            structure = self._state.structures.get(structure_id)
            if structure is None:
                logger.debug("update_structure: structure %s not found", structure_id)
                return
            valid_fields = {f.name for f in dataclasses.fields(structure)}
            for key, value in fields.items():
                if key not in valid_fields:
                    logger.warning("update_structure: unknown field %r — skipping", key)
                    continue
                setattr(structure, key, value)
            try:
                await self._persistence.queue_write("structure", structure.id, structure)
            except Exception as exc:
                logger.debug("Could not queue structure write: %s", exc)

    async def get_structure(self, structure_id: str) -> Structure | None:
        """Return the structure with the given id, or None."""
        async with self._lock:
            return self._state.structures.get(structure_id)

    async def get_structures_by_village(self, village_id: str) -> list[Structure]:
        """Return all structures belonging to the given village."""
        async with self._lock:
            village = self._state.villages.get(village_id)
            if village is None:
                return []
            return [
                self._state.structures[sid]
                for sid in village.structure_ids
                if sid in self._state.structures
            ]

    async def add_work_units(
        self, agent_id: str, structure_type: StructureType, units: int
    ) -> None:
        """Add work units to the agent's total and to the nearest structure of the given type.

        Advances structure stage when cumulative work_units meets the threshold.
        Work units reset to 0 on stage advancement.
        Material updates with stage using STRUCTURE_RULES.
        """
        async with self._lock:
            agent = self._state.agents.get(agent_id)
            if agent is None:
                logger.debug("add_work_units: agent %s not found", agent_id)
                return

            agent.total_work_units += units

            # Find the nearest structure of the given type in the agent's village
            village = self._state.villages.get(agent.village_id)
            if village is None:
                logger.debug(
                    "add_work_units: village %s not found for agent %s",
                    agent.village_id,
                    agent_id,
                )
                try:
                    await self._persistence.queue_write("agent", agent.id, agent)
                except Exception as exc:
                    logger.debug("Could not queue agent write: %s", exc)
                return

            # Find nearest matching structure by Chebyshev distance
            nearest_structure: Structure | None = None
            nearest_dist = float("inf")
            for sid in village.structure_ids:
                s = self._state.structures.get(sid)
                if s is None or s.type != structure_type:
                    continue
                dist = max(
                    abs(s.position.x - agent.position.x),
                    abs(s.position.y - agent.position.y),
                )
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_structure = s

            if nearest_structure is None:
                logger.debug(
                    "add_work_units: no structure of type %s found in village %s",
                    structure_type.value,
                    agent.village_id,
                )
                try:
                    await self._persistence.queue_write("agent", agent.id, agent)
                except Exception as exc:
                    logger.debug("Could not queue agent write: %s", exc)
                return

            # Check for stage advancement — skip accumulation on fully-built structures
            rules = STRUCTURE_RULES.get(structure_type)
            if rules is None:
                logger.warning("add_work_units: no rules defined for %s", structure_type)
                return
            thresholds = rules["thresholds"]
            materials = rules["materials"]
            current_stage = nearest_structure.stage
            if current_stage < 3:
                nearest_structure.work_units += units
                threshold = thresholds[current_stage]
                if nearest_structure.work_units >= threshold:
                    new_stage = current_stage + 1
                    nearest_structure.stage = new_stage
                    nearest_structure.work_units = 0
                    nearest_structure.material = materials[new_stage]
                    if new_stage < 3:
                        nearest_structure.work_required = thresholds[new_stage]
                    else:
                        nearest_structure.work_required = 0

            now = datetime.now(UTC)
            nearest_structure.updated_at = now
            agent.updated_at = now

            try:
                await self._persistence.queue_write("agent", agent.id, agent)
            except Exception as exc:
                logger.debug("Could not queue agent write: %s", exc)
            try:
                await self._persistence.queue_write(
                    "structure", nearest_structure.id, nearest_structure
                )
            except Exception as exc:
                logger.debug("Could not queue structure write: %s", exc)

    # ------------------------------------------------------------------
    # Viewport / TUI queries (no lock needed for read-only snapshot use,
    # but lock-protected for consistency)
    # ------------------------------------------------------------------

    async def get_agents_in_view(self, bounds: Any) -> list[Agent]:
        """Return agents whose position falls within the given bounding box.

        ``bounds`` is duck-typed: it must expose ``min_x``, ``min_y``,
        ``max_x``, and ``max_y`` attributes.
        """
        async with self._lock:
            return [
                a
                for a in self._state.agents.values()
                if bounds.min_x <= a.position.x <= bounds.max_x
                and bounds.min_y <= a.position.y <= bounds.max_y
            ]

    async def get_structures_in_view(self, bounds: Any) -> list[Structure]:
        """Return structures whose position falls within the given bounding box."""
        async with self._lock:
            return [
                s
                for s in self._state.structures.values()
                if bounds.min_x <= s.position.x <= bounds.max_x
                and bounds.min_y <= s.position.y <= bounds.max_y
            ]

    async def get_event_log(self, limit: int = 100) -> list[EventLogEntry]:
        """Return the last ``limit`` entries from the event log."""
        async with self._lock:
            return list(self._state.event_log[-limit:])

    async def get_projects(self) -> list[Project]:
        """Return a snapshot list of all known projects."""
        async with self._lock:
            return list(self._state.projects.values())

    async def get_all_agents(self) -> list[Agent]:
        """Return a snapshot list of all known agents."""
        async with self._lock:
            return list(self._state.agents.values())

    async def get_all_structures(self) -> list[Structure]:
        """Return a snapshot of all structures."""
        async with self._lock:
            return list(self._state.structures.values())

    async def get_all_villages(self) -> list[Village]:
        """Return a snapshot of all villages."""
        async with self._lock:
            return list(self._state.villages.values())

    async def handle_event(self, event: InternalEvent) -> None:
        """Append event to in-memory event log. Called by EventProcessor."""
        try:
            async with self._lock:
                if event.hook_type == HookType.Notification:
                    summary = f"Notification: {event.notification_message or ''}"
                elif event.hook_type == HookType.Stop:
                    summary = f"Stop: {event.stop_reason or ''}"
                else:
                    summary = f"{event.hook_type.value}: {event.tool_name or ''}"
                entry = EventLogEntry(
                    id=event.id,
                    timestamp=event.received_at,
                    session_id=event.session_id or "",
                    project_id=event.project_id or "",
                    hook_type=event.hook_type.value,
                    tool_name=event.tool_name,
                    summary=summary,
                )
                self._state.event_log.append(entry)
                if len(self._state.event_log) > 100:
                    self._state.event_log = self._state.event_log[-100:]
        except Exception as exc:
            logger.warning("handle_event: failed to log event: %s", exc)
