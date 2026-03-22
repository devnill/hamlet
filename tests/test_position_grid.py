"""Tests for PositionGrid spatial tracking (work item 088).

Run with: pytest tests/test_position_grid.py -v
"""
from __future__ import annotations

import pytest

from hamlet.world_state.grid import PositionGrid
from hamlet.world_state.types import Position


class TestPositionGrid:
    """Test suite for PositionGrid occupancy operations."""

    def test_occupy_stores_entity(self) -> None:
        """occupy() stores entity_id at the given position."""
        grid = PositionGrid()
        pos = Position(10, 10)

        grid.occupy(pos, "agent1")

        assert grid.is_occupied(pos)
        assert grid.get_entity_at(pos) == "agent1"

    def test_vacate_removes_entity(self) -> None:
        """vacate() removes the entity at the given position."""
        grid = PositionGrid()
        pos = Position(5, 5)
        grid.occupy(pos, "agent2")

        grid.vacate(pos)

        assert not grid.is_occupied(pos)
        assert grid.get_entity_at(pos) is None

    def test_is_occupied_returns_boolean(self) -> None:
        """is_occupied() returns True if position has entity, False otherwise."""
        grid = PositionGrid()
        occupied_pos = Position(1, 1)
        unoccupied_pos = Position(2, 2)
        grid.occupy(occupied_pos, "agent3")

        assert grid.is_occupied(occupied_pos) is True
        assert grid.is_occupied(unoccupied_pos) is False

    def test_occupy_raises_on_duplicate(self) -> None:
        """occupy() raises ValueError when position is already occupied."""
        grid = PositionGrid()
        pos = Position(3, 3)
        grid.occupy(pos, "first_agent")

        with pytest.raises(ValueError) as exc_info:
            grid.occupy(pos, "second_agent")

        assert "already occupied by 'first_agent'" in str(exc_info.value)

    def test_vacate_is_idempotent(self) -> None:
        """vacate() does nothing when position is not occupied."""
        grid = PositionGrid()
        pos = Position(7, 7)

        # Should not raise
        grid.vacate(pos)

        assert not grid.is_occupied(pos)

    def test_get_entity_at_returns_none_for_empty(self) -> None:
        """get_entity_at() returns None for unoccupied positions."""
        grid = PositionGrid()
        pos = Position(0, 0)

        result = grid.get_entity_at(pos)

        assert result is None

    def test_get_occupied_positions_returns_snapshot(self) -> None:
        """get_occupied_positions() returns a copy of occupied positions."""
        grid = PositionGrid()
        pos1 = Position(1, 1)
        pos2 = Position(2, 2)
        grid.occupy(pos1, "agent_a")
        grid.occupy(pos2, "agent_b")

        occupied = grid.get_occupied_positions()

        assert occupied == {pos1, pos2}
        # Verify it's a copy - modifying it doesn't affect grid
        occupied.add(Position(99, 99))
        assert not grid.is_occupied(Position(99, 99))

    def test_occupy_footprint_tier2_marks_all_cells(self) -> None:
        """occupy_footprint() tier 2 at (5,5) marks all 9 cells in 3x3 footprint."""
        grid = PositionGrid()
        center = Position(5, 5)

        grid.occupy_footprint(center, tier=2, entity_id="struct1")

        # All cells in (4,4)-(6,6) must be occupied by struct1
        for x in range(4, 7):
            for y in range(4, 7):
                assert grid.is_occupied(Position(x, y)), f"Expected {(x, y)} to be occupied"
                assert grid.get_entity_at(Position(x, y)) == "struct1"

    def test_vacate_footprint_clears_cells(self) -> None:
        """vacate_footprint() clears all cells occupied by the given entity."""
        grid = PositionGrid()
        center = Position(5, 5)
        grid.occupy_footprint(center, tier=2, entity_id="struct1")

        grid.vacate_footprint(center, tier=2, entity_id="struct1")

        for x in range(4, 7):
            for y in range(4, 7):
                assert not grid.is_occupied(Position(x, y)), f"Expected {(x, y)} to be free"

    def test_occupy_footprint_raises_on_conflict(self) -> None:
        """occupy_footprint() raises ValueError if a cell is occupied by a different entity."""
        grid = PositionGrid()
        grid.occupy(Position(5, 5), "other_entity")

        with pytest.raises(ValueError) as exc_info:
            grid.occupy_footprint(Position(5, 5), tier=2, entity_id="struct1")

        assert "already occupied by 'other_entity'" in str(exc_info.value)

    def test_occupy_footprint_tier1_marks_single_cell(self) -> None:
        """occupy_footprint() tier 1 marks only the center cell."""
        grid = PositionGrid()
        center = Position(3, 3)

        grid.occupy_footprint(center, tier=1, entity_id="struct_tiny")

        assert grid.is_occupied(center)
        assert grid.get_entity_at(center) == "struct_tiny"
        # Adjacent cells should not be occupied
        for pos in [Position(2, 3), Position(4, 3), Position(3, 2), Position(3, 4)]:
            assert not grid.is_occupied(pos)

    def test_vacate_footprint_only_removes_own_cells(self) -> None:
        """vacate_footprint() does not remove cells occupied by other entities."""
        grid = PositionGrid()
        center = Position(5, 5)
        grid.occupy_footprint(center, tier=2, entity_id="struct1")
        # Overwrite one cell with a different entity directly
        grid._grid[Position(4, 4)] = "other"

        grid.vacate_footprint(center, tier=2, entity_id="struct1")

        # The cell owned by 'other' must remain
        assert grid.get_entity_at(Position(4, 4)) == "other"
        # All other struct1 cells must be cleared
        for x in range(4, 7):
            for y in range(4, 7):
                if (x, y) != (4, 4):
                    assert not grid.is_occupied(Position(x, y))
