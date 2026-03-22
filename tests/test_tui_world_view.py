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
    size_tier: int = 1,
) -> MagicMock:
    """Create a mock Structure with the given position and properties."""
    structure = MagicMock(spec=Structure)
    structure.position = Position(x=x, y=y)
    structure.type = structure_type
    structure.material = material
    structure.stage = stage
    structure.size_tier = size_tier
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

    def test_render_tier2_structure_renders_3x3_box(self, world_view_with_bounds: WorldView) -> None:
        """Tier-2 structure at (5,5) renders a 3x3 box with +, -, |, and symbol."""
        structure = _make_structure(x=5, y=5, structure_type=StructureType.HOUSE, size_tier=2)
        world_view_with_bounds._agents = []
        world_view_with_bounds._structures = [structure]

        text = world_view_with_bounds.render()

        # Parse rendered text into a grid: lines[y][x]
        lines = text.plain.splitlines()

        bounds = world_view_with_bounds._viewport.get_visible_bounds()
        def char_at(wx: int, wy: int) -> str:
            row = wy - bounds.min_y
            col = wx - bounds.min_x
            return lines[row][col]

        # Corners
        assert char_at(4, 4) == "+"
        assert char_at(6, 4) == "+"
        assert char_at(4, 6) == "+"
        assert char_at(6, 6) == "+"
        # Horizontal edges
        assert char_at(5, 4) == "-"
        assert char_at(5, 6) == "-"
        # Vertical edges
        assert char_at(4, 5) == "|"
        assert char_at(6, 5) == "|"
        # Interior (center) shows structure symbol
        from hamlet.tui.symbols import get_structure_symbol
        assert char_at(5, 5) == get_structure_symbol(structure)

    def test_render_agent_takes_priority_over_structure_cell(self, world_view_with_bounds: WorldView) -> None:
        """Agent at a structure footprint cell renders as agent, not structure border."""
        structure = _make_structure(x=5, y=5, structure_type=StructureType.HOUSE, size_tier=2)
        agent = _make_agent(x=4, y=5, state=AgentState.IDLE)

        world_view_with_bounds._agents = [agent]
        world_view_with_bounds._structures = [structure]

        text = world_view_with_bounds.render()
        lines = text.plain.splitlines()

        bounds = world_view_with_bounds._viewport.get_visible_bounds()
        row = 5 - bounds.min_y
        col = 4 - bounds.min_x
        # Agent symbol takes priority over the "|" border that would be at (4,5)
        assert lines[row][col] == "@"


def _make_terrain_grid(terrain_map: dict) -> MagicMock:
    """Create a mock TerrainGrid with specified terrain at positions.

    Args:
        terrain_map: Dict mapping (x, y) tuples to TerrainType values

    Returns:
        Mock TerrainGrid that returns terrain from the map
    """
    from hamlet.world_state.terrain import TerrainType
    from hamlet.world_state.types import Position

    grid = MagicMock()

    def get_terrain(pos):
        return terrain_map.get((pos.x, pos.y), TerrainType.PLAIN)

    def get_terrain_in_bounds(bounds):
        result = {}
        for y in range(bounds.min_y, bounds.max_y + 1):
            for x in range(bounds.min_x, bounds.max_x + 1):
                pos = Position(x, y)
                terrain = terrain_map.get((x, y), TerrainType.PLAIN)
                result[pos] = terrain
        return result

    grid.get_terrain.side_effect = get_terrain
    grid.get_terrain_in_bounds.side_effect = get_terrain_in_bounds
    return grid


class TestWorldViewTerrain:
    """Test suite for terrain rendering in WorldView widget."""

    @pytest.fixture
    def world_view_with_terrain(self) -> WorldView:
        """Create a WorldView with mocked viewport and terrain_grid."""
        from hamlet.world_state.terrain import TerrainType

        viewport = Mock()
        viewport.get_visible_bounds.return_value = BoundingBox(
            min_x=0, min_y=0, max_x=10, max_y=10
        )
        world_state = Mock()

        # Create terrain grid with water at (2, 2), mountain at (5, 5)
        terrain_grid = _make_terrain_grid({
            (2, 2): TerrainType.WATER,
            (5, 5): TerrainType.MOUNTAIN,
        })

        return WorldView(world_state, viewport, terrain_grid)

    def test_render_terrain_shows_water_symbol_at_water_position(self, world_view_with_terrain: WorldView) -> None:
        """Terrain layer renders water symbol at water positions."""
        from hamlet.world_state.terrain import TerrainType

        world_view_with_terrain._agents = []
        world_view_with_terrain._structures = []

        text = world_view_with_terrain.render()
        lines = text.plain.splitlines()

        bounds = world_view_with_terrain._viewport.get_visible_bounds()
        row = 2 - bounds.min_y
        col = 2 - bounds.min_x

        # Water should render as '~' at position (2, 2)
        assert lines[row][col] == TerrainType.WATER.symbol  # '~'

    def test_render_terrain_shows_mountain_symbol_at_mountain_position(self, world_view_with_terrain: WorldView) -> None:
        """Terrain layer renders mountain symbol at mountain positions."""
        from hamlet.world_state.terrain import TerrainType

        world_view_with_terrain._agents = []
        world_view_with_terrain._structures = []

        text = world_view_with_terrain.render()
        lines = text.plain.splitlines()

        bounds = world_view_with_terrain._viewport.get_visible_bounds()
        row = 5 - bounds.min_y
        col = 5 - bounds.min_x

        # Mountain should render as '^' at position (5, 5)
        assert lines[row][col] == TerrainType.MOUNTAIN.symbol  # '^'

    def test_render_terrain_layer_for_empty_cells(self, world_view_with_terrain: WorldView) -> None:
        """WorldView renders terrain symbols as background when no agent or structure is present."""
        from hamlet.world_state.terrain import TerrainType

        world_view_with_terrain._agents = []
        world_view_with_terrain._structures = []

        text = world_view_with_terrain.render()
        lines = text.plain.splitlines()

        bounds = world_view_with_terrain._viewport.get_visible_bounds()

        # Check that water at (2,2) renders as '~' and not as plain '.'
        row = 2 - bounds.min_y
        col = 2 - bounds.min_x
        assert lines[row][col] == TerrainType.WATER.symbol

        # Check that mountain at (5,5) renders as '^'
        row = 5 - bounds.min_y
        col = 5 - bounds.min_x
        assert lines[row][col] == TerrainType.MOUNTAIN.symbol

        # Check that positions without explicit terrain default to plain ('.')
        # Position (0, 0) is not in our terrain map, should show PLAIN
        row = 0 - bounds.min_y
        col = 0 - bounds.min_x
        assert lines[row][col] == TerrainType.PLAIN.symbol  # '.'

    def test_render_agent_takes_priority_over_terrain(self, world_view_with_terrain: WorldView) -> None:
        """Agent renders on top of terrain, not terrain symbol at that position."""
        from hamlet.world_state.terrain import TerrainType

        # Place agent at (2, 2) which is water terrain
        agent = _make_agent(x=2, y=2, state=AgentState.IDLE)
        world_view_with_terrain._agents = [agent]
        world_view_with_terrain._structures = []

        text = world_view_with_terrain.render()
        lines = text.plain.splitlines()

        bounds = world_view_with_terrain._viewport.get_visible_bounds()
        row = 2 - bounds.min_y
        col = 2 - bounds.min_x

        # Agent should show '@', not water symbol '~'
        assert lines[row][col] == "@"

    def test_render_structure_takes_priority_over_terrain(self, world_view_with_terrain: WorldView) -> None:
        """Structure renders on top of terrain, not terrain symbol at that position."""
        from hamlet.world_state.terrain import TerrainType

        # Place structure at (5, 5) which is mountain terrain
        structure = _make_structure(x=5, y=5, structure_type=StructureType.HOUSE)
        world_view_with_terrain._agents = []
        world_view_with_terrain._structures = [structure]

        text = world_view_with_terrain.render()
        lines = text.plain.splitlines()

        bounds = world_view_with_terrain._viewport.get_visible_bounds()
        row = 5 - bounds.min_y
        col = 5 - bounds.min_x

        # Structure should show its symbol, not mountain '^'
        from hamlet.tui.symbols import get_structure_symbol
        assert lines[row][col] == get_structure_symbol(structure)

    def test_render_without_terrain_grid_shows_dots(self) -> None:
        """WorldView without terrain_grid renders '.' for empty cells."""
        viewport = Mock()
        viewport.get_visible_bounds.return_value = BoundingBox(
            min_x=0, min_y=0, max_x=5, max_y=5
        )
        world_state = Mock()

        # Create WorldView without terrain_grid
        world_view = WorldView(world_state, viewport, terrain_grid=None)
        world_view._agents = []
        world_view._structures = []

        text = world_view.render()
        plain_text = text.plain

        # Without terrain, all empty cells should show '.'
        assert "." in plain_text

    def test_render_forest_terrain_with_correct_symbol(self) -> None:
        """Forest terrain renders with correct symbol and color."""
        from hamlet.world_state.terrain import TerrainType

        viewport = Mock()
        viewport.get_visible_bounds.return_value = BoundingBox(
            min_x=0, min_y=0, max_x=5, max_y=5
        )
        world_state = Mock()

        terrain_grid = _make_terrain_grid({
            (3, 3): TerrainType.FOREST,
        })

        world_view = WorldView(world_state, viewport, terrain_grid)
        world_view._agents = []
        world_view._structures = []

        text = world_view.render()
        lines = text.plain.splitlines()

        bounds = viewport.get_visible_bounds()
        row = 3 - bounds.min_y
        col = 3 - bounds.min_x

        # Forest should render as '♣'
        assert lines[row][col] == TerrainType.FOREST.symbol

    def test_render_meadow_terrain_with_correct_symbol(self) -> None:
        """Meadow terrain renders with correct symbol."""
        from hamlet.world_state.terrain import TerrainType

        viewport = Mock()
        viewport.get_visible_bounds.return_value = BoundingBox(
            min_x=0, min_y=0, max_x=5, max_y=5
        )
        world_state = Mock()

        terrain_grid = _make_terrain_grid({
            (2, 4): TerrainType.MEADOW,
        })

        world_view = WorldView(world_state, viewport, terrain_grid)
        world_view._agents = []
        world_view._structures = []

        text = world_view.render()
        lines = text.plain.splitlines()

        bounds = viewport.get_visible_bounds()
        row = 4 - bounds.min_y
        col = 2 - bounds.min_x

        # Meadow should render as '"'
        assert lines[row][col] == TerrainType.MEADOW.symbol
