"""MapViewer widget — terrain-only rendering for the map viewer mode."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rich.text import Text
from textual.events import Resize
from textual.widgets import Static
from textual.reactive import reactive

from hamlet.world_state.terrain import TerrainType
from hamlet.viewport.coordinates import BoundingBox, Size, Position, get_visible_bounds

if TYPE_CHECKING:
    from hamlet.world_state.terrain import TerrainGrid

_log = logging.getLogger(__name__)

__all__ = ["MapViewer", "ZOOM_LEVELS"]

# Valid zoom levels: 1x, 2x, 4x, 8x
ZOOM_LEVELS = [1, 2, 4, 8]


class MapViewer(Static):
    """Widget that renders terrain without agents or structures.

    Used in the map viewer mode for terrain exploration and parameter adjustment.

    Attributes:
        center_x: Reactive property for viewport center X coordinate.
        center_y: Reactive property for viewport center Y coordinate.
        zoom: Reactive property for current zoom level (1, 2, 4, or 8).
    """

    # Reactive properties for viewport management
    center_x: reactive[int] = reactive(0)
    center_y: reactive[int] = reactive(0)
    zoom: reactive[int] = reactive(1)

    def __init__(
        self,
        terrain_grid: "TerrainGrid",
        viewport_width: int = 80,
        viewport_height: int = 24,
    ) -> None:
        """Initialize the map viewer.

        Args:
            terrain_grid: TerrainGrid instance for on-demand terrain generation.
            viewport_width: Initial viewport width in characters.
            viewport_height: Initial viewport height in characters.
        """
        super().__init__()
        self._terrain_grid = terrain_grid
        self._viewport_width = viewport_width
        self._viewport_height = viewport_height

    def on_resize(self, event: Resize) -> None:
        """Update viewport dimensions when terminal is resized."""
        self._viewport_width = event.size.width
        self._viewport_height = event.size.height
        self.refresh()

    def get_visible_bounds(self) -> BoundingBox:
        """Return the world-space bounding box of the visible area.

        At higher zoom levels, fewer world cells are visible because each
        takes more screen cells.
        """
        viewport_size = Size(self._viewport_width, self._viewport_height)
        center = Position(self.center_x, self.center_y)
        return get_visible_bounds(center, viewport_size, self.zoom)

    def scroll(self, delta_x: int, delta_y: int) -> None:
        """Scroll the viewport by the given delta in world cells."""
        self.center_x += delta_x
        self.center_y += delta_y

    def set_center(self, x: int, y: int) -> None:
        """Set the viewport center to a specific position."""
        self.center_x = x
        self.center_y = y

    def zoom_in(self) -> None:
        """Increase zoom level (show fewer cells larger)."""
        current_index = ZOOM_LEVELS.index(self.zoom)
        if current_index < len(ZOOM_LEVELS) - 1:
            self.zoom = ZOOM_LEVELS[current_index + 1]
            self.refresh()

    def zoom_out(self) -> None:
        """Decrease zoom level (show more cells smaller)."""
        current_index = ZOOM_LEVELS.index(self.zoom)
        if current_index > 0:
            self.zoom = ZOOM_LEVELS[current_index - 1]
            self.refresh()

    def reset_zoom(self) -> None:
        """Reset zoom to default (1x)."""
        self.zoom = 1
        self.refresh()

    @property
    def zoom_level(self) -> int:
        """Return current zoom level."""
        return self.zoom

    def render(self) -> Text:
        """Render the terrain grid without agents or structures.

        At zoom > 1, each world cell is rendered as multiple screen cells.
        For example, at zoom=2, each world cell becomes a 2x2 block of the same character.
        """
        # Sync viewport to widget's actual allocated size
        w, h = self.size.width, self.size.height
        if w > 0 and h > 0:
            self._viewport_width = w
            self._viewport_height = h

        bounds = self.get_visible_bounds()
        zoom = self.zoom

        # Get terrain for visible bounds
        terrain_map = self._terrain_grid.get_terrain_in_bounds(bounds)

        # Build terrain lookup
        terrain_by_pos: dict[tuple[int, int], tuple[str, str]] = {}
        for pos, terrain in terrain_map.items():
            try:
                if hasattr(pos, "x"):
                    key = (pos.x, pos.y)
                else:
                    key = tuple(pos)

                if isinstance(terrain, TerrainType):
                    terrain_type = terrain
                else:
                    terrain_type = TerrainType(terrain)

                terrain_by_pos[key] = (
                    terrain_type.symbol,
                    terrain_type.color,
                )
            except (ValueError, AttributeError):
                pass

        # Render terrain with zoom scaling
        text = Text()
        for world_y in range(bounds.min_y, bounds.max_y + 1):
            # For each world row, we render 'zoom' screen rows
            for row_repeat in range(zoom):
                for world_x in range(bounds.min_x, bounds.max_x + 1):
                    key = (world_x, world_y)
                    if key in terrain_by_pos:
                        symbol, color = terrain_by_pos[key]
                    else:
                        symbol, color = ".", "dim white"

                    # For each world column, we render 'zoom' screen columns
                    for col_repeat in range(zoom):
                        text.append(symbol, style=color)
                text.append("\n")

        return text