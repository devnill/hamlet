from __future__ import annotations

"""In-memory position grid index mapping world coordinates to entity IDs."""

from .types import Position

__all__ = ["PositionGrid"]


class PositionGrid:
    """Tracks which entity occupies each position in the world grid.

    Internal storage is a plain dict mapping Position to entity_id string.
    No persistence — in-memory only.
    """

    def __init__(self) -> None:
        self._grid: dict[Position, str] = {}

    def occupy(self, position: Position, entity_id: str) -> None:
        """Store entity_id at position.

        Raises ValueError if position is already occupied.
        """
        if position in self._grid:
            raise ValueError(
                f"Position {position} is already occupied by '{self._grid[position]}'"
            )
        self._grid[position] = entity_id

    def vacate(self, position: Position) -> None:
        """Remove the entity at position.

        Does nothing if position is not occupied (idempotent).
        """
        self._grid.pop(position, None)

    def is_occupied(self, position: Position) -> bool:
        """Return True if an entity occupies position."""
        return position in self._grid

    def get_entity_at(self, position: Position) -> str | None:
        """Return the entity_id at position, or None if unoccupied."""
        return self._grid.get(position)

    def get_occupied_positions(self) -> set[Position]:
        """Return a snapshot copy of all currently occupied positions."""
        return set(self._grid.keys())

    def footprint_positions(self, center: "Position", tier: int) -> list["Position"]:
        """Return all positions in (2*tier-1) x (2*tier-1) footprint centered on center."""
        half = tier - 1
        return [
            Position(center.x + dx, center.y + dy)
            for dx in range(-half, half + 1)
            for dy in range(-half, half + 1)
        ]

    # Keep private alias for internal callers within this module
    _footprint_positions = footprint_positions

    def occupy_footprint(self, position: "Position", tier: int, entity_id: str) -> None:
        """Mark all cells in the tier footprint as occupied by entity_id."""
        for pos in self.footprint_positions(position, tier):
            occupied_by = self._grid.get(pos)
            if occupied_by is not None and occupied_by != entity_id:
                raise ValueError(f"Position {pos} already occupied by '{occupied_by}'")
            self._grid[pos] = entity_id

    def vacate_footprint(self, position: "Position", tier: int, entity_id: str) -> None:
        """Clear all footprint cells that are occupied by entity_id."""
        for pos in self.footprint_positions(position, tier):
            if self._grid.get(pos) == entity_id:
                del self._grid[pos]
