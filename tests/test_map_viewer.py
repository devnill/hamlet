"""Tests for the map viewer TUI widgets."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid, TerrainType
from hamlet.viewport.coordinates import BoundingBox


class TestMapViewer:
    """Tests for MapViewer widget."""

    def test_map_viewer_initialization(self):
        """Test MapViewer can be initialized with TerrainGrid."""
        config = TerrainConfig(seed=12345)
        generator = TerrainGenerator(config)
        grid = TerrainGrid(generator)

        from hamlet.tui.map_viewer import MapViewer
        viewer = MapViewer(grid, viewport_width=80, viewport_height=24)

        assert viewer._terrain_grid is grid
        assert viewer._viewport_width == 80
        assert viewer._viewport_height == 24

    def test_map_viewer_get_visible_bounds(self):
        """Test visible bounds calculation."""
        config = TerrainConfig(seed=12345)
        generator = TerrainGenerator(config)
        grid = TerrainGrid(generator)

        from hamlet.tui.map_viewer import MapViewer
        viewer = MapViewer(grid, viewport_width=80, viewport_height=24)
        viewer.center_x = 0
        viewer.center_y = 0

        bounds = viewer.get_visible_bounds()
        assert bounds.min_x <= 0
        assert bounds.max_x >= 0
        assert bounds.min_y <= 0
        assert bounds.max_y >= 0

    def test_map_viewer_scroll(self):
        """Test scrolling updates center position."""
        config = TerrainConfig(seed=12345)
        generator = TerrainGenerator(config)
        grid = TerrainGrid(generator)

        from hamlet.tui.map_viewer import MapViewer
        viewer = MapViewer(grid)
        viewer.center_x = 0
        viewer.center_y = 0

        viewer.scroll(10, 5)
        assert viewer.center_x == 10
        assert viewer.center_y == 5

    def test_map_viewer_set_center(self):
        """Test setting center position."""
        config = TerrainConfig(seed=12345)
        generator = TerrainGenerator(config)
        grid = TerrainGrid(generator)

        from hamlet.tui.map_viewer import MapViewer
        viewer = MapViewer(grid)
        viewer.set_center(100, -50)
        assert viewer.center_x == 100
        assert viewer.center_y == -50

    def test_map_viewer_zoom_in(self):
        """Test zooming in increases zoom level."""
        config = TerrainConfig(seed=12345)
        generator = TerrainGenerator(config)
        grid = TerrainGrid(generator)

        from hamlet.tui.map_viewer import MapViewer, ZOOM_LEVELS
        viewer = MapViewer(grid)

        # Default zoom is 1
        assert viewer.zoom == 1

        # Zoom in should increase zoom level
        viewer.zoom_in()
        assert viewer.zoom == 2

        viewer.zoom_in()
        assert viewer.zoom == 4

        viewer.zoom_in()
        assert viewer.zoom == 8

        # Zoom in at max should stay at max
        viewer.zoom_in()
        assert viewer.zoom == 8

    def test_map_viewer_zoom_out(self):
        """Test zooming out decreases zoom level."""
        config = TerrainConfig(seed=12345)
        generator = TerrainGenerator(config)
        grid = TerrainGrid(generator)

        from hamlet.tui.map_viewer import MapViewer
        viewer = MapViewer(grid)

        # Start at max zoom
        viewer.zoom = 8

        # Zoom out should decrease zoom level
        viewer.zoom_out()
        assert viewer.zoom == 4

        viewer.zoom_out()
        assert viewer.zoom == 2

        viewer.zoom_out()
        assert viewer.zoom == 1

        # Zoom out at min should stay at min
        viewer.zoom_out()
        assert viewer.zoom == 1

    def test_map_viewer_reset_zoom(self):
        """Test resetting zoom to default."""
        config = TerrainConfig(seed=12345)
        generator = TerrainGenerator(config)
        grid = TerrainGrid(generator)

        from hamlet.tui.map_viewer import MapViewer
        viewer = MapViewer(grid)

        # Set zoom to something other than default
        viewer.zoom = 4

        # Reset should bring back to 1
        viewer.reset_zoom()
        assert viewer.zoom == 1

    def test_map_viewer_zoom_level_property(self):
        """Test zoom_level property returns current zoom."""
        config = TerrainConfig(seed=12345)
        generator = TerrainGenerator(config)
        grid = TerrainGrid(generator)

        from hamlet.tui.map_viewer import MapViewer
        viewer = MapViewer(grid)

        assert viewer.zoom_level == 1

        viewer.zoom = 4
        assert viewer.zoom_level == 4

    def test_map_viewer_visible_bounds_with_zoom(self):
        """Test visible bounds calculation with zoom."""
        config = TerrainConfig(seed=12345)
        generator = TerrainGenerator(config)
        grid = TerrainGrid(generator)

        from hamlet.tui.map_viewer import MapViewer
        viewer = MapViewer(grid, viewport_width=80, viewport_height=24)
        viewer.center_x = 0
        viewer.center_y = 0

        # At 1x zoom, bounds should be full size
        bounds_1x = viewer.get_visible_bounds()
        width_1x = bounds_1x.max_x - bounds_1x.min_x + 1
        height_1x = bounds_1x.max_y - bounds_1x.min_y + 1

        # At 2x zoom, we should see fewer world cells
        viewer.zoom = 2
        bounds_2x = viewer.get_visible_bounds()
        width_2x = bounds_2x.max_x - bounds_2x.min_x + 1
        height_2x = bounds_2x.max_y - bounds_2x.min_y + 1

        # At 2x zoom, visible area should be roughly half in each dimension
        assert width_2x <= width_1x // 2 + 1  # +1 for rounding
        assert height_2x <= height_1x // 2 + 1

        # At 4x zoom, even fewer world cells visible
        viewer.zoom = 4
        bounds_4x = viewer.get_visible_bounds()
        width_4x = bounds_4x.max_x - bounds_4x.min_x + 1
        height_4x = bounds_4x.max_y - bounds_4x.min_y + 1

        assert width_4x <= width_2x // 2 + 1
        assert height_4x <= height_2x // 2 + 1


class TestParameterPanel:
    """Tests for ParameterPanel widget."""

    def test_parameter_panel_initialization(self):
        """Test ParameterPanel can be initialized with TerrainConfig."""
        config = TerrainConfig(seed=12345)

        from hamlet.tui.parameter_panel import ParameterPanel
        panel = ParameterPanel(config)

        assert panel._config is config
        assert panel._selected_index == 0

    def test_parameter_panel_current_seed(self):
        """Test current_seed property returns correct seed."""
        config = TerrainConfig(seed=42)

        from hamlet.tui.parameter_panel import ParameterPanel
        panel = ParameterPanel(config)

        assert panel.current_seed == 42

    def test_parameter_panel_current_seed_none(self):
        """Test current_seed property when seed is None."""
        config = TerrainConfig(seed=None)

        from hamlet.tui.parameter_panel import ParameterPanel
        panel = ParameterPanel(config)

        # Should return 0 when seed is None
        assert panel.current_seed == 0

    def test_parameter_panel_navigation(self):
        """Test parameter navigation actions."""
        config = TerrainConfig(seed=12345)

        from hamlet.tui.parameter_panel import ParameterPanel
        panel = ParameterPanel(config)

        # Start at index 0
        assert panel._selected_index == 0

        # Move down
        panel.action_next_param()
        assert panel._selected_index == 1

        # Move back up
        panel.action_prev_param()
        assert panel._selected_index == 0

    def test_parameter_panel_adjustment(self):
        """Test parameter adjustment actions."""
        config = TerrainConfig(seed=12345, smoothing_passes=4)

        from hamlet.tui.parameter_panel import ParameterPanel
        panel = ParameterPanel(config)

        # Find smoothing_passes parameter index
        smoothing_index = None
        for i, (name, *_) in enumerate(panel._params):
            if name == "smoothing_passes":
                smoothing_index = i
                break

        assert smoothing_index is not None, "smoothing_passes parameter not found"
        panel._selected_index = smoothing_index

        original = config.smoothing_passes
        panel.action_increase()
        assert config.smoothing_passes == original + 1

        panel.action_decrease()
        assert config.smoothing_passes == original

    def test_parameter_panel_callbacks(self):
        """Test callback invocation on parameter changes."""
        config = TerrainConfig(seed=12345)
        change_called = []
        save_called = []
        seed_change_called = []

        from hamlet.tui.parameter_panel import ParameterPanel
        panel = ParameterPanel(
            config,
            on_change=lambda c, n, v: change_called.append((n, v)),
            on_save=lambda c: save_called.append(c),
            on_seed_change=lambda: seed_change_called.append(True),
        )

        # Test save callback
        panel.action_save()
        assert len(save_called) == 1

        # Test seed change callback
        panel.action_randomize_seed()
        assert len(seed_change_called) == 1

    def test_parameter_panel_update_config(self):
        """Test update_config refreshes the panel."""
        config1 = TerrainConfig(seed=12345)
        config2 = TerrainConfig(seed=99999)

        from hamlet.tui.parameter_panel import ParameterPanel
        panel = ParameterPanel(config1)

        assert panel._config.seed == 12345

        panel.update_config(config2)
        assert panel._config.seed == 99999


class TestMapApp:
    """Tests for MapApp TUI application."""

    def test_map_app_initialization_default_config(self):
        """Test MapApp initializes with default TerrainConfig."""
        from hamlet.tui.map_app import MapApp
        app = MapApp()

        assert app._config is not None
        assert app._config.seed is not None

    def test_map_app_initialization_custom_config(self):
        """Test MapApp initializes with custom TerrainConfig."""
        config = TerrainConfig(seed=42, smoothing_passes=10)
        from hamlet.tui.map_app import MapApp
        app = MapApp(config=config)

        assert app._config.seed == 42
        assert app._config.smoothing_passes == 10

    def test_map_app_seed_change(self):
        """Test seed change regenerates terrain."""
        from hamlet.tui.map_app import MapApp
        app = MapApp()

        original_seed = app._config.seed
        app._on_seed_change()

        # Seed should have changed
        assert app._config.seed != original_seed
        # Generator should be recreated
        assert app._generator.seed == app._config.seed

    def test_map_app_param_change(self):
        """Test parameter change preserves seed."""
        from hamlet.tui.map_app import MapApp
        from dataclasses import replace
        app = MapApp()

        original_seed = app._config.seed
        original_smoothing = app._config.smoothing_passes

        # Create a new config with updated smoothing_passes
        new_config = replace(app._config, smoothing_passes=original_smoothing + 2)

        # Change parameter
        app._on_param_change(new_config, "smoothing_passes", original_smoothing + 2)

        # Seed should be preserved
        assert app._config.seed == original_seed
        # Smoothing should be updated
        assert app._config.smoothing_passes == original_smoothing + 2