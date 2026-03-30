"""Tests for CursorState (work item WI-295).

Run with: pytest tests/test_cursor.py -v
"""
from __future__ import annotations

import time

import pytest

from hamlet.tui.cursor import CursorState
from hamlet.viewport.coordinates import Position


class TestCursorState:
    """Test suite for CursorState."""

    def test_default_initialization(self) -> None:
        """Test CursorState default values."""
        state = CursorState()

        assert state.visible is True
        assert state.last_activity == 0.0
        assert state.fade_after_seconds == 3.0
        assert state.viewport_center == Position(0, 0)
        assert state.selected_item is None

    def test_is_visible_returns_true_when_visible_and_recent_activity(self) -> None:
        """Test is_visible returns True when visible and activity is recent."""
        state = CursorState(fade_after_seconds=3.0)
        state.visible = True
        state.last_activity = time.time()

        assert state.is_visible() is True

    def test_is_visible_returns_false_when_visible_flag_false(self) -> None:
        """Test is_visible returns False when visible flag is False."""
        state = CursorState(fade_after_seconds=3.0)
        state.visible = False
        state.last_activity = time.time()

        assert state.is_visible() is False

    def test_is_visible_returns_false_when_activity_expired(self) -> None:
        """Test is_visible returns False when activity timestamp is too old."""
        state = CursorState(fade_after_seconds=3.0)
        state.visible = True
        # Set last_activity to 10 seconds ago (beyond default fade time)
        state.last_activity = time.time() - 10.0

        assert state.is_visible() is False

    def test_is_visible_respects_custom_fade_duration(self) -> None:
        """Test is_visible respects custom fade_after_seconds."""
        state = CursorState(fade_after_seconds=1.0)
        state.visible = True
        state.last_activity = time.time() - 0.5  # 0.5 seconds ago, within 1s fade

        assert state.is_visible() is True

        # Now set to 2 seconds ago, beyond 1s fade
        state.last_activity = time.time() - 2.0

        assert state.is_visible() is False

    def test_reset_activity_updates_timestamp(self) -> None:
        """Test reset_activity updates last_activity to current time."""
        state = CursorState()
        state.last_activity = 0.0

        before = time.time()
        state.reset_activity()
        after = time.time()

        # last_activity should be between before and after
        assert before <= state.last_activity <= after

    def test_reset_activity_sets_visible_true(self) -> None:
        """Test reset_activity ensures visible is True."""
        state = CursorState()
        state.visible = False

        state.reset_activity()

        assert state.visible is True

    def test_hide_sets_visible_false(self) -> None:
        """Test hide method sets visible to False."""
        state = CursorState()
        state.visible = True

        state.hide()

        assert state.visible is False

    def test_select_sets_selected_item(self) -> None:
        """Test select method sets selected_item with type and id."""
        state = CursorState()

        state.select("agent", "agent-123")

        assert state.selected_item is not None
        assert state.selected_item["type"] == "agent"
        assert state.selected_item["id"] == "agent-123"

    def test_select_accepts_extra_metadata(self) -> None:
        """Test select method accepts additional metadata."""
        state = CursorState()

        state.select("structure", "struct-456", name="Workshop", level=2)

        assert state.selected_item is not None
        assert state.selected_item["type"] == "structure"
        assert state.selected_item["id"] == "struct-456"
        assert state.selected_item["name"] == "Workshop"
        assert state.selected_item["level"] == 2

    def test_select_resets_activity(self) -> None:
        """Test select method resets activity timestamp."""
        state = CursorState()
        state.last_activity = 0.0

        before = time.time()
        state.select("agent", "agent-789")
        after = time.time()

        assert before <= state.last_activity <= after

    def test_clear_selection_removes_selected_item(self) -> None:
        """Test clear_selection sets selected_item to None."""
        state = CursorState()
        state.selected_item = {"type": "agent", "id": "agent-123"}

        state.clear_selection()

        assert state.selected_item is None

    def test_set_viewport_center_updates_position(self) -> None:
        """Test set_viewport_center updates viewport_center."""
        state = CursorState()

        state.set_viewport_center(Position(100, 200))

        assert state.viewport_center == Position(100, 200)

    def test_set_viewport_center_resets_activity(self) -> None:
        """Test set_viewport_center resets activity timestamp."""
        state = CursorState()
        state.last_activity = 0.0

        before = time.time()
        state.set_viewport_center(Position(50, 75))
        after = time.time()

        assert before <= state.last_activity <= after

    def test_custom_fade_after_seconds_in_initialization(self) -> None:
        """Test custom fade_after_seconds can be set at initialization."""
        state = CursorState(fade_after_seconds=5.0)

        assert state.fade_after_seconds == 5.0

    def test_custom_viewport_center_in_initialization(self) -> None:
        """Test custom viewport_center can be set at initialization."""
        state = CursorState(viewport_center=Position(42, 24))

        assert state.viewport_center == Position(42, 24)

    def test_custom_selected_item_in_initialization(self) -> None:
        """Test custom selected_item can be set at initialization."""
        selection = {"type": "village", "id": "village-001"}
        state = CursorState(selected_item=selection)

        assert state.selected_item == selection

    def test_is_visible_at_boundary(self) -> None:
        """Test is_visible at exactly fade_after_seconds boundary."""
        state = CursorState(fade_after_seconds=3.0)
        state.visible = True
        # Set just inside the boundary (accounting for execution time)
        state.last_activity = time.time() - 2.99

        # At just under fade_after_seconds, should still be visible
        assert state.is_visible() is True

    def test_is_visible_just_past_boundary(self) -> None:
        """Test is_visible just past fade_after_seconds boundary."""
        state = CursorState(fade_after_seconds=3.0)
        state.visible = True
        # Just past the boundary
        state.last_activity = time.time() - 3.001

        assert state.is_visible() is False