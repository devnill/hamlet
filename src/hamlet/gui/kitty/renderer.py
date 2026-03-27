"""Kitty graphics protocol renderer for hamlet.

Implements RendererProtocol using ANSI escape sequences for character
rendering and the Kitty graphics protocol for sprite blitting at
CLOSE/MEDIUM zoom levels.
"""

from __future__ import annotations

from typing import IO, TYPE_CHECKING, Sequence

from hamlet.gui.kitty.protocol import encode_delete_all, encode_image_display
from hamlet.gui.kitty.zoom import ZoomConfig, ZoomLevel, get_zoom_config
from hamlet.gui.symbol_config import SymbolConfig, default_config
from hamlet.viewport.coordinates import Position as VPosition
from hamlet.viewport.coordinates import world_to_screen
from hamlet.world_state.types import AgentState

if TYPE_CHECKING:
    from hamlet.gui.kitty.sprites import SpriteManager
    from hamlet.viewport.state import ViewportState
    from hamlet.world_state.types import Agent, Structure

_RICH_TO_RGB: dict[str, tuple[int, int, int]] = {
    "cyan": (0, 255, 255),
    "yellow": (255, 255, 0),
    "orange1": (255, 175, 0),
    "dark_green": (0, 100, 0),
    "magenta": (255, 0, 255),
    "blue": (0, 0, 255),
    "white": (255, 255, 255),
    "green": (0, 255, 0),
    "red": (255, 0, 0),
    "grey50": (128, 128, 128),
    "grey85": (217, 217, 217),
    "dark_orange": (255, 140, 0),
    "chartreuse": (127, 255, 0),
}

_SPINNER = ["|", "/", "-", "\\"]
_EVENT_LOG_ROWS = 5


class KittyRenderer:
    """Renderer that writes ANSI/Kitty escape sequences to an IO[str] stream.

    At FAR zoom, entities are rendered as characters with ANSI color escapes.
    At MEDIUM/CLOSE zoom, sprites are blitted via the Kitty graphics protocol
    when a SpriteManager is available and has uploaded sprites; otherwise
    falls back to character rendering.
    """

    def __init__(
        self,
        output: IO[str],
        cols: int,
        rows: int,
        symbol_config: SymbolConfig | None = None,
        sprite_manager: SpriteManager | None = None,
    ) -> None:
        self._output = output
        self._cols = cols
        self._rows = rows
        self._config = symbol_config or default_config()
        self._sprite_manager = sprite_manager
        self._zoom_level = ZoomLevel.FAR
        self._zoom_config: ZoomConfig = get_zoom_config(self._zoom_level)
        self._frame_counter = 0

    def set_zoom(self, level: ZoomLevel) -> None:
        """Set the current zoom level and update render mode accordingly."""
        self._zoom_level = level
        self._zoom_config = get_zoom_config(level)

    def render_frame(
        self,
        viewport_state: ViewportState,
        agents: Sequence[Agent],
        structures: Sequence[Structure],
        terrain_data: dict,
        event_log: list[str],
    ) -> None:
        """Render a single frame in layer order: clear, terrain, structures, agents, HUD."""
        buf: list[str] = []

        # Layer 0: clear
        buf.append("\x1b[2J")
        buf.append("\x1b[H")

        # Layer 1: terrain
        self._render_terrain(buf, viewport_state, terrain_data)

        # Layer 2: structures
        self._render_structures(buf, viewport_state, structures)

        # Layer 3: agents
        self._render_agents(buf, viewport_state, agents)

        # Layer 4: HUD
        self._render_hud(buf, event_log)

        self._output.write("".join(buf))
        self._output.flush()
        self._frame_counter += 1

    def cleanup(self) -> None:
        """Release terminal resources: delete all Kitty images and reset colors."""
        buf: list[str] = []
        buf.append(encode_delete_all())
        buf.append("\x1b[0m")
        self._output.write("".join(buf))
        self._output.flush()

    # ------------------------------------------------------------------
    # Private rendering helpers
    # ------------------------------------------------------------------

    def _to_screen(self, wx: int, wy: int, viewport_state: ViewportState) -> tuple[int, int]:
        """Convert world coords to 0-based screen coords."""
        vp_center = VPosition(x=viewport_state.center.x, y=viewport_state.center.y)
        vp_size = viewport_state.size
        screen = world_to_screen(VPosition(x=wx, y=wy), vp_center, vp_size)
        return screen.x, screen.y

    def _in_bounds(self, sx: int, sy: int) -> bool:
        """Check if 0-based screen coords are within the renderable area.

        Row 0 is reserved for the HUD status bar, and the bottom
        ``_EVENT_LOG_ROWS`` rows are reserved for the event log.
        """
        return 1 <= sy < (self._rows - _EVENT_LOG_ROWS) and 0 <= sx < self._cols

    def _move_cursor(self, sx: int, sy: int) -> str:
        """Return escape sequence to move cursor to 0-based screen position (converted to 1-based)."""
        return f"\x1b[{sy + 1};{sx + 1}H"

    def _fg_color(self, color_name: str) -> str:
        """Return ANSI escape for foreground RGB color from a Rich color name."""
        r, g, b = _RICH_TO_RGB.get(color_name, (255, 255, 255))
        return f"\x1b[38;2;{r};{g};{b}m"

    def _bg_color(self, color_name: str) -> str:
        """Return ANSI escape for background RGB color from a Rich color name."""
        r, g, b = _RICH_TO_RGB.get(color_name, (0, 0, 0))
        return f"\x1b[48;2;{r};{g};{b}m"

    def _render_terrain(
        self,
        buf: list[str],
        viewport_state: ViewportState,
        terrain_data: dict,
    ) -> None:
        """Render terrain layer. Iterates over terrain_data; empty dict is a no-op."""
        for pos_key, terrain_info in terrain_data.items():
            # terrain_data keys may be (x, y) tuples or Position objects
            if hasattr(pos_key, "x") and hasattr(pos_key, "y"):
                wx, wy = pos_key.x, pos_key.y
            elif isinstance(pos_key, tuple) and len(pos_key) == 2:
                wx, wy = pos_key
            else:
                continue

            sx, sy = self._to_screen(wx, wy, viewport_state)
            if not self._in_bounds(sx, sy):
                continue

            # Determine terrain type string
            if isinstance(terrain_info, str):
                terrain_type = terrain_info
            elif isinstance(terrain_info, dict):
                terrain_type = terrain_info.get("type", "plain")
            elif hasattr(terrain_info, "type"):
                terrain_type = terrain_info.type
            else:
                terrain_type = "plain"

            # Try sprite rendering at MEDIUM/CLOSE zoom
            if self._zoom_config.render_mode == "sprite" and self._sprite_manager is not None:
                handle = self._sprite_manager.get_terrain_sprite(
                    terrain_type, self._zoom_config.tile_pixels
                )
                if handle is not None and self._sprite_manager.is_uploaded(handle.image_id):
                    px = sx * self._zoom_config.tile_pixels
                    py = sy * self._zoom_config.tile_pixels
                    buf.append(encode_image_display(handle.image_id, px, py))
                    continue

            # Character rendering (FAR zoom or sprite fallback)
            symbol = self._config.terrain.symbols.get(terrain_type, ".")
            color = self._config.terrain.colors.get(terrain_type, "white")
            buf.append(self._move_cursor(sx, sy))
            buf.append(self._fg_color(color))
            buf.append(symbol)
            buf.append("\x1b[0m")

    def _render_structures(
        self,
        buf: list[str],
        viewport_state: ViewportState,
        structures: Sequence[Structure],
    ) -> None:
        """Render structure layer. Uses .get() for symbol lookup (Q-10 fix)."""
        for struct in structures:
            sx, sy = self._to_screen(struct.position.x, struct.position.y, viewport_state)
            if not self._in_bounds(sx, sy):
                continue

            # Try sprite rendering at MEDIUM/CLOSE zoom
            if self._zoom_config.render_mode == "sprite" and self._sprite_manager is not None:
                handle = self._sprite_manager.get_structure_sprite(
                    struct.type.value, struct.stage, self._zoom_config.tile_pixels
                )
                if handle is not None and self._sprite_manager.is_uploaded(handle.image_id):
                    px = sx * self._zoom_config.tile_pixels
                    py = sy * self._zoom_config.tile_pixels
                    buf.append(encode_image_display(handle.image_id, px, py))
                    continue

            # Character rendering — Q-10 fix: use .get() to avoid KeyError
            symbol = self._config.structure.symbols.get(struct.type, "?")
            material_color = self._config.structure.material_colors.get(struct.material, "white")
            buf.append(self._move_cursor(sx, sy))
            buf.append(self._fg_color(material_color))
            buf.append(symbol)
            buf.append("\x1b[0m")

    def _render_agents(
        self,
        buf: list[str],
        viewport_state: ViewportState,
        agents: Sequence[Agent],
    ) -> None:
        """Render agent layer. Zombie agents use zombie_color."""
        for agent in agents:
            sx, sy = self._to_screen(agent.position.x, agent.position.y, viewport_state)
            if not self._in_bounds(sx, sy):
                continue

            # Try sprite rendering at MEDIUM/CLOSE zoom
            if self._zoom_config.render_mode == "sprite" and self._sprite_manager is not None:
                handle = self._sprite_manager.get_agent_sprite(
                    agent.inferred_type.value, self._frame_counter % 4, self._zoom_config.tile_pixels
                )
                if handle is not None and self._sprite_manager.is_uploaded(handle.image_id):
                    px = sx * self._zoom_config.tile_pixels
                    py = sy * self._zoom_config.tile_pixels
                    buf.append(encode_image_display(handle.image_id, px, py))
                    continue

            # Character rendering
            symbol = self._config.agent.symbol
            if agent.state == AgentState.ZOMBIE:
                color_name = self._config.agent.zombie_color
            else:
                color_name = self._config.agent.colors.get(agent.inferred_type, "white")
            buf.append(self._move_cursor(sx, sy))
            buf.append(self._fg_color(color_name))
            buf.append(symbol)
            buf.append("\x1b[0m")

    def _render_hud(self, buf: list[str], event_log: list[str]) -> None:
        """Render HUD: status bar on row 0, event log on bottom 5 rows."""
        if self._rows < 2:
            return
        # Status bar on row 0
        spinner_char = _SPINNER[self._frame_counter % len(_SPINNER)]
        status_text = f" {spinner_char} hamlet "
        buf.append(self._move_cursor(0, 0))
        buf.append("\x1b[0m")
        buf.append(status_text)

        # Event log on bottom 5 rows
        log_rows = 5
        start_row = self._rows - log_rows
        if start_row < 1:
            start_row = 1

        # Take last N events
        visible_events = event_log[-(log_rows):]
        for i, event_text in enumerate(visible_events):
            row = start_row + i
            if row >= self._rows:
                break
            buf.append(self._move_cursor(0, row))
            buf.append("\x1b[0m")
            # Truncate to terminal width
            truncated = event_text[: self._cols]
            buf.append(truncated)


__all__ = ["KittyRenderer", "_RICH_TO_RGB"]
