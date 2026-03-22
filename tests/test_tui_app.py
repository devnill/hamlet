"""Tests for HamletApp TUI application (work item 087).

Test framework: pytest + pytest-asyncio (see pyproject.toml dev dependencies).
Run with: pytest tests/test_tui_app.py -v
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from textual.app import App, ComposeResult

from hamlet.tui.app import HamletApp
from hamlet.tui.status_bar import StatusBar
from hamlet.tui.event_log import EventLog
from hamlet.tui.legend import LegendOverlay
from hamlet.tui.world_view import WorldView
from hamlet.viewport.coordinates import BoundingBox, Position
from hamlet.viewport.state import ViewportState


class TestHamletApp:
    """Test suite for HamletApp TUI application."""

    @pytest.fixture
    def mock_world_state(self) -> Mock:
        """Create a mock WorldStateManager."""
        ws = Mock()
        ws.get_agents_in_view = AsyncMock(return_value=[])
        ws.get_structures_in_view = AsyncMock(return_value=[])
        ws.get_projects = AsyncMock(return_value=[])
        ws.get_event_log = AsyncMock(return_value=[])
        ws.get_all_agents = AsyncMock(return_value=[])
        return ws

    @pytest.fixture
    def mock_viewport(self) -> Mock:
        """Create a mock ViewportManager."""
        vp = Mock()
        vp.update = AsyncMock()
        vp.get_visible_bounds.return_value = BoundingBox(
            min_x=0, min_y=0, max_x=10, max_y=10
        )
        vp_state = ViewportState(
            center=Position(x=0, y=0),
            size=Mock(width=80, height=24),
            follow_mode="center",
            follow_target=None,
        )
        vp.get_viewport_state.return_value = vp_state
        return vp

    @pytest.mark.asyncio
    async def test_compose_yields_all_widgets(
        self, mock_world_state: Mock, mock_viewport: Mock
    ) -> None:
        """HamletApp compose yields all expected widgets."""

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            # Check all widgets are mounted
            status_bar = pilot.app.query_one(StatusBar)
            world_view = pilot.app.query_one(WorldView)
            event_log = pilot.app.query_one(EventLog)
            legend_overlay = pilot.app.query_one(LegendOverlay)

            assert status_bar is not None
            assert world_view is not None
            assert event_log is not None
            assert legend_overlay is not None

    @pytest.mark.asyncio
    async def test_action_scroll_left_calls_viewport(
        self, mock_world_state: Mock, mock_viewport: Mock
    ) -> None:
        """Action scroll_left calls viewport.scroll with correct arguments."""

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            await pilot.press("h")
            await pilot.pause()

            mock_viewport.scroll.assert_called_with(-1, 0)

    @pytest.mark.asyncio
    async def test_action_scroll_right_calls_viewport(
        self, mock_world_state: Mock, mock_viewport: Mock
    ) -> None:
        """Action scroll_right calls viewport.scroll with correct arguments."""

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()

            mock_viewport.scroll.assert_called_with(1, 0)

    @pytest.mark.asyncio
    async def test_action_scroll_up_calls_viewport(
        self, mock_world_state: Mock, mock_viewport: Mock
    ) -> None:
        """Action scroll_up calls viewport.scroll with correct arguments."""

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            await pilot.press("k")
            await pilot.pause()

            mock_viewport.scroll.assert_called_with(0, -1)

    @pytest.mark.asyncio
    async def test_action_scroll_down_calls_viewport(
        self, mock_world_state: Mock, mock_viewport: Mock
    ) -> None:
        """Action scroll_down calls viewport.scroll with correct arguments."""

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            await pilot.press("j")
            await pilot.pause()

            mock_viewport.scroll.assert_called_with(0, 1)

    @pytest.mark.asyncio
    async def test_action_scroll_with_arrow_keys(
        self, mock_world_state: Mock, mock_viewport: Mock
    ) -> None:
        """Action scroll works with arrow keys as well as hjkl."""

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            # Test left arrow
            await pilot.press("left")
            await pilot.pause()
            mock_viewport.scroll.assert_called_with(-1, 0)

            # Test right arrow
            await pilot.press("right")
            await pilot.pause()
            mock_viewport.scroll.assert_called_with(1, 0)

    @pytest.mark.asyncio
    async def test_action_toggle_legend_toggles_visibility(
        self, mock_world_state: Mock, mock_viewport: Mock
    ) -> None:
        """Action toggle_legend toggles LegendOverlay visibility."""

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            legend = pilot.app.query_one(LegendOverlay)

            # Initially hidden (display: none in CSS)
            initial_display = legend.display
            assert initial_display is False

            # Press / to toggle legend
            await pilot.press("/")
            await pilot.pause()

            # Display should have toggled
            assert legend.display is not initial_display

            # Press / again to toggle back
            await pilot.press("/")
            await pilot.pause()

            assert legend.display is initial_display

    @pytest.mark.asyncio
    async def test_update_state_updates_status_bar(
        self, mock_world_state: Mock, mock_viewport: Mock
    ) -> None:
        """_update_state updates StatusBar with agent and structure counts."""
        # Set up mock return values
        mock_agents = [Mock(), Mock(), Mock()]  # 3 agents
        mock_structures = [Mock(), Mock()]  # 2 structures

        mock_world_state.get_agents_in_view = AsyncMock(return_value=mock_agents)
        mock_world_state.get_structures_in_view = AsyncMock(return_value=mock_structures)

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            status_bar = pilot.app.query_one(StatusBar)

            # Manually trigger update_state
            await pilot.app._update_state()
            await pilot.pause()

            # Status bar should be updated
            assert status_bar.agent_count == 3
            assert status_bar.structure_count == 2

    @pytest.mark.asyncio
    async def test_update_state_updates_event_log(
        self, mock_world_state: Mock, mock_viewport: Mock
    ) -> None:
        """_update_state updates EventLog with events."""
        from datetime import datetime

        # Create properly configured mock events with timestamp and summary
        event1 = Mock()
        event1.timestamp = datetime(2025, 1, 15, 10, 30, 0)
        event1.summary = "Test event 1"
        event2 = Mock()
        event2.timestamp = datetime(2025, 1, 15, 10, 31, 0)
        event2.summary = "Test event 2"
        mock_events = [event1, event2]
        mock_world_state.get_event_log = AsyncMock(return_value=mock_events)

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            event_log = pilot.app.query_one(EventLog)

            await pilot.app._update_state()
            await pilot.pause()

            assert event_log.events == mock_events

    @pytest.mark.asyncio
    async def test_update_state_handles_errors_gracefully(
        self, mock_world_state: Mock, mock_viewport: Mock
    ) -> None:
        """_update_state handles errors following GP-7 (errors logged, not raised)."""
        mock_world_state.get_agents_in_view = AsyncMock(side_effect=Exception("DB error"))

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            # Should not raise
            await pilot.app._update_state()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_action_quit_exits_app(
        self, mock_world_state: Mock, mock_viewport: Mock
    ) -> None:
        """Action quit exits the application."""

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            await pilot.press("q")
            await pilot.pause()

            assert pilot.app._exit

    @pytest.mark.asyncio
    async def test_bindings_defined(self, mock_world_state: Mock, mock_viewport: Mock) -> None:
        """HamletApp has expected key bindings defined."""

        class TestHamletApp(HamletApp):
            def __init__(self) -> None:
                super().__init__(mock_world_state, mock_viewport)

        async with TestHamletApp().run_test() as pilot:
            bindings = pilot.app.BINDINGS
            binding_keys = [b.key for b in bindings]

            assert "q" in binding_keys  # quit
            assert "h" in binding_keys  # scroll_left
            assert "l" in binding_keys  # scroll_right
            assert "j" in binding_keys  # scroll_down
            assert "k" in binding_keys  # scroll_up
            assert "/" in binding_keys  # toggle_legend
            assert "f" in binding_keys  # toggle_follow
