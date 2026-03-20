"""EventLog Textual widget displaying recent world events."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from hamlet.world_state.state import EventLogEntry

__all__ = ["EventLog"]


class EventLog(Static):
    """Scrollable event log widget showing recent Hamlet events."""

    events: reactive[list] = reactive(list)
    max_lines: reactive[int] = reactive(5)

    def render(self) -> str:
        """Render the most recent max_lines events, newest at bottom."""
        if not self.events:
            return "No events"

        recent = self.events[-self.max_lines:]
        lines = []
        for event in recent:
            timestamp = event.timestamp.strftime("%H:%M:%S")
            lines.append(f"[{timestamp}] {event.summary}")
        return "\n".join(lines)
