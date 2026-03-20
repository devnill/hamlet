"""Spatial index for fast visibility queries in the Hamlet viewport."""
from __future__ import annotations

from .coordinates import BoundingBox, Position

__all__ = ["SpatialIndex"]


class SpatialIndex:
    """Cell-based spatial index for O(cells) visibility queries.

    The world is divided into square cells of `cell_size`. Each entity
    occupies exactly one cell based on its position. Querying a bounding
    box iterates only over the cells that intersect it.
    """

    def __init__(self, cell_size: int = 50) -> None:
        self._cell_size = cell_size
        self._cells: dict[tuple[int, int], set[str]] = {}  # cell_key -> entity IDs
        self._entity_cells: dict[str, tuple[int, int]] = {}  # entity_id -> cell_key

    def _get_cell(self, position: Position) -> tuple[int, int]:
        return (position.x // self._cell_size, position.y // self._cell_size)

    def update(self, entity_id: str, position: Position) -> None:
        """Insert or move an entity to the cell containing position."""
        new_cell = self._get_cell(position)
        old_cell = self._entity_cells.get(entity_id)

        if old_cell == new_cell:
            return  # No change needed

        # Remove from old cell; prune the key when the set becomes empty
        if old_cell is not None:
            cell_set = self._cells.get(old_cell)
            if cell_set is not None:
                cell_set.discard(entity_id)
                if not cell_set:
                    del self._cells[old_cell]

        # Add to new cell
        if new_cell not in self._cells:
            self._cells[new_cell] = set()
        self._cells[new_cell].add(entity_id)
        self._entity_cells[entity_id] = new_cell

    def remove(self, entity_id: str) -> None:
        """Remove an entity from the index."""
        cell = self._entity_cells.pop(entity_id, None)
        if cell is not None:
            cell_set = self._cells.get(cell)
            if cell_set is not None:
                cell_set.discard(entity_id)
                if not cell_set:
                    del self._cells[cell]

    def query(self, bounds: BoundingBox) -> list[str]:
        """Return all entity IDs whose cell intersects the bounding box."""
        min_cx = bounds.min_x // self._cell_size
        min_cy = bounds.min_y // self._cell_size
        max_cx = bounds.max_x // self._cell_size
        max_cy = bounds.max_y // self._cell_size

        result = []
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                entities = self._cells.get((cx, cy))
                if entities:
                    result.extend(entities)
        return result

    def clear(self) -> None:
        """Remove all entities from the index."""
        self._cells.clear()
        self._entity_cells.clear()
