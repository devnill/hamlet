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
