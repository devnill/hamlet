"""Tests for ViewportManager (work item 085).

Run with: pytest tests/test_viewport_manager.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock

from hamlet.viewport.coordinates import Position, Size
from hamlet.viewport.manager import ViewportManager


class TestViewportManager:
    """Test suite for ViewportManager."""

    @pytest.fixture
    def viewport(self) -> ViewportManager:
        """Return a ViewportManager with a mocked WorldStateManager."""
        world_state = Mock()
        world_state.get_all_villages = AsyncMock(return_value=[])
        world_state.get_all_agents = AsyncMock(return_value=[])
        world_state.get_all_structures = AsyncMock(return_value=[])
        world_state.get_viewport_center = Mock(return_value=None)
        world_state.update_viewport_center = AsyncMock()
        return ViewportManager(world_state)

    def test_world_to_screen_translation(self, viewport: ViewportManager) -> None:
        """Test world-to-screen coordinate translation formula."""
        # Set viewport size and center
        viewport._state.size = Size(80, 24)
        viewport._state.center = Position(50, 50)

        # Translate world position to screen
        world_pos = Position(60, 60)
        screen = viewport.world_to_screen(world_pos)

        # Formula: screen_x = world_x - center_x + width // 2
        # screen_x = 60 - 50 + 40 = 50
        # screen_y = 60 - 50 + 12 = 22
        assert screen.x == 50
        assert screen.y == 22

    def test_scroll_switches_to_free_mode(self, viewport: ViewportManager) -> None:
        """Test that scrolling switches viewport to free mode."""
        # Set up follow mode first
        viewport._state.follow_mode = "center"
        viewport._state.follow_target = "agent123"

        # Scroll the viewport
        viewport.scroll(10, 5)

        # Verify switched to free mode
        assert viewport._state.follow_mode == "free"
        assert viewport._state.follow_target is None

    def test_auto_follow_sets_target(self, viewport: ViewportManager) -> None:
        """Test that auto_follow sets the follow target and mode."""
        # Initially in free mode
        viewport._state.follow_mode = "free"
        viewport._state.follow_target = None

        # Enable auto-follow
        viewport.auto_follow("agent123")

        # Verify follow mode is enabled
        assert viewport._state.follow_target == "agent123"
        assert viewport._state.follow_mode == "center"

    @pytest.mark.asyncio
    async def test_initialize_restores_saved_center(self) -> None:
        """initialize() uses saved viewport center from world_metadata when available."""
        world_state = Mock()
        world_state.get_viewport_center = Mock(return_value=(42, 17))
        world_state.get_all_agents = AsyncMock(return_value=[])
        world_state.get_all_structures = AsyncMock(return_value=[])
        viewport = ViewportManager(world_state)
        await viewport.initialize()
        assert viewport._state.center == Position(42, 17)

    @pytest.mark.asyncio
    async def test_initialize_falls_back_to_village_center(self) -> None:
        """initialize() uses first village center when no saved viewport center exists."""
        village = Mock()
        village.center = Position(10, 20)
        world_state = Mock()
        world_state.get_viewport_center = Mock(return_value=None)
        world_state.get_all_villages = AsyncMock(return_value=[village])
        world_state.get_all_agents = AsyncMock(return_value=[])
        world_state.get_all_structures = AsyncMock(return_value=[])
        viewport = ViewportManager(world_state)
        await viewport.initialize()
        assert viewport._state.center == Position(10, 20)

    def test_scroll_sets_dirty_flag(self, viewport: ViewportManager) -> None:
        """scroll() sets _dirty_center so the center is persisted on next update()."""
        assert viewport._dirty_center is False
        viewport.scroll(1, 0)
        assert viewport._dirty_center is True

    def test_set_center_sets_dirty_flag(self, viewport: ViewportManager) -> None:
        """set_center() sets _dirty_center so the center is persisted on next update()."""
        assert viewport._dirty_center is False
        viewport.set_center(Position(5, 5))
        assert viewport._dirty_center is True

    @pytest.mark.asyncio
    async def test_update_persists_dirty_center(self, viewport: ViewportManager) -> None:
        """update() calls update_viewport_center when _dirty_center is True."""
        viewport._state.center = Position(7, 3)
        viewport._dirty_center = True
        await viewport.update()
        viewport._world_state.update_viewport_center.assert_awaited_once_with(7, 3)
        assert viewport._dirty_center is False

    @pytest.mark.asyncio
    async def test_update_does_not_persist_when_clean(self, viewport: ViewportManager) -> None:
        """update() does not call update_viewport_center when _dirty_center is False."""
        viewport._dirty_center = False
        await viewport.update()
        viewport._world_state.update_viewport_center.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_follows_agent_position(self, viewport: ViewportManager) -> None:
        """Test that update() follows agent position in follow mode."""
        # Create a mock agent
        agent = Mock()
        agent.position = Position(100, 100)

        # Set agent id and configure world state to return it
        agent.id = "agent123"
        viewport._world_state.get_all_agents.return_value = [agent]

        # Enable follow mode
        viewport.auto_follow("agent123")
        assert viewport._state.follow_mode == "center"
        assert viewport._state.follow_target == "agent123"

        # Set initial center
        viewport._state.center = Position(0, 0)

        # Update viewport
        await viewport.update()

        # Verify center now tracks agent position
        assert viewport._state.center == Position(100, 100)
