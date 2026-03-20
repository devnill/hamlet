"""Tests for ViewportState (work item 085).

Run with: pytest tests/test_viewport_state.py -v
"""
from __future__ import annotations

import pytest

from hamlet.viewport.coordinates import Position
from hamlet.viewport.state import ViewportState


class TestViewportState:
    """Test suite for ViewportState."""

    def test_default_initialization(self) -> None:
        """Test ViewportState default values."""
        state = ViewportState()

        assert state.center == Position(0, 0)
        assert state.size.width == 80
        assert state.size.height == 24
        assert state.follow_mode == "center"
        assert state.follow_target is None

    def test_set_center_switches_to_free(self) -> None:
        """Test that set_center switches to free mode."""
        state = ViewportState()

        # Set up follow mode first
        state.follow_mode = "center"
        state.follow_target = "agent123"

        # Set center
        state.set_center(Position(100, 100))

        # Verify switched to free mode
        assert state.follow_mode == "free"
        assert state.follow_target is None
        assert state.center == Position(100, 100)

    def test_scroll_switches_to_free_mode(self) -> None:
        """Test that scroll switches to free mode."""
        state = ViewportState()

        # Set up follow mode
        state.follow_mode = "center"
        state.follow_target = "agent123"
        initial_center = Position(50, 50)
        state.center = initial_center

        # Scroll
        state.scroll(10, 5)

        # Verify switched to free mode and center updated
        assert state.follow_mode == "free"
        assert state.follow_target is None
        assert state.center == Position(60, 55)

    def test_scroll_negative_delta(self) -> None:
        """Test scrolling with negative deltas."""
        state = ViewportState()
        state.center = Position(50, 50)

        state.scroll(-10, -5)

        assert state.center == Position(40, 45)

    def test_set_follow_target(self) -> None:
        """Test setting follow target."""
        state = ViewportState()

        # Initially in free mode
        state.follow_mode = "free"
        state.follow_target = None

        # Set follow target
        state.set_follow_target("agent123")

        assert state.follow_mode == "center"
        assert state.follow_target == "agent123"

    def test_set_follow_target_overwrites_previous(self) -> None:
        """Test that set_follow_target overwrites previous target."""
        state = ViewportState()

        # Set initial follow target
        state.set_follow_target("agent1")
        assert state.follow_target == "agent1"

        # Set new follow target
        state.set_follow_target("agent2")
        assert state.follow_target == "agent2"
        assert state.follow_mode == "center"

    def test_center_is_mutable(self) -> None:
        """Test that center position can be directly modified."""
        state = ViewportState()

        # Directly modify center
        state.center = Position(200, 150)

        assert state.center == Position(200, 150)
