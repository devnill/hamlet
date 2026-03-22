"""WorldView Textual widget for rendering the Hamlet world."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual.events import Resize
from textual.widgets import Static

from hamlet.tui.symbols import (
    AGENT_SYMBOL, get_agent_color, get_structure_symbol, get_structure_color,
)
from hamlet.world_state.types import AgentState

if TYPE_CHECKING:
    from hamlet.viewport.coordinates import BoundingBox

_log = logging.getLogger(__name__)

SPIN_SYMBOLS = ["-", "\\", "|", "/"]
__all__ = ["WorldView"]


class WorldView(Static):
    """Main world rendering widget displaying agents and structures."""

    def __init__(self, world_state: Any, viewport: Any) -> None:
        super().__init__()
        self._world_state = world_state
        self._viewport = viewport
        self._agents: list[Any] = []
        self._structures: list[Any] = []
        self._spin_frame: int = 0

    def on_mount(self) -> None:
        """Set up 4Hz animation frame updates and 30FPS render refresh."""
        self.set_interval(1 / 4, self._update_animation_frame)
        # on_resize fires after the layout pass with the correct terminal size.

    def on_resize(self, event: Resize) -> None:
        """Update viewport dimensions when terminal is resized."""
        self._viewport.resize(event.size.width, event.size.height)

    async def _update_animation_frame(self) -> None:
        """Advance spin animation frame and refresh state from world."""
        self._spin_frame = (self._spin_frame + 1) % 4
        try:
            bounds = self._viewport.get_visible_bounds()
            self._agents = await self._world_state.get_agents_in_view(bounds)
            self._structures = await self._world_state.get_structures_in_view(bounds)
        except Exception as exc:
            _log.warning("state update failed: %s", exc)
            self._agents = []
            self._structures = []
        self.refresh()

    def render(self) -> Text:
        """Render the world view using cached agent/structure state."""
        # Sync viewport to widget's actual allocated size on every render.
        # on_resize may fire before layout is complete; reading self.size here
        # ensures the viewport is always correct without waiting for a user resize.
        w, h = self.size.width, self.size.height
        if w > 0 and h > 0:
            self._viewport.resize(w, h)

        try:
            bounds = self._viewport.get_visible_bounds()
        except Exception:
            return Text("Loading...")

        # Build position lookups
        agent_by_pos: dict[tuple[int, int], Any] = {}
        for agent in self._agents:
            pos = agent.position
            agent_by_pos[(pos.x, pos.y)] = agent

        struct_by_pos: dict[tuple[int, int], tuple[str, str]] = {}
        for structure in self._structures:
            pos = structure.position
            tier = getattr(structure, "size_tier", 1)
            symbol = get_structure_symbol(structure)
            color = get_structure_color(structure)
            if tier <= 1:
                struct_by_pos[(pos.x, pos.y)] = (symbol, color)
            else:
                half = tier - 1
                for dx in range(-half, half + 1):
                    for dy in range(-half, half + 1):
                        cx, cy = pos.x + dx, pos.y + dy
                        is_top = dy == -half
                        is_bottom = dy == half
                        is_left = dx == -half
                        is_right = dx == half
                        is_corner = (is_top or is_bottom) and (is_left or is_right)
                        is_h_edge = (is_top or is_bottom) and not is_corner
                        is_v_edge = (is_left or is_right) and not is_corner
                        if is_corner:
                            char: str = "+"
                        elif is_h_edge:
                            char = "-"
                        elif is_v_edge:
                            char = "|"
                        else:
                            char = symbol
                        struct_by_pos[(cx, cy)] = (char, color)

        text = Text()
        for y in range(bounds.min_y, bounds.max_y + 1):
            for x in range(bounds.min_x, bounds.max_x + 1):
                key = (x, y)
                if key in agent_by_pos:
                    agent = agent_by_pos[key]
                    color = get_agent_color(agent)
                    # Active agents spin, idle/zombie show @
                    if agent.state == AgentState.ACTIVE:
                        symbol = SPIN_SYMBOLS[self._spin_frame]
                    else:
                        symbol = AGENT_SYMBOL
                    text.append(symbol, style=color)
                elif key in struct_by_pos:
                    char, style = struct_by_pos[key]
                    text.append(char, style=style)
                else:
                    text.append(".", style="dim white")
            text.append("\n")
        return text
