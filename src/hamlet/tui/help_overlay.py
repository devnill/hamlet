"""Help overlay widget — keyboard controls reference."""
from __future__ import annotations
from textual.widgets import Static


class HelpOverlay(Static):
    """Modal overlay showing keyboard controls. Toggled by ? from HamletApp."""

    DEFAULT_CSS = """
HelpOverlay {
    display: none;
    layer: overlay;
    offset: 2 2;
    width: 42;
    height: 22;
    background: $surface;
}
"""

    def render(self) -> str:
        return (
            "┌─ Help ──────────────────────────────┐\n"
            "│  Arrow keys / hjkl — scroll          │\n"
            "│  f — toggle follow mode              │\n"
            "│  / — legend                          │\n"
            "│  ? — this help menu                  │\n"
            "│  q — quit                            │\n"
            "│                                      │\n"
            "│  Press ? to toggle  •  Esc to close  │\n"
            "└──────────────────────────────────────┘"
        )
