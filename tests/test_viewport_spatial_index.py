"""Tests for SpatialIndex (work item 085).

Run with: pytest tests/test_viewport_spatial_index.py -v
"""
from __future__ import annotations

import pytest

from hamlet.viewport.coordinates import BoundingBox, Position
from hamlet.viewport.spatial_index import SpatialIndex


class TestSpatialIndex:
    """Test suite for SpatialIndex."""

    def test_update_adds_entity(self) -> None:
        """Test that update adds entity to the spatial index."""
        index = SpatialIndex(cell_size=10)

        # Add an entity
        index.update("agent1", Position(5, 5))

        # Verify entity is tracked
        assert "agent1" in index._entity_cells
        # Cell is (0, 0) for position (5, 5) with cell_size 10
        assert index._entity_cells["agent1"] == (0, 0)
        # Entity is in the cell
        assert "agent1" in index._cells[(0, 0)]

    def test_update_adds_entity_to_correct_cell(self) -> None:
        """Test that update places entity in correct cell based on position."""
        index = SpatialIndex(cell_size=10)

        # Add entities at different positions
        index.update("agent1", Position(5, 5))    # Cell (0, 0)
        index.update("agent2", Position(15, 25))  # Cell (1, 2)
        index.update("agent3", Position(-5, -5))  # Cell (-1, -1)

        assert index._entity_cells["agent1"] == (0, 0)
        assert index._entity_cells["agent2"] == (1, 2)
        assert index._entity_cells["agent3"] == (-1, -1)

    def test_update_moves_entity_between_cells(self) -> None:
        """Test that update moves entity when position changes."""
        index = SpatialIndex(cell_size=10)

        # Add entity to initial position
        index.update("agent1", Position(5, 5))
        assert index._entity_cells["agent1"] == (0, 0)
        assert "agent1" in index._cells[(0, 0)]

        # Move entity to new position
        index.update("agent1", Position(15, 15))
        assert index._entity_cells["agent1"] == (1, 1)
        assert "agent1" in index._cells[(1, 1)]
        assert "agent1" not in index._cells.get((0, 0), set())

    def test_update_no_change_same_cell(self) -> None:
        """Test that update does nothing when entity stays in same cell."""
        index = SpatialIndex(cell_size=10)

        # Add entity
        index.update("agent1", Position(5, 5))

        # Update with position in same cell
        index.update("agent1", Position(9, 9))

        # Still in same cell
        assert index._entity_cells["agent1"] == (0, 0)

    def test_remove_entity(self) -> None:
        """Test removing an entity from the index."""
        index = SpatialIndex(cell_size=10)

        # Add and then remove entity
        index.update("agent1", Position(5, 5))
        index.remove("agent1")

        # Verify entity is removed
        assert "agent1" not in index._entity_cells
        assert "agent1" not in index._cells.get((0, 0), set())

    def test_remove_nonexistent_entity(self) -> None:
        """Test removing an entity that doesn't exist."""
        index = SpatialIndex(cell_size=10)

        # Should not raise
        index.remove("nonexistent")

    def test_query_returns_entities_in_bounds(self) -> None:
        """Test that query returns entities within bounds."""
        index = SpatialIndex(cell_size=10)

        # Add entities at different positions
        index.update("agent1", Position(5, 5))      # Cell (0, 0)
        index.update("agent2", Position(15, 15))    # Cell (1, 1)
        index.update("agent3", Position(100, 100))  # Cell (10, 10)

        # Query bounds that include agent1 and agent2
        bounds = BoundingBox(0, 0, 20, 20)
        results = index.query(bounds)

        assert "agent1" in results
        assert "agent2" in results
        assert "agent3" not in results

    def test_query_returns_entities_in_cell_intersection(self) -> None:
        """Test that query returns entities in cells intersecting bounds."""
        index = SpatialIndex(cell_size=10)

        # Add entities
        index.update("agent1", Position(5, 5))    # Cell (0, 0)
        index.update("agent2", Position(15, 5))   # Cell (1, 0)
        index.update("agent3", Position(25, 5))   # Cell (2, 0)

        # Query bounds that intersect cells (0, 0) and (1, 0)
        bounds = BoundingBox(0, 0, 15, 10)
        results = index.query(bounds)

        assert "agent1" in results
        assert "agent2" in results
        assert "agent3" not in results

    def test_query_empty_bounds(self) -> None:
        """Test query with bounds that include no cells."""
        index = SpatialIndex(cell_size=10)

        # Add entity
        index.update("agent1", Position(5, 5))

        # Query bounds outside entity
        bounds = BoundingBox(100, 100, 200, 200)
        results = index.query(bounds)

        assert results == []

    def test_clear_removes_all_entities(self) -> None:
        """Test that clear removes all entities from the index."""
        index = SpatialIndex(cell_size=10)

        # Add multiple entities
        index.update("agent1", Position(5, 5))
        index.update("agent2", Position(15, 15))
        index.update("agent3", Position(25, 25))

        # Clear the index
        index.clear()

        # Verify all entities are removed
        assert index._entity_cells == {}
        assert index._cells == {}

    def test_prunes_empty_cells(self) -> None:
        """Test that empty cells are pruned when entities move."""
        index = SpatialIndex(cell_size=10)

        # Add entity
        index.update("agent1", Position(5, 5))
        assert (0, 0) in index._cells

        # Move entity to different cell
        index.update("agent1", Position(15, 15))

        # Old cell should be removed
        assert (0, 0) not in index._cells
        assert (1, 1) in index._cells
