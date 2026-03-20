"""ViewportManager — tracks the visible region of the world and translates coordinates."""
from __future__ import annotations

import dataclasses
from typing import Any

from hamlet.viewport.coordinates import (
    BoundingBox,
    Position,
    Size,
    get_visible_bounds as _get_bounds,
    is_visible as _is_vis,
    screen_to_world as _s2w,
    world_to_screen as _w2s,
)
from hamlet.viewport.spatial_index import SpatialIndex
from hamlet.viewport.state import ViewportState

__all__ = ["ViewportManager"]


class ViewportManager:
    """Manages viewport state and provides coordinate translation services.

    Holds a reference to WorldStateManager for reading entity positions and
    maintains an internal SpatialIndex that is updated when entities move.
    """

    def __init__(self, world_state: Any) -> None:
        self._world_state = world_state
        self._state = ViewportState()
        self._spatial_index = SpatialIndex(cell_size=50)
        self._dirty_center = False

    async def initialize(self) -> None:
        """Set the viewport center and populate the spatial index.

        Restores viewport_center from world_metadata if available; otherwise
        defaults to the first village's center.
        """
        saved = self._world_state.get_viewport_center()
        if saved is not None:
            self._state.center = Position(saved[0], saved[1])
        else:
            villages = await self._world_state.get_all_villages()
            if villages:
                first_village = villages[0]
                self._state.center = Position(
                    first_village.center.x,
                    first_village.center.y,
                )

        # Populate spatial index with all current agents
        for agent in await self._world_state.get_all_agents():
            self.update_entity(agent.id, agent.position.x, agent.position.y)

        # Populate spatial index with all current structures
        for structure in await self._world_state.get_all_structures():
            self.update_entity(structure.id, structure.position.x, structure.position.y)

    def update_entity(self, entity_id: str, x: int, y: int) -> None:
        """Insert or update an entity's position in the spatial index."""
        self._spatial_index.update(entity_id, Position(x, y))

    def world_to_screen(self, world_pos: Position) -> Position:
        """Translate a world-space position to screen-space coordinates."""
        return _w2s(world_pos, self._state.center, self._state.size)

    def screen_to_world(self, screen_pos: Position) -> Position:
        """Translate a screen-space position to world-space coordinates."""
        return _s2w(screen_pos, self._state.center, self._state.size)

    def is_visible(self, world_pos: Position) -> bool:
        """Return True if world_pos is within the current visible viewport bounds."""
        bounds = _get_bounds(self._state.center, self._state.size)
        return _is_vis(world_pos, bounds)

    def get_visible_bounds(self) -> BoundingBox:
        """Return the world-space bounding box of the currently visible area."""
        return _get_bounds(self._state.center, self._state.size)

    def resize(self, width: int, height: int) -> None:
        """Update the viewport dimensions."""
        self._state.size = Size(width, height)

    def get_viewport_state(self) -> ViewportState:
        """Return a copy of the current viewport state snapshot."""
        return dataclasses.replace(
            self._state,
            center=dataclasses.replace(self._state.center),
            size=dataclasses.replace(self._state.size),
        )

    def scroll(self, delta_x: int, delta_y: int) -> None:
        """Scroll viewport by delta (switches to free mode)."""
        self._state.scroll(delta_x, delta_y)
        self._dirty_center = True

    def set_center(self, position: Position) -> None:
        """Set explicit viewport center (switches to free mode)."""
        self._state.set_center(position)
        self._dirty_center = True

    def auto_follow(self, agent_id: str) -> None:
        """Enable follow mode tracking the given agent."""
        self._state.set_follow_target(agent_id)

    async def update(self) -> None:
        """Update viewport center if in follow mode, then persist if center changed.

        If follow target no longer exists, revert to primary village center (free mode).
        """
        if self._state.follow_mode == "center" and self._state.follow_target is not None:
            all_agents = await self._world_state.get_all_agents()
            agents_by_id = {a.id: a for a in all_agents}
            agent = agents_by_id.get(self._state.follow_target)
            if agent is None:
                # Agent no longer exists — revert to village center (free mode)
                villages = await self._world_state.get_all_villages()
                if villages:
                    first_village = villages[0]
                    self._state.set_center(
                        Position(first_village.center.x, first_village.center.y)
                    )
                else:
                    self._state.set_center(self._state.center)  # clears follow_target
                self._dirty_center = True
            else:
                self._state.center = agent.position
                self._dirty_center = True

        if self._dirty_center:
            try:
                await self._world_state.update_viewport_center(
                    self._state.center.x, self._state.center.y
                )
                self._dirty_center = False
            except Exception:
                pass

    async def get_agents_in_view(self) -> list[str]:
        """Return IDs of agents whose position is within the current viewport bounds."""
        bounds = _get_bounds(self._state.center, self._state.size)
        candidates = self._spatial_index.query(bounds)
        all_agents = await self._world_state.get_all_agents()
        agent_ids = {a.id for a in all_agents}
        return [eid for eid in candidates if eid in agent_ids]

    async def get_structures_in_view(self) -> list[str]:
        """Return IDs of structures whose position is within the current viewport bounds."""
        bounds = _get_bounds(self._state.center, self._state.size)
        candidates = self._spatial_index.query(bounds)
        all_structures = await self._world_state.get_all_structures()
        structure_ids = {s.id for s in all_structures}
        return [eid for eid in candidates if eid in structure_ids]
