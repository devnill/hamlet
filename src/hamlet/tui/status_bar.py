"""StatusBar Textual widget displaying world summary information."""
from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

__all__ = ["StatusBar"]


class StatusBar(Static):
    """Status bar widget showing agent count, structure count, village name, and viewport position."""

    agent_count: reactive[int] = reactive(0)
    structure_count: reactive[int] = reactive(0)
    village_name: reactive[str] = reactive("")
    viewport_pos: reactive[tuple[int, int]] = reactive((0, 0))
    current_activity: reactive[str] = reactive("")
    cursor_summary: reactive[str] = reactive("")

    def render(self) -> str:
        x, y = self.viewport_pos
        village_display = self.village_name if self.village_name else "\u2014"
        base = (
            f"Agents: {self.agent_count} │ "
            f"Structures: {self.structure_count} │ "
            f"Village: {village_display} │ "
            f"({x}, {y})"
        )
        if self.cursor_summary:
            base = f"{base} │ {self.cursor_summary}"
        if self.current_activity:
            return f"{base} │ {self.current_activity}"
        return base
