"""Kitty graphics viewer application for hamlet.

Manages the terminal lifecycle (alternate screen, raw mode), input handling,
state fetching, and render loop at 30 FPS.
"""

from __future__ import annotations

import os
import select
import sys
import termios
import time
import tty

from hamlet.gui.kitty.renderer import KittyRenderer
from hamlet.gui.kitty.sprites import SpriteManager
from hamlet.gui.kitty.state_fetcher import StateFetcher, StateSnapshot
from hamlet.gui.kitty.zoom import ZoomLevel, next_zoom, prev_zoom
from hamlet.gui.symbol_config import default_config
from hamlet.viewport.coordinates import Position, Size
from hamlet.viewport.state import ViewportState

_FRAME_DURATION = 1.0 / 30.0
_FETCH_INTERVAL = 1.0

_TERRAIN_TYPES = ["plain", "water", "mountain", "forest", "meadow"]
_STRUCTURE_TYPES = ["house", "workshop", "library", "forge", "tower", "road", "well"]
_AGENT_TYPES = [
    "general", "researcher", "coder", "planner",
    "executor", "architect", "tester",
]


def _upload_sprites(mgr: SpriteManager) -> str:
    """Load all sprites and return concatenated Kitty upload sequences.

    Missing sprite files are silently skipped — the renderer falls back
    to character rendering for any sprite it cannot find.
    """
    sequences: list[str] = []
    for size in (16, 8):
        for name in _TERRAIN_TYPES:
            h = mgr.get_terrain_sprite(name, size)
            if h and not mgr.is_uploaded(h.image_id):
                sequences.append(mgr.get_upload_sequence(h))
        for name in _STRUCTURE_TYPES:
            h = mgr.get_structure_sprite(name, 0, size)
            if h and not mgr.is_uploaded(h.image_id):
                sequences.append(mgr.get_upload_sequence(h))
        for name in _AGENT_TYPES:
            for frame in range(4):
                h = mgr.get_agent_sprite(name, frame, size)
                if h and not mgr.is_uploaded(h.image_id):
                    sequences.append(mgr.get_upload_sequence(h))
    return "".join(sequences)


class KittyApp:
    """Main Kitty viewer application.

    Parameters
    ----------
    base_url:
        Base URL of the hamlet daemon HTTP server.
    """

    def __init__(self, base_url: str = "http://localhost:8080") -> None:
        self._base_url = base_url
        self._fetcher = StateFetcher(base_url)
        self._running = False
        self._zoom = ZoomLevel.FAR
        self._show_legend = False
        self._renderer: KittyRenderer | None = None
        self._sprite_mgr: SpriteManager | None = None
        self._center_x = 0
        self._center_y = 0
        self._follow_target: str | None = None
        self._snapshot = StateSnapshot()
        self._last_fetch = 0.0
        self._frame_count = 0
        self._cols = 80
        self._rows = 24

    def run(self) -> int:
        """Run the viewer. Returns 0 on clean exit, 1 on error."""
        # Health check BEFORE taking terminal
        if not self._fetcher.check_health():
            print(
                f"Error: Hamlet daemon is not running at {self._base_url}",
                file=sys.stderr,
            )
            print(
                "       Start the daemon first with: hamlet daemon",
                file=sys.stderr,
            )
            return 1

        # Get terminal dimensions before initial fetch so terrain bounds are correct
        self._cols, self._rows = os.get_terminal_size()

        # Initial state fetch
        self._do_fetch()

        # Set initial viewport from first village
        if self._snapshot.villages:
            v = self._snapshot.villages[0]
            self._center_x = v.center.x
            self._center_y = v.center.y

        # Enter raw mode
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            sys.stdout.write("\x1b[?1049h\x1b[?25l")  # alt screen, hide cursor
            sys.stdout.flush()

            self._cols, self._rows = os.get_terminal_size()
            self._sprite_mgr = SpriteManager()
            upload_seq = _upload_sprites(self._sprite_mgr)
            if upload_seq:
                sys.stdout.write(upload_seq)
                sys.stdout.flush()
            self._renderer = KittyRenderer(
                sys.stdout,
                self._cols,
                self._rows,
                sprite_manager=self._sprite_mgr,
            )
            self._running = True
            self._render_loop()
        finally:
            if self._renderer:
                self._renderer.cleanup()
            sys.stdout.write("\x1b[?25h\x1b[?1049l")  # show cursor, leave alt screen
            sys.stdout.flush()
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        return 0

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    def _do_fetch(self) -> None:
        """Fetch a new state snapshot from the daemon."""
        half_w = self._cols // 2
        half_h = self._rows // 2
        self._snapshot = self._fetcher.fetch_snapshot(
            self._center_x, self._center_y, half_w, half_h
        )
        self._last_fetch = time.monotonic()

    def _render_loop(self) -> None:
        """Main render loop at 30 FPS."""
        while self._running:
            frame_start = time.monotonic()

            # Periodic state fetch
            if frame_start - self._last_fetch >= _FETCH_INTERVAL:
                self._do_fetch()

            # Handle input
            self._handle_input()

            if not self._running:
                break

            # Follow mode: center on followed agent
            if self._follow_target and self._snapshot.agents:
                for agent in self._snapshot.agents:
                    if agent.id == self._follow_target:
                        self._center_x = agent.position.x
                        self._center_y = agent.position.y
                        break

            # Build ViewportState
            viewport = ViewportState(
                center=Position(self._center_x, self._center_y),
                size=Size(self._cols, self._rows),
                follow_mode="center" if self._follow_target else "free",
            )

            # Render
            assert self._renderer is not None
            self._renderer.set_zoom(self._zoom)
            self._renderer.render_frame(
                viewport,
                self._snapshot.agents,
                self._snapshot.structures,
                self._snapshot.terrain_data,
                self._snapshot.event_log,
            )

            # Legend overlay
            if self._show_legend:
                self._render_legend()

            sys.stdout.flush()
            self._frame_count += 1

            # Sleep remainder of frame
            elapsed = time.monotonic() - frame_start
            if elapsed < _FRAME_DURATION:
                time.sleep(_FRAME_DURATION - elapsed)

    def _handle_input(self) -> None:
        """Handle non-blocking keyboard input."""
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return

        ch = sys.stdin.read(1)
        if ch == "q":
            self._running = False
        elif ch == "h":
            self._center_x -= 1
            self._follow_target = None
        elif ch == "l":
            self._center_x += 1
            self._follow_target = None
        elif ch == "k":
            self._center_y -= 1
            self._follow_target = None
        elif ch == "j":
            self._center_y += 1
            self._follow_target = None
        elif ch == "f":
            self._toggle_follow()
        elif ch == "+":
            self._zoom = prev_zoom(self._zoom)
        elif ch == "-":
            self._zoom = next_zoom(self._zoom)
        elif ch == "/":
            self._show_legend = not self._show_legend
        elif ch == "\x1b":
            # Escape sequence — read arrow keys
            more_ready, _, _ = select.select([sys.stdin], [], [], 0)
            if more_ready:
                seq1 = sys.stdin.read(1)
                if seq1 == "[":
                    if select.select([sys.stdin], [], [], 0.05)[0]:
                        seq2 = sys.stdin.read(1)
                    else:
                        return  # discard partial sequence
                    if seq2 == "A":  # Up
                        self._center_y -= 1
                        self._follow_target = None
                    elif seq2 == "B":  # Down
                        self._center_y += 1
                        self._follow_target = None
                    elif seq2 == "C":  # Right
                        self._center_x += 1
                        self._follow_target = None
                    elif seq2 == "D":  # Left
                        self._center_x -= 1
                        self._follow_target = None

    def _toggle_follow(self) -> None:
        """Toggle follow mode. Picks first agent if no target set."""
        if self._follow_target:
            self._follow_target = None
        elif self._snapshot.agents:
            first = self._snapshot.agents[0]
            self._follow_target = first.id or None

    def _render_legend(self) -> None:
        """Render a bordered legend overlay in the center of the screen."""
        config = default_config()

        lines: list[str] = []
        lines.append("Key Bindings")
        lines.append("────────────")
        lines.append("q        quit")
        lines.append("hjkl     pan (vim-style)")
        lines.append("arrows   pan")
        lines.append("f        follow agent")
        lines.append("+/-      zoom in/out")
        lines.append("/        toggle legend")
        lines.append("")
        lines.append("Terrain Symbols")
        lines.append("────────────────")
        for terrain_type, symbol in config.terrain.symbols.items():
            lines.append(f"  {symbol}  {terrain_type}")
        lines.append("")
        lines.append("Agent: @")

        # Compute box dimensions
        inner_width = max(len(line) for line in lines)
        box_width = inner_width + 4  # 2 border + 2 padding

        # Center position
        start_col = max(0, (self._cols - box_width) // 2)
        start_row = max(0, (self._rows - len(lines) - 2) // 2)

        buf: list[str] = []

        # Top border
        buf.append(f"\x1b[{start_row + 1};{start_col + 1}H")
        buf.append("┌" + "─" * (box_width - 2) + "┐")

        # Content lines
        for i, line in enumerate(lines):
            row = start_row + 1 + i
            buf.append(f"\x1b[{row + 1};{start_col + 1}H")
            padded = line.ljust(inner_width)
            buf.append("│ " + padded + " │")

        # Bottom border
        bottom_row = start_row + len(lines) + 1
        buf.append(f"\x1b[{bottom_row + 1};{start_col + 1}H")
        buf.append("└" + "─" * (box_width - 2) + "┘")

        sys.stdout.write("".join(buf))


__all__ = ["KittyApp"]
