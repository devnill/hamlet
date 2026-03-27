"""Tests for viewport coordinate utilities (work item 085).

Run with: pytest tests/test_viewport_coordinates.py -v
"""
from __future__ import annotations

import pytest

from hamlet.viewport.coordinates import (
    BoundingBox,
    Position,
    Size,
    get_visible_bounds,
    is_visible,
    screen_to_world,
    world_to_screen,
)


class TestCoordinates:
    """Test suite for coordinate types and translation utilities."""

    def test_position_creation(self) -> None:
        """Test Position dataclass creation with float values."""
        pos = Position(x=10.7, y=20.3)
        assert pos.x == 10  # Truncated to int (int() truncates toward zero)
        assert pos.y == 20

    def test_position_creation_with_ints(self) -> None:
        """Test Position dataclass creation with int values."""
        pos = Position(x=10, y=20)
        assert pos.x == 10
        assert pos.y == 20

    def test_size_creation(self) -> None:
        """Test Size dataclass creation."""
        size = Size(width=80.5, height=24.7)
        assert size.width == 80
        assert size.height == 24

    def test_bounding_box_creation(self) -> None:
        """Test BoundingBox dataclass creation."""
        box = BoundingBox(min_x=0.5, min_y=1.5, max_x=100.7, max_y=200.3)
        assert box.min_x == 0
        assert box.min_y == 1
        assert box.max_x == 100
        assert box.max_y == 200

    def test_world_to_screen_formula(self) -> None:
        """Test world-to-screen coordinate translation formula."""
        viewport_center = Position(50, 50)
        viewport_size = Size(80, 24)

        # Test various world positions
        # Formula: screen_x = world_x - center_x + width // 2
        # Formula: screen_y = world_y - center_y + height // 2

        # World position at center should map to screen center
        screen = world_to_screen(Position(50, 50), viewport_center, viewport_size)
        assert screen.x == 40  # 50 - 50 + 40
        assert screen.y == 12  # 50 - 50 + 12

        # World position at origin
        screen = world_to_screen(Position(0, 0), viewport_center, viewport_size)
        assert screen.x == -10  # 0 - 50 + 40
        assert screen.y == -38  # 0 - 50 + 12

        # World position at (100, 100)
        screen = world_to_screen(Position(100, 100), viewport_center, viewport_size)
        assert screen.x == 90  # 100 - 50 + 40
        assert screen.y == 62  # 100 - 50 + 12

    def test_screen_to_world_formula(self) -> None:
        """Test screen-to-world coordinate translation formula."""
        viewport_center = Position(50, 50)
        viewport_size = Size(80, 24)

        # Formula: world_x = screen_x + center_x - width // 2
        # Formula: world_y = screen_y + center_y - height // 2

        # Screen center should map to world center
        world = screen_to_world(Position(40, 12), viewport_center, viewport_size)
        assert world.x == 50  # 40 + 50 - 40
        assert world.y == 50  # 12 + 50 - 12

        # Screen origin
        world = screen_to_world(Position(0, 0), viewport_center, viewport_size)
        assert world.x == 10  # 0 + 50 - 40
        assert world.y == 38  # 0 + 50 - 12

    def test_is_visible_inclusive_bounds(self) -> None:
        """Test is_visible with inclusive bounds."""
        bounds = BoundingBox(0, 0, 100, 100)

        # Point inside bounds
        assert is_visible(Position(50, 50), bounds) is True

        # Point on boundary (inclusive)
        assert is_visible(Position(0, 50), bounds) is True
        assert is_visible(Position(100, 50), bounds) is True
        assert is_visible(Position(50, 0), bounds) is True
        assert is_visible(Position(50, 100), bounds) is True

        # Corner points (inclusive)
        assert is_visible(Position(0, 0), bounds) is True
        assert is_visible(Position(100, 100), bounds) is True

        # Point outside bounds
        assert is_visible(Position(-1, 50), bounds) is False
        assert is_visible(Position(101, 50), bounds) is False
        assert is_visible(Position(50, -1), bounds) is False
        assert is_visible(Position(50, 101), bounds) is False

    def test_get_visible_bounds(self) -> None:
        """Test get_visible_bounds calculation."""
        viewport_center = Position(50, 50)
        viewport_size = Size(80, 24)

        bounds = get_visible_bounds(viewport_center, viewport_size)

        # For even dimensions: half_w = 40, half_h = 12
        # min_x = 50 - 40 = 10
        # min_y = 50 - 12 = 38
        # max_x = 50 + 40 - 1 = 89
        # max_y = 50 + 12 - 1 = 61
        assert bounds.min_x == 10
        assert bounds.min_y == 38
        assert bounds.max_x == 89
        assert bounds.max_y == 61

    def test_get_visible_bounds_odd_dimensions(self) -> None:
        """Test get_visible_bounds with odd dimensions."""
        viewport_center = Position(50, 50)
        viewport_size = Size(81, 25)

        bounds = get_visible_bounds(viewport_center, viewport_size)

        # For odd dimensions: half_w = 40, half_h = 12
        # width % 2 = 1, height % 2 = 1
        # min_x = 50 - 40 = 10
        # min_y = 50 - 12 = 38
        # max_x = 50 + 40 - 1 + 1 = 90
        # max_y = 50 + 12 - 1 + 1 = 62
        assert bounds.min_x == 10
        assert bounds.min_y == 38
        assert bounds.max_x == 90
        assert bounds.max_y == 62

    def test_world_to_screen_with_zoom(self) -> None:
        """Test world-to-screen coordinate translation with zoom."""
        viewport_center = Position(50, 50)
        viewport_size = Size(80, 24)

        # At 1x zoom, center should map to screen center
        screen = world_to_screen(Position(50, 50), viewport_center, viewport_size, zoom=1)
        assert screen.x == 40
        assert screen.y == 12

        # At 2x zoom, each world cell is 2 screen cells
        # World position (50, 50) should still map to screen center
        screen = world_to_screen(Position(50, 50), viewport_center, viewport_size, zoom=2)
        assert screen.x == 40
        assert screen.y == 12

        # At 2x zoom, world position (51, 51) should be 2 screen cells away from center
        screen = world_to_screen(Position(51, 51), viewport_center, viewport_size, zoom=2)
        assert screen.x == 42  # (51 - 50) * 2 + 40
        assert screen.y == 14  # (51 - 50) * 2 + 12

        # At 4x zoom, world position (52, 52) should be 8 screen cells from center
        screen = world_to_screen(Position(52, 52), viewport_center, viewport_size, zoom=4)
        assert screen.x == 48  # (52 - 50) * 4 + 40
        assert screen.y == 20  # (52 - 50) * 4 + 12

    def test_screen_to_world_with_zoom(self) -> None:
        """Test screen-to-world coordinate translation with zoom."""
        viewport_center = Position(50, 50)
        viewport_size = Size(80, 24)

        # At 1x zoom, screen center should map to world center
        world = screen_to_world(Position(40, 12), viewport_center, viewport_size, zoom=1)
        assert world.x == 50
        assert world.y == 50

        # At 2x zoom, screen center still maps to world center
        world = screen_to_world(Position(40, 12), viewport_center, viewport_size, zoom=2)
        assert world.x == 50
        assert world.y == 50

        # At 2x zoom, screen position (42, 14) should map to world (51, 51)
        world = screen_to_world(Position(42, 14), viewport_center, viewport_size, zoom=2)
        assert world.x == 51  # (42 - 40) // 2 + 50
        assert world.y == 51  # (14 - 12) // 2 + 50

        # At 4x zoom, screen position (48, 20) should map to world (52, 52)
        world = screen_to_world(Position(48, 20), viewport_center, viewport_size, zoom=4)
        assert world.x == 52  # (48 - 40) // 4 + 50
        assert world.y == 52  # (20 - 12) // 4 + 50

    def test_get_visible_bounds_with_zoom(self) -> None:
        """Test get_visible_bounds with zoom factor."""
        viewport_center = Position(50, 50)
        viewport_size = Size(80, 24)

        # At 1x zoom
        bounds_1x = get_visible_bounds(viewport_center, viewport_size, zoom=1)

        # At 2x zoom, we should see fewer world cells
        bounds_2x = get_visible_bounds(viewport_center, viewport_size, zoom=2)

        # The visible range should be roughly half at 2x zoom
        width_1x = bounds_1x.max_x - bounds_1x.min_x + 1
        width_2x = bounds_2x.max_x - bounds_2x.min_x + 1
        assert width_2x <= width_1x // 2 + 1

        # At 4x zoom, even fewer cells visible
        bounds_4x = get_visible_bounds(viewport_center, viewport_size, zoom=4)
        width_4x = bounds_4x.max_x - bounds_4x.min_x + 1
        assert width_4x <= width_2x // 2 + 1
