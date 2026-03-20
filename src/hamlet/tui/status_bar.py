"""StatusBar Textual widget displaying world summary information."""
from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

__all__ = ["StatusBar"]


class StatusBar(Static):
    """Status bar widget showing agent count, structure count, project name, and viewport position."""

    agent_count: reactive[int] = reactive(0)
    structure_count: reactive[int] = reactive(0)
    project_name: reactive[str] = reactive("")
    viewport_pos: reactive[tuple[int, int]] = reactive((0, 0))
    current_activity: reactive[str] = reactive("")

    def render(self) -> str:
        x, y = self.viewport_pos
        base = (
            f"Agents: {self.agent_count} │ "
            f"Structures: {self.structure_count} │ "
            f"Project: {self.project_name} │ "
            f"({x}, {y})"
        )
        if self.current_activity:
            return f"{base} │ {self.current_activity}"
        return base
