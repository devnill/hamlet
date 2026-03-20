"""Coordinate types and translation utilities for the hamlet viewport.

World coordinates use a global origin at (0, 0) placed at the first village
center. X increases east (right), Y increases south (down).

Screen coordinates are viewport-relative: top-left is (0, 0).
"""

from dataclasses import dataclass


@dataclass
class Position:
    """A point in either world or screen coordinate space."""

    x: int
    y: int

    def __post_init__(self) -> None:
        self.x = int(self.x)
        self.y = int(self.y)


@dataclass
class Size:
    """Dimensions of a rectangular area."""

    width: int
    height: int

    def __post_init__(self) -> None:
        self.width = int(self.width)
        self.height = int(self.height)


@dataclass
class BoundingBox:
    """An axis-aligned bounding box defined by its minimum and maximum corners."""

    min_x: int
    min_y: int
    max_x: int
    max_y: int

    def __post_init__(self) -> None:
        self.min_x = int(self.min_x)
        self.min_y = int(self.min_y)
        self.max_x = int(self.max_x)
        self.max_y = int(self.max_y)


def world_to_screen(
    world_pos: Position,
    viewport_center: Position,
    viewport_size: Size,
) -> Position:
    """Translate a world-space position to screen-space coordinates.

    Formula:
        screen_x = world_x - center_x + width // 2
        screen_y = world_y - center_y + height // 2
    """
    screen_x = world_pos.x - viewport_center.x + viewport_size.width // 2
    screen_y = world_pos.y - viewport_center.y + viewport_size.height // 2
    return Position(x=screen_x, y=screen_y)


def screen_to_world(
    screen_pos: Position,
    viewport_center: Position,
    viewport_size: Size,
) -> Position:
    """Translate a screen-space position to world-space coordinates.

    Formula:
        world_x = screen_x + center_x - width // 2
        world_y = screen_y + center_y - height // 2
    """
    world_x = screen_pos.x + viewport_center.x - viewport_size.width // 2
    world_y = screen_pos.y + viewport_center.y - viewport_size.height // 2
    return Position(x=world_x, y=world_y)


def is_visible(world_pos: Position, viewport_bounds: BoundingBox) -> bool:
    """Return True if world_pos falls within the given viewport bounds (inclusive)."""
    return (
        viewport_bounds.min_x <= world_pos.x <= viewport_bounds.max_x
        and viewport_bounds.min_y <= world_pos.y <= viewport_bounds.max_y
    )


def get_visible_bounds(
    viewport_center: Position,
    viewport_size: Size,
) -> BoundingBox:
    """Return the world-space bounding box of the visible viewport area.

    Consistent with world_to_screen: the max bounds are adjusted so that
    every position in the bounding box maps to a valid screen coordinate
    (0 to width-1, 0 to height-1).
    """
    half_w = viewport_size.width // 2
    half_h = viewport_size.height // 2
    return BoundingBox(
        min_x=viewport_center.x - half_w,
        min_y=viewport_center.y - half_h,
        max_x=viewport_center.x + half_w - 1 + (viewport_size.width % 2),
        max_y=viewport_center.y + half_h - 1 + (viewport_size.height % 2),
    )
