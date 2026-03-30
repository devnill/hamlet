"""CursorOverlay widget — transient cursor display at viewport center.

The cursor appears after movement keypresses and fades after a configurable
period of inactivity (default 3 seconds). It renders a crosshair character
at the center of the viewport.
"""

from __future__ import annotations

from textual.widgets import Static
from textual.reactive import reactive

from hamlet.tui.cursor import CursorState

__all__ = ["CursorOverlay"]


class CursorOverlay(Static):
    """Transient cursor overlay that shows a crosshair at viewport center.

    The cursor appears after movement activity and fades after inactivity.
    Display is controlled by CursorState.is_visible() which respects both
    the visibility flag and activity timing.

    CSS display is set to 'none' when cursor should not be visible,
    'block' when visible. The crosshair is centered via CSS.
    """

    DEFAULT_CSS = """
    CursorOverlay {
        display: none;
        layer: overlay;
        width: 1;
        height: 1;
        content-align: center middle;
        background: transparent;
    }
    """

    # Reactive property to trigger display updates
    _visible: reactive[bool] = reactive(False)

    def __init__(
        self,
        cursor_state: CursorState | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the cursor overlay.

        Args:
            cursor_state: CursorState instance to query for visibility.
            name: Widget name (Textual).
            id: Widget ID (Textual).
            classes: CSS classes (Textual).
        """
        super().__init__(name=name, id=id, classes=classes)
        self._cursor_state = cursor_state

    def _check_visibility(self) -> bool:
        """Check if cursor should be visible based on CursorState.

        Returns:
            True if cursor should be displayed, False otherwise.
        """
        if self._cursor_state is None:
            return False
        return self._cursor_state.is_visible()

    def on_mount(self) -> None:
        """Set up periodic visibility check after widget mounts."""
        # Refresh visibility at 10 Hz to match fade timing granularity
        self.set_interval(0.1, self._update_visibility)

    def _update_visibility(self) -> None:
        """Update the visible reactive property from CursorState."""
        self._visible = self._check_visibility()

    def _watch__visible(self, visible: bool) -> None:
        """React to visibility changes by updating CSS display property.

        In Textual, display is boolean: True means visible, False means hidden.
        """
        self.display = visible

    def render(self) -> str:
        """Return crosshair character for cursor display.

        Returns:
            Crosshair character '+' when visible, empty string otherwise.
        """
        if not self._visible:
            return ""
        return "+"