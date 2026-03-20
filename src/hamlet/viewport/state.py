"""Viewport state dataclass for tracking center position and follow mode."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .coordinates import Position, Size

__all__ = ["ViewportState"]


@dataclass
class ViewportState:
    """Mutable state for the viewport, tracking center position and follow mode."""

    center: Position = field(default_factory=lambda: Position(0, 0))
    size: Size = field(default_factory=lambda: Size(80, 24))
    follow_mode: Literal["center", "free"] = "center"
    follow_target: str | None = None

    def set_center(self, position: Position) -> None:
        """Set the viewport center and switch to free mode."""
        self.follow_mode = "free"
        self.follow_target = None
        self.center = position

    def scroll(self, delta_x: int, delta_y: int) -> None:
        """Scroll the viewport by a delta and switch to free mode."""
        self.follow_mode = "free"
        self.follow_target = None
        self.center = Position(self.center.x + delta_x, self.center.y + delta_y)

    def set_follow_target(self, agent_id: str) -> None:
        """Set a follow target agent and switch to center mode."""
        self.follow_mode = "center"
        self.follow_target = agent_id
