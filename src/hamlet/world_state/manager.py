"""WorldStateManager — loads and maintains the in-memory world state from persistence."""
from __future__ import annotations

import asyncio
import logging
import math
import random
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from hamlet.event_processing.internal_event import HookType, InternalEvent

if TYPE_CHECKING:
    from hamlet.protocols import PersistenceProtocol

logger = logging.getLogger(__name__)

import dataclasses

from .grid import PositionGrid
from .rules import STRUCTURE_RULES
from .terrain import TerrainConfig, TerrainGenerator, TerrainGrid, TerrainType

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

    # Minimum distance between village centers
    MIN_VILLAGE_DISTANCE = 15

    def __init__(
        self, persistence: "PersistenceProtocol", terrain_config: TerrainConfig | None = None
    ) -> None:
        self._persistence = persistence
        self._lock = asyncio.Lock()
        self._state = WorldState()
        self._grid = PositionGrid()
        self._terrain_grid: TerrainGrid | None = None
        self._terrain_config = terrain_config  # Optional config from settings

    async def load_from_persistence(self) -> None:
        """Load all entities from persistence and rebuild the in-memory world state.

        Fetches projects, villages, sessions, agents, and structures from the
        persistence layer and reconstructs the corresponding in-memory objects.
        Agent and structure positions are registered in the spatial grid; position
        conflicts (duplicate occupants) are silently skipped — the first occupant
        keeps the grid slot and the conflicting entity is accessible only via
        state lookup, not spatial queries.

        Acquires self._lock for the duration of the rebuild.

        Note: all agents are loaded as ``AgentState.ZOMBIE`` regardless of their
        persisted state. The inference engine's zombie detection is memory-only
        and empty at startup, so restoring non-zombie states would leave phantom
        active agents on screen. New hook events from live Claude sessions will
        promote agents back to ACTIVE via the normal inference path.
        """
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
                    has_expanded=bool(d.get("has_expanded", False)),
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
                    state=AgentState.ZOMBIE,  # always start as zombie on reload; new events will promote to active
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

            # Initialize terrain grid from seed (or generate new seed)
            terrain_seed = self._state.world_metadata.get("terrain_seed")
            if terrain_seed is None:
                terrain_seed = str(random.randint(0, 2**31 - 1))
                self._state.world_metadata["terrain_seed"] = terrain_seed
                # Persist the new seed so terrain is deterministic across restarts
                await self._persistence.queue_write(
                    "world_metadata", "terrain_seed", {"key": "terrain_seed", "value": terrain_seed}
                )
            # Merge persisted seed with config from settings (if provided)
            if self._terrain_config is not None:
                # Use config from settings but override with persisted seed
                config = TerrainConfig(
                    seed=int(terrain_seed),
                    **{k: v for k, v in dataclasses.asdict(self._terrain_config).items() if k != "seed"}
                )
            else:
                config = TerrainConfig(seed=int(terrain_seed))
            self._terrain_grid = TerrainGrid(TerrainGenerator(config))

    async def get_terrain_at(self, x: int, y: int) -> TerrainType:
        """Return the terrain type at position (x, y).

        Returns PLAIN if terrain grid not yet initialized.
        """
        if self._terrain_grid is None:
            return TerrainType.PLAIN
        return self._terrain_grid.get_terrain(Position(x, y))

    async def is_passable(self, x: int, y: int) -> bool:
        """Check if position (x, y) is passable for agents and structures.

        Returns True if terrain grid not yet initialized (graceful fallback).
        """
        if self._terrain_grid is None:
            return True
        return self._terrain_grid.is_passable(Position(x, y))

    @property
    def terrain_grid(self) -> "TerrainGrid | None":
        """Return the terrain grid for rendering, or None if not initialized."""
        return self._terrain_grid

    def _find_village_position(
        self,
        existing_villages: list[Village],
        occupied_positions: set[Position],
    ) -> Position:
        """Find a valid position for a new village using spiral search.

        Searches from origin (0, 0) outward, checking:
        1. Terrain is passable (not WATER or MOUNTAIN)
        2. Position is not occupied by an existing entity
        3. Position is at least MIN_VILLAGE_DISTANCE from other village centers

        Raises RuntimeError if no valid position found within MAX_SEARCH_RADIUS.

        Caller must hold self._lock (or ensure no concurrent mutations).
        """
        MAX_SEARCH_RADIUS = 100

        for radius in range(0, MAX_SEARCH_RADIUS + 1):
            # Spiral outward, checking perimeter of each ring
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    # Only check perimeter cells (not inner cells)
                    if abs(dx) != radius and abs(dy) != radius:
                        continue
                    candidate = Position(dx, dy)

                    # Check terrain passability
                    if self._terrain_grid is not None:
                        if not self._terrain_grid.is_passable(candidate):
                            continue

                    # Check not occupied
                    if candidate in occupied_positions:
                        continue

                    # Check minimum distance from other village centers
                    too_close = False
                    for village in existing_villages:
                        dist = math.hypot(
                            candidate.x - village.center.x,
                            candidate.y - village.center.y,
                        )
                        if dist < self.MIN_VILLAGE_DISTANCE:
                            too_close = True
                            break
                    if too_close:
                        continue

                    return candidate

        raise RuntimeError(
            f"No valid village position found within {MAX_SEARCH_RADIUS} units of origin"
        )

    async def get_or_create_project(self, project_id: str, name: str) -> Project:
        """Return the existing project or create a new one with an associated village.

        If the project already exists it is returned immediately. Otherwise a new
        ``Project`` and its companion ``Village`` are persisted and an initial set
        of structures (LIBRARY, WORKSHOP, FORGE) is seeded near the village center.

        Acquires self._lock while mutating in-memory state and queuing persistence
        writes. Structure seeding occurs outside the lock to avoid a deadlock with
        ``create_structure``.

        Args:
            project_id: Stable identifier for the project (e.g. the Claude project ID).
            name: Human-readable project name used for the village label.

        Returns:
            The existing or newly created ``Project`` instance.
        """
        village_to_seed: Village | None = None
        async with self._lock:
            if project_id in self._state.projects:
                return self._state.projects[project_id]

            village_id = str(uuid.uuid4())
            now = datetime.now(UTC)

            # Find a valid position for the village using terrain-aware placement
            occupied_positions = self._grid.get_occupied_positions()
            village_center = self._find_village_position(
                list(self._state.villages.values()),
                occupied_positions,
            )

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
                center=village_center,
                bounds=Bounds(
                    village_center.x,
                    village_center.y,
                    village_center.x,
                    village_center.y,
                ),
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
        """Return the existing session or create a new one for the given project.

        If a session with ``session_id`` already exists it is returned without
        modification. Otherwise a new ``Session`` is created, stored in memory,
        and queued for persistence.

        Acquires self._lock.

        Args:
            session_id: Unique identifier for the Claude session.
            project_id: Identifier of the project this session belongs to.

        Returns:
            The existing or newly created ``Session`` instance.
        """
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
        """Return the village associated with the given project, or None.

        Looks up the project's ``village_id`` first; falls back to a linear scan
        of all villages when the project is not found.

        Acquires self._lock.

        Args:
            project_id: ID of the project whose village is requested.

        Returns:
            The associated ``Village`` instance, or ``None`` if not found.
        """
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
        """Return the primary agent for this session, or create and register a new one.

        If the session already has at least one agent, the first (primary) agent is
        returned. Otherwise a new ``Agent`` is spawned:

        - Position is chosen via ``_find_spawn_position``: the closest unoccupied
          cell within ``MAX_SPAWN_RADIUS`` of the parent agent (or village center).
        - The agent is registered in the spatial grid and village/session back-references.
        - A village is created on-the-fly when none exists for the project.
        - The new agent is queued for persistence.

        Acquires self._lock. Structure seeding (when a new village is created)
        occurs outside the lock to avoid deadlock with ``create_structure``.

        Args:
            session_id: Session the new agent belongs to.
            parent_id: ID of the parent agent used as the spawn-position origin,
                or ``None`` to spawn near the village center.

        Returns:
            The primary ``Agent`` for the session (existing or newly created).
        """
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
        """Update the given agent's fields and queue a persistence write.

        Only fields that correspond to declared ``Agent`` dataclass attributes are
        applied; unknown keys are logged as warnings and skipped.

        Acquires self._lock.

        Args:
            agent_id: ID of the agent to update.
            **fields: Keyword arguments mapping agent attribute names to new values.
        """
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
        """Return all agents that belong to the given session.

        Acquires self._lock.

        Args:
            session_id: The session whose agents are requested.

        Returns:
            List of ``Agent`` objects whose ``session_id`` matches the argument.
            Returns an empty list if no agents are found.
        """
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

    async def despawn_agent(self, agent_id: str) -> None:
        """Remove an agent from world state and queue its deletion from persistence."""
        async with self._lock:
            agent = self._state.agents.pop(agent_id, None)
            if agent is None:
                return  # no-op if already gone
            # Free grid position
            try:
                self._grid.vacate(agent.position)
            except Exception as e:
                logger.warning(
                    "despawn_agent: failed to vacate grid position for agent %s: %s",
                    agent_id,
                    e,
                )
            # Remove from village's agent_ids
            village = self._state.villages.get(agent.village_id)
            if village and agent_id in village.agent_ids:
                village.agent_ids.remove(agent_id)
            # Remove from session's agent_ids
            session = self._state.sessions.get(agent.session_id)
            if session and agent_id in session.agent_ids:
                session.agent_ids.remove(agent_id)
        # Queue DB delete outside the lock (persistence is async-safe)
        await self._persistence.delete_agent(agent_id)

    # ------------------------------------------------------------------
    # Structure CRUD
    # ------------------------------------------------------------------

    async def _create_structure_locked(
        self, village_id: str, structure_type: StructureType, position: Position
    ) -> Structure:
        """Create a structure without acquiring the lock. Caller must hold self._lock."""
        # Validate terrain is passable before creating structure
        if self._terrain_grid is not None:
            terrain = self._terrain_grid.get_terrain(position)
            if not terrain.passable:
                raise ValueError(
                    f"Cannot build {structure_type.value} on {terrain.value} terrain at {position}"
                )

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

    def _find_free_position_outside(self, center: "Position", tier: int) -> "Position":
        """Find nearest free cell outside the (2*tier-1)x(2*tier-1) footprint.

        Caller must hold self._lock (or ensure no concurrent mutations).
        Searches outward from the footprint edge and returns the first unoccupied cell.
        Continues expanding indefinitely until a free cell is found (up to 200 rings).
        """
        half = tier  # start just outside the footprint
        for radius in range(half, half + 200):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) == radius or abs(dy) == radius:
                        pos = Position(center.x + dx, center.y + dy)
                        if not self._grid.is_occupied(pos):
                            return pos
        # Absolute fallback: far corner that is highly unlikely to be occupied
        fallback = Position(center.x + 500, center.y + 500)
        logger.warning("_find_free_position_outside: exhausted search, using fallback %s", fallback)
        return fallback

    async def upgrade_structure_tier(self, structure_id: str, new_tier: int) -> None:
        """Upgrade a structure's size_tier, expanding its footprint and displacing agents.

        Steps:
        1. Vacate the structure's old footprint from the grid.
        2. Find any agents occupying cells in the new (larger) footprint.
        3. Move those agents to the nearest free cell outside the new footprint.
        4. Occupy the new footprint with the structure.
        5. Update the structure's size_tier and queue persistence.

        Acquires self._lock.

        Args:
            structure_id: ID of the structure to upgrade.
            new_tier: The new size_tier value (must be > current tier).
        """
        async with self._lock:
            structure = self._state.structures.get(structure_id)
            if structure is None:
                logger.debug("upgrade_structure_tier: structure %s not found", structure_id)
                return

            old_tier = structure.size_tier
            center = structure.position

            # Vacate the old footprint
            self._grid.vacate_footprint(center, old_tier, structure.id)

            # Compute the new footprint cells
            new_footprint = self._grid.footprint_positions(center, new_tier)

            # Find agents occupying new footprint cells (deduplicated; skip non-agent occupants)
            seen_agent_ids: set[str] = set()
            agents_to_displace: list[Agent] = []
            for pos in new_footprint:
                occupant_id = self._grid.get_entity_at(pos)
                if occupant_id is not None and occupant_id not in seen_agent_ids:
                    agent = self._state.agents.get(occupant_id)
                    if agent is not None:
                        seen_agent_ids.add(occupant_id)
                        agents_to_displace.append(agent)
                    else:
                        logger.warning(
                            "upgrade_structure_tier: non-agent occupant %s at %s — cannot displace",
                            occupant_id, pos,
                        )

            # Displace agents one at a time, computing free position after each vacate
            # so subsequent agents see the updated grid state (avoids duplicate targets).
            for agent in agents_to_displace:
                self._grid.vacate(agent.position)
                free_pos = self._find_free_position_outside(center, new_tier)
                try:
                    self._grid.occupy(free_pos, agent.id)
                    agent.position = free_pos  # only update position on success
                except ValueError:
                    logger.warning(
                        "upgrade_structure_tier: free_pos %s already taken displacing agent %s; "
                        "agent left off-grid",
                        free_pos,
                        agent.id,
                    )
                try:
                    await self._persistence.queue_write("agent", agent.id, agent)
                except Exception as exc:
                    logger.debug("Could not queue agent write after displacement: %s", exc)

            # Occupy new (expanded) footprint
            self._grid.occupy_footprint(center, new_tier, structure.id)

            # Update the structure's tier
            structure.size_tier = new_tier
            structure.updated_at = datetime.now(UTC)
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
        """Add work units to an agent and to the nearest structure of the given type.

        Increments the agent's ``total_work_units`` and applies ``units`` to the
        nearest (by Chebyshev distance) structure of ``structure_type`` in the
        agent's village. When the structure's cumulative ``work_units`` reaches the
        threshold defined in ``STRUCTURE_RULES``, the structure advances one stage:
        ``work_units`` resets to 0, ``material`` and ``work_required`` are updated
        from the rule table. Fully-built structures (stage 3) are not modified.

        Both the agent and the updated structure are queued for persistence writes.
        If no matching structure is found, only the agent's total is updated.

        Acquires self._lock.

        Args:
            agent_id: ID of the agent performing the work.
            structure_type: The type of structure to credit work units to.
            units: Number of work units to award.
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

        Acquires self._lock.

        Args:
            bounds: Duck-typed viewport object that exposes ``min_x``, ``min_y``,
                ``max_x``, and ``max_y`` integer attributes (inclusive bounds).

        Returns:
            List of ``Agent`` objects whose grid position lies within the viewport.
        """
        async with self._lock:
            return [
                a
                for a in self._state.agents.values()
                if bounds.min_x <= a.position.x <= bounds.max_x
                and bounds.min_y <= a.position.y <= bounds.max_y
            ]

    async def get_nearest_village_to(self, x: int, y: int) -> Village | None:
        """Return the village whose center is nearest to (x, y), or None if no villages."""
        async with self._lock:
            villages = list(self._state.villages.values())
            if not villages:
                return None
            return min(villages, key=lambda v: math.hypot(v.center.x - x, v.center.y - y))

    async def get_structures_in_view(self, bounds: Any) -> list[Structure]:
        """Return structures whose position falls within the given bounding box.

        Acquires self._lock.

        Args:
            bounds: Duck-typed viewport object that exposes ``min_x``, ``min_y``,
                ``max_x``, and ``max_y`` integer attributes (inclusive bounds).

        Returns:
            List of ``Structure`` objects whose grid position lies within the viewport.
        """
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

    async def found_village(
        self, originating_village_id: str, project_id: str, center: Position, name: str
    ) -> Village:
        """Create a new village for *project_id* at *center* and persist it.

        If any existing village center is within 5 cells of *center* the
        existing village is returned without creating a duplicate (idempotency
        guard against concurrent ticks).

        Sets ``has_expanded = True`` on the originating village (identified by
        *originating_village_id*) so that subsequent ticks do not re-trigger
        expansion for the same village.

        Acquires self._lock.

        Args:
            originating_village_id: ID of the village that triggered expansion.
            project_id: ID of the project that is founding the new settlement.
            center: World-coordinate center of the new village.
            name: Human-readable name for the new village.

        Returns:
            The newly created ``Village``, or an existing one if a nearby
            village is already present.
        """
        village_to_seed: Village | None = None
        async with self._lock:
            # Idempotency guard: return existing village if one is already near center.
            # Even on early return, mark originating village as expanded so future
            # ticks don't retry (the outpost already exists nearby).
            for existing in self._state.villages.values():
                dist = (
                    (existing.center.x - center.x) ** 2
                    + (existing.center.y - center.y) ** 2
                ) ** 0.5
                if dist < 5:
                    if originating_village_id in self._state.villages:
                        self._state.villages[originating_village_id].has_expanded = True
                        try:
                            await self._persistence.queue_write(
                                "village",
                                originating_village_id,
                                self._state.villages[originating_village_id],
                            )
                        except Exception as exc:
                            logger.debug(
                                "Could not queue village write for originating village"
                                " (idempotency path): %s",
                                exc,
                            )
                    return existing

            # Mark originating village as expanded so this won't fire again.
            if originating_village_id in self._state.villages:
                self._state.villages[originating_village_id].has_expanded = True
                try:
                    await self._persistence.queue_write(
                        "village",
                        originating_village_id,
                        self._state.villages[originating_village_id],
                    )
                except Exception as exc:
                    logger.debug(
                        "Could not queue village write for originating village: %s", exc
                    )

            village_id = str(uuid.uuid4())
            now = datetime.now(UTC)
            village = Village(
                id=village_id,
                project_id=project_id,
                name=name,
                center=center,
                bounds=Bounds(center.x, center.y, center.x, center.y),
                created_at=now,
                updated_at=now,
            )

            self._state.villages[village_id] = village

            try:
                await self._persistence.queue_write("village", village_id, village)
            except Exception as exc:
                logger.debug("Could not queue village write for outpost: %s", exc)

            village_to_seed = village

        # Outside the lock: _seed_initial_structures calls create_structure which
        # acquires self._lock itself; calling it inside would cause a deadlock.
        if village_to_seed is not None:
            await self._seed_initial_structures(village_to_seed)

        return village_to_seed

    async def handle_event(self, event: InternalEvent) -> None:
        """Route an event by HookType and update world state accordingly.

        Dispatches on ``event.hook_type``:

        - **SessionStart**: ensures the project and session entities exist via
          ``get_or_create_project`` and ``get_or_create_session``.
        - **SessionEnd**: marks all agents belonging to the session as
          ``AgentState.IDLE``. Acquires self._lock for the state mutation.
        - **SubagentStart**: creates a new agent for the session via
          ``get_or_create_agent``.
        - **TaskCompleted**: awards 10 work units to a random structure type for
          an agent belonging to the session via ``add_work_units``.
        - All other hook types: records a summary string without mutating world
          state entities.

        In all cases the event is appended to the in-memory event log (capped at
        100 entries). Errors in per-hook handlers are caught and logged as
        warnings so that a single bad event never halts the pipeline.

        Acquires self._lock when writing to the event log.

        Args:
            event: The normalised internal event delivered by EventProcessor.
        """
        try:
            # All branches use enum identity (event.hook_type == HookType.X), not string comparison.
            # Do not change to hook_type.value == "..." — enum renames would silently fall through.

            # --- Compute summary and perform lock-free state mutations ---
            # Note: helpers like get_or_create_project/session/agent and
            # add_work_units all acquire self._lock internally, so they must
            # NOT be called while the lock is held below.

            if event.hook_type == HookType.Notification:
                ntype = event.notification_type or "generic"
                if ntype != "generic":
                    summary = f"Notification [type={ntype}]: {event.notification_message or ''}"
                else:
                    summary = f"Notification: {event.notification_message or ''}"

            elif event.hook_type == HookType.Stop:
                summary = f"Stop: {event.stop_reason or ''}"
                if event.stop_reason in ("tool", "stop", "end_turn"):
                    try:
                        session_id = event.session_id or ""
                        if session_id:
                            agent_ids_to_idle: list[str] = []
                            async with self._lock:
                                for a_id, a in self._state.agents.items():
                                    if a.session_id == session_id:
                                        agent_ids_to_idle.append(a_id)
                            for a_id in agent_ids_to_idle:
                                await self.update_agent(a_id, state=AgentState.IDLE)
                    except Exception as exc:
                        logger.warning("handle_event Stop: visual effect failed: %s", exc)

            elif event.hook_type == HookType.SessionStart:
                summary = f"SessionStart: {event.source or 'startup'}"
                try:
                    if event.project_id and event.session_id:
                        await self.get_or_create_project(
                            event.project_id, event.project_name or ""
                        )
                        await self.get_or_create_session(
                            event.session_id, event.project_id
                        )
                except Exception as exc:
                    logger.warning("handle_event SessionStart: visual effect failed: %s", exc)

            elif event.hook_type == HookType.SessionEnd:
                summary = f"SessionEnd: {event.reason or ''}"
                try:
                    session_id = event.session_id or ""
                    if session_id:
                        async with self._lock:
                            for agent in self._state.agents.values():
                                if agent.session_id == session_id:
                                    agent.state = AgentState.IDLE
                except Exception as exc:
                    logger.warning("handle_event SessionEnd: visual effect failed: %s", exc)

            elif event.hook_type == HookType.SubagentStart:
                summary = f"SubagentStart: {event.agent_type or 'unknown'}"
                try:
                    await self.get_or_create_agent(event.session_id or "")
                except Exception as exc:
                    logger.warning("handle_event SubagentStart: visual effect failed: %s", exc)

            elif event.hook_type == HookType.SubagentStop:
                summary = f"SubagentStop: {event.agent_type or 'unknown'}"

            elif event.hook_type == HookType.TeammateIdle:
                summary = f"TeammateIdle: {event.teammate_name or ''}"

            elif event.hook_type == HookType.TaskCompleted:
                summary = f"TaskCompleted: {event.task_subject or ''}"
                try:
                    session_id = event.session_id or ""
                    agent_id: str | None = None
                    async with self._lock:
                        for a_id, a in self._state.agents.items():
                            if a.session_id == session_id and a.village_id:
                                agent_id = a_id
                                break
                    if agent_id is not None:
                        structure_type = random.choice(list(StructureType))
                        await self.add_work_units(agent_id, structure_type, 10)
                    else:
                        logger.debug(
                            "handle_event TaskCompleted: no agent with valid village_id found for session %s",
                            session_id,
                        )
                except Exception as exc:
                    logger.warning("handle_event TaskCompleted: visual effect failed: %s", exc)

            elif event.hook_type == HookType.PostToolUseFailure:
                summary = f"PostToolUseFailure: {event.tool_name or ''}"

            elif event.hook_type == HookType.UserPromptSubmit:
                summary = "UserPromptSubmit"

            elif event.hook_type == HookType.PreCompact:
                summary = "PreCompact"

            elif event.hook_type == HookType.PostCompact:
                summary = "PostCompact"

            elif event.hook_type == HookType.StopFailure:
                summary = "StopFailure"

            else:
                summary = f"{event.hook_type.value}: {event.tool_name or ''}"

            async with self._lock:
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
