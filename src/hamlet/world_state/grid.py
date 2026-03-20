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
