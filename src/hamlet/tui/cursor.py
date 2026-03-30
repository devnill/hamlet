"""Cursor state for tracking cursor visibility and selection.

The cursor appears at viewport center after movement keys and fades after
a configurable period of inactivity (default 3 seconds).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hamlet.viewport.coordinates import Position

__all__ = ["CursorState"]


@dataclass
class CursorState:
    """Mutable state for the cursor, tracking visibility and selection.

    The cursor fades after a configurable period of inactivity to avoid
    distracting from the world view. Activity (movement, selection) resets
    the visibility timer.

    Attributes:
        visible: Whether the cursor should be rendered (respects fade logic).
        last_activity: Unix timestamp of the last cursor activity.
        fade_after_seconds: Seconds of inactivity before cursor fades.
        viewport_center: Current center position of the viewport in world coords.
        selected_item: Currently selected item, if any (dict with type and id).
    """

    visible: bool = True
    last_activity: float = 0.0
    fade_after_seconds: float = 3.0
    viewport_center: Position = field(default_factory=lambda: Position(0, 0))
    selected_item: dict[str, Any] | None = None

    def is_visible(self) -> bool:
        """Return True if the cursor should be visible based on activity timing.

        A cursor is visible if:
        - The visible flag is True, AND
        - The time since last_activity is within fade_after_seconds

        Returns:
            True if cursor should be rendered, False otherwise.
        """
        if not self.visible:
            return False

        import time

        elapsed = time.time() - self.last_activity
        return elapsed <= self.fade_after_seconds

    def reset_activity(self) -> None:
        """Update last_activity timestamp to now and ensure visible."""
        import time

        self.last_activity = time.time()
        self.visible = True

    def hide(self) -> None:
        """Hide the cursor regardless of activity timing."""
        self.visible = False

    def select(self, item_type: str, item_id: str, **extra: Any) -> None:
        """Select an item and reset activity.

        Args:
            item_type: Type of the selected item (e.g., 'agent', 'structure').
            item_id: Unique identifier for the selected item.
            **extra: Additional metadata about the selection.
        """
        self.selected_item = {"type": item_type, "id": item_id, **extra}
        self.reset_activity()

    def clear_selection(self) -> None:
        """Clear the current selection."""
        self.selected_item = None

    def set_viewport_center(self, position: Position) -> None:
        """Update the viewport center position and reset activity."""
        self.viewport_center = position
        self.reset_activity()