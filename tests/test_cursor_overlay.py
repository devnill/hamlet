"""Tests for CursorOverlay widget."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from hamlet.tui.cursor import CursorState
from hamlet.tui.cursor_overlay import CursorOverlay


class TestCursorOverlay:
    """Test cases for CursorOverlay widget."""

    def test_init_with_cursor_state(self) -> None:
        """CursorOverlay initializes with CursorState."""
        cursor_state = CursorState()
        overlay = CursorOverlay(cursor_state=cursor_state)
        assert overlay._cursor_state is cursor_state

    def test_init_without_cursor_state(self) -> None:
        """CursorOverlay initializes without CursorState (defaults to None)."""
        overlay = CursorOverlay()
        assert overlay._cursor_state is None

    def test_check_visibility_no_cursor_state(self) -> None:
        """_check_visibility returns False when no CursorState provided."""
        overlay = CursorOverlay()
        assert overlay._check_visibility() is False

    def test_check_visibility_visible_state(self) -> None:
        """_check_visibility returns True when CursorState is visible."""
        cursor_state = CursorState(visible=True, last_activity=time.time())
        overlay = CursorOverlay(cursor_state=cursor_state)
        assert overlay._check_visibility() is True

    def test_check_visibility_hidden_state(self) -> None:
        """_check_visibility returns False when CursorState.visible is False."""
        cursor_state = CursorState(visible=False, last_activity=time.time())
        overlay = CursorOverlay(cursor_state=cursor_state)
        assert overlay._check_visibility() is False

    def test_check_visibility_faded(self) -> None:
        """_check_visibility returns False when cursor has faded due to inactivity."""
        # Set activity time far enough in the past to trigger fade
        cursor_state = CursorState(
            visible=True,
            last_activity=time.time() - 10.0,  # 10 seconds ago
            fade_after_seconds=3.0,
        )
        overlay = CursorOverlay(cursor_state=cursor_state)
        assert overlay._check_visibility() is False

    def test_render_returns_crosshair_when_visible(self) -> None:
        """render() returns '+' when _visible is True."""
        overlay = CursorOverlay()
        overlay._visible = True
        assert overlay.render() == "+"

    def test_render_returns_empty_when_not_visible(self) -> None:
        """render() returns empty string when _visible is False."""
        overlay = CursorOverlay()
        overlay._visible = False
        assert overlay.render() == ""

    def test_watch_visible_sets_display_true(self) -> None:
        """_watch__visible sets display to True when visible is True."""
        overlay = CursorOverlay()
        overlay._watch__visible(True)
        # In Textual, display is boolean: True means visible
        assert overlay.display is True

    def test_watch_visible_sets_display_false(self) -> None:
        """_watch__visible sets display to False when visible is False."""
        overlay = CursorOverlay()
        overlay._watch__visible(False)
        # In Textual, display is boolean: False means hidden
        assert overlay.display is False

    def test_default_css_has_layer_overlay(self) -> None:
        """DEFAULT_CSS includes layer: overlay."""
        assert "layer: overlay" in CursorOverlay.DEFAULT_CSS

    def test_default_css_has_display_none(self) -> None:
        """DEFAULT_CSS includes display: none as default."""
        assert "display: none" in CursorOverlay.DEFAULT_CSS

    def test_default_css_has_content_align_center(self) -> None:
        """DEFAULT_CSS centers the cursor content."""
        assert "content-align: center middle" in CursorOverlay.DEFAULT_CSS


class TestCursorOverlayIntegration:
    """Integration tests for CursorOverlay with CursorState."""

    def test_visibility_respects_activity_timing(self) -> None:
        """Visibility correctly reflects activity timing from CursorState."""
        cursor_state = CursorState(
            visible=True,
            last_activity=time.time(),
            fade_after_seconds=3.0,
        )
        overlay = CursorOverlay(cursor_state=cursor_state)

        # Initially visible
        assert overlay._check_visibility() is True

        # Simulate time passing beyond fade threshold
        cursor_state.last_activity = time.time() - 5.0
        assert overlay._check_visibility() is False

        # Reset activity
        cursor_state.reset_activity()
        assert overlay._check_visibility() is True

    def test_visibility_respects_hide(self) -> None:
        """Visibility respects explicit hide() call on CursorState."""
        cursor_state = CursorState(visible=True, last_activity=time.time())
        overlay = CursorOverlay(cursor_state=cursor_state)

        # Initially visible
        assert overlay._check_visibility() is True

        # Hide explicitly
        cursor_state.hide()
        assert overlay._check_visibility() is False

    def test_update_visibility_syncs_with_cursor_state(self) -> None:
        """_update_visibility correctly syncs _visible with CursorState."""
        cursor_state = CursorState(visible=True, last_activity=time.time())
        overlay = CursorOverlay(cursor_state=cursor_state)

        # Should be visible initially
        overlay._update_visibility()
        assert overlay._visible is True

        # Hide the cursor state
        cursor_state.hide()
        overlay._update_visibility()
        assert overlay._visible is False