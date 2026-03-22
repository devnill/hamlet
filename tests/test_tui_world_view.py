"""Tests for WorldView TUI widget (work item 087).

Test framework: pytest + pytest-asyncio (see pyproject.toml dev dependencies).
Run with: pytest tests/test_tui_world_view.py -v
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import pytest
from rich.text import Text

from hamlet.tui.world_view import WorldView, SPIN_SYMBOLS
from hamlet.world_state.types import Agent, AgentState, AgentType, Position, Structure, StructureType
from hamlet.viewport.coordinates import BoundingBox


def _make_agent(
    x: int = 0,
    y: int = 0,
    state: AgentState = AgentState.ACTIVE,
    agent_type: AgentType = AgentType.GENERAL,
) -> MagicMock:
    """Create a mock Agent with the given position and state."""
    agent = MagicMock(spec=Agent)
    agent.position = Position(x=x, y=y)
    agent.state = state
    agent.inferred_type = agent_type
    agent.color = "white"
    return agent


def _make_structure(
    x: int = 0,
    y: int = 0,
    structure_type: StructureType = StructureType.HOUSE,
    material: str = "wood",
    stage: int = 0,
) -> MagicMock:
    """Create a mock Structure with the given position and properties."""
    structure = MagicMock(spec=Structure)
    structure.position = Position(x=x, y=y)
    structure.type = structure_type
    structure.material = material
    structure.stage = stage
    return structure


class TestWorldView:
    """Test suite for WorldView widget."""

    @pytest.fixture
    def world_view(self) -> WorldView:
        """Create a WorldView with mocked viewport and world_state."""
        viewport = Mock()
        world_state = Mock()
        return WorldView(world_state, viewport)

    @pytest.fixture
    def world_view_with_bounds(self) -> WorldView:
        """Create a WorldView with mocked viewport returning visible bounds."""
        viewport = Mock()
        viewport.get_visible_bounds.return_value = BoundingBox(
            min_x=0, min_y=0, max_x=10, max_y=10
        )
        world_state = Mock()
        return WorldView(world_state, viewport)

    def test_render_shows_agents_at_positions(self, world_view_with_bounds: WorldView) -> None:
        """WorldView render shows agents at their correct positions."""
        # Set up agents at specific positions
        agent1 = _make_agent(x=2, y=3, state=AgentState.IDLE, agent_type=AgentType.CODER)
        agent2 = _make_agent(x=5, y=7, state=AgentState.IDLE, agent_type=AgentType.RESEARCHER)

        world_view_with_bounds._agents = [agent1, agent2]
        world_view_with_bounds._structures = []

        text = world_view_with_bounds.render()

        # The render should be a Rich Text object
        assert isinstance(text, Text)
        # Check that agent symbols are rendered (we check the text content contains agent symbols)
        plain_text = text.plain
        assert "@" in plain_text  # Idle agents show @

    def test_render_shows_structures_at_positions(self, world_view_with_bounds: WorldView) -> None:
        """WorldView render shows structures at their correct positions."""
        # Set up structures at specific positions
        structure1 = _make_structure(x=1, y=1, structure_type=StructureType.HOUSE, material="wood")
        structure2 = _make_structure(x=4, y=4, structure_type=StructureType.FORGE, material="stone")

        world_view_with_bounds._agents = []
        world_view_with_bounds._structures = [structure1, structure2]

        text = world_view_with_bounds.render()

        assert isinstance(text, Text)
        plain_text = text.plain
        # Structure symbols should be present (these are unicode symbols)
        # House = ∩, Forge = ▲
        assert "∩" in plain_text or "▲" in plain_text

    def test_render_agent_active_shows_spin(self, world_view_with_bounds: WorldView) -> None:
        """WorldView render shows spin animation symbol for active agents."""
        # Set up an active agent
        active_agent = _make_agent(x=3, y=3, state=AgentState.ACTIVE, agent_type=AgentType.CODER)
        idle_agent = _make_agent(x=5, y=5, state=AgentState.IDLE, agent_type=AgentType.GENERAL)

        world_view_with_bounds._agents = [active_agent, idle_agent]
        world_view_with_bounds._structures = []

        # Test with different spin frames
        for frame in range(4):
            world_view_with_bounds._spin_frame = frame

            text = world_view_with_bounds.render()
            plain_text = text.plain

            # Active agent should show spin symbol (-, \, |, /)
            spin_symbol = SPIN_SYMBOLS[frame]
            assert spin_symbol in plain_text, f"Spin symbol '{spin_symbol}' not found at frame {frame}"
            # Idle agent should show @
            assert "@" in plain_text

    def test_render_empty_cells_show_dots(self, world_view_with_bounds: WorldView) -> None:
        """WorldView render shows dots for empty floor cells."""
        world_view_with_bounds._agents = []
        world_view_with_bounds._structures = []

        text = world_view_with_bounds.render()
        plain_text = text.plain

        # Empty cells should show dots
        assert "." in plain_text

    def test_render_zombie_agent_shows_at_symbol(self, world_view_with_bounds: WorldView) -> None:
        """WorldView render shows @ symbol for zombie agents (not spinning)."""
        zombie_agent = _make_agent(x=2, y=2, state=AgentState.ZOMBIE)

        world_view_with_bounds._agents = [zombie_agent]
        world_view_with_bounds._structures = []

        text = world_view_with_bounds.render()
        plain_text = text.plain

        # Zombie agents should show @, not spin symbols
        assert "@" in plain_text
        # Should not contain any spin symbols
        for spin in SPIN_SYMBOLS:
            if spin != "@":  # @ is not in SPIN_SYMBOLS anyway
                assert spin not in plain_text, f"Unexpected spin symbol '{spin}' for zombie agent"

    def test_render_combines_agents_and_structures(self, world_view_with_bounds: WorldView) -> None:
        """WorldView render shows both agents and structures in same view."""
        agent = _make_agent(x=2, y=2, state=AgentState.IDLE)
        structure = _make_structure(x=5, y=5, structure_type=StructureType.LIBRARY)

        world_view_with_bounds._agents = [agent]
        world_view_with_bounds._structures = [structure]

        text = world_view_with_bounds.render()
        plain_text = text.plain

        # Both should be present
        assert "@" in plain_text
        # Library = ⌂
        assert "⌂" in plain_text

    async def test_update_animation_frame_updates_state(self) -> None:
        """Test that _update_animation_frame fetches agents and structures."""
        viewport = Mock()
        viewport.get_visible_bounds.return_value = BoundingBox(
            min_x=0, min_y=0, max_x=10, max_y=10
        )

        world_state = Mock()
        world_state.get_agents_in_view = AsyncMock(return_value=[])
        world_state.get_structures_in_view = AsyncMock(return_value=[])

        world_view = WorldView(world_state, viewport)

        await world_view._update_animation_frame()

        world_state.get_agents_in_view.assert_called_once()
        world_state.get_structures_in_view.assert_called_once()

    async def test_update_animation_frame_advances_spin_frame(self) -> None:
        """Test that _update_animation_frame advances the spin frame."""
        viewport = Mock()
        viewport.get_visible_bounds.return_value = BoundingBox(
            min_x=0, min_y=0, max_x=10, max_y=10
        )

        world_state = Mock()
        world_state.get_agents_in_view = AsyncMock(return_value=[])
        world_state.get_structures_in_view = AsyncMock(return_value=[])

        world_view = WorldView(world_state, viewport)
        initial_frame = world_view._spin_frame

        await world_view._update_animation_frame()

        assert world_view._spin_frame == (initial_frame + 1) % 4

    async def test_update_animation_frame_handles_errors_gracefully(self) -> None:
        """Test that _update_animation_frame handles errors following GP-7."""
        viewport = Mock()
        viewport.get_visible_bounds.side_effect = Exception("Viewport error")

        world_state = Mock()

        world_view = WorldView(world_state, viewport)
        world_view._agents = [MagicMock()]  # Set some existing state

        await world_view._update_animation_frame()

        # Should clear agents on error, not raise
        assert world_view._agents == []
        assert world_view._structures == []

    def test_render_returns_loading_when_viewport_fails(self) -> None:
        """Test that render returns 'Loading...' when viewport fails."""
        viewport = Mock()
        viewport.get_visible_bounds.side_effect = Exception("Viewport error")

        world_state = Mock()

        world_view = WorldView(world_state, viewport)

        text = world_view.render()

        assert isinstance(text, Text)
        assert "Loading..." in text.plain

    def test_on_mount_does_not_call_viewport_resize(self) -> None:
        """on_mount must NOT call viewport.resize (premature size is wrong at mount time)."""
        viewport = Mock()
        world_state = Mock()

        world_view = WorldView(world_state, viewport)

        # set_interval is a Textual internal; mock it to avoid errors
        world_view.set_interval = Mock()

        world_view.on_mount()

        viewport.resize.assert_not_called()

    def test_on_resize_calls_resize_with_event_dimensions(self) -> None:
        """on_resize calls viewport.resize with the event's size dimensions."""
        viewport = Mock()
        world_state = Mock()

        world_view = WorldView(world_state, viewport)

        mock_event = MagicMock()
        mock_event.size.width = 120
        mock_event.size.height = 40

        world_view.on_resize(mock_event)

        viewport.resize.assert_called_with(120, 40)

    def test_render_syncs_viewport_to_size(self) -> None:
        """render() calls viewport.resize with the widget's current size each frame."""
        viewport = Mock()
        viewport.get_visible_bounds.return_value = BoundingBox(
            min_x=0, min_y=0, max_x=10, max_y=10
        )
        world_state = Mock()

        world_view = WorldView(world_state, viewport)
        world_view._agents = []
        world_view._structures = []

        # Patch self.size to return a controlled width/height
        mock_size = MagicMock()
        mock_size.width = 120
        mock_size.height = 40

        with patch.object(type(world_view), "size", new_callable=PropertyMock, return_value=mock_size):
            world_view.render()

        viewport.resize.assert_called_with(120, 40)
