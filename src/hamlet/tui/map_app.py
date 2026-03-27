"""Map Viewer TUI application for terrain exploration and parameter adjustment."""
from __future__ import annotations

import random
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static
from textual.containers import Horizontal

from hamlet.world_state.terrain import TerrainConfig, TerrainGenerator, TerrainGrid
from hamlet.config.settings import Settings
from hamlet.tui.legend import LegendOverlay
from hamlet.tui.map_viewer import MapViewer
from hamlet.tui.parameter_panel import ParameterPanel

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

__all__ = ["MapApp", "StatusBar"]


class StatusBar(Static):
    """Status bar showing current zoom level and other info."""

    def __init__(self) -> None:
        """Initialize the status bar."""
        super().__init__()
        self._zoom_level = 1

    def update_zoom(self, zoom_level: int) -> None:
        """Update the displayed zoom level."""
        self._zoom_level = zoom_level
        self.refresh()

    def render(self):
        """Render the status bar."""
        from rich.text import Text
        text = Text()
        text.append(f"Zoom: {self._zoom_level}x", style="bold white")
        text.append("  |  ", style="dim white")
        text.append("+/- to zoom, arrows/hjkl to scroll, r to randomize", style="dim white")
        return text


class MapApp(App):
    """Map viewer TUI application.

    Provides terrain visualization without agents/structures, with a side panel
    for adjusting terrain generation parameters. Changes preserve the seed
    unless explicitly randomized.
    """

    LAYERS = ("default", "overlay")

    CSS = """
    Screen {
        layout: horizontal;
    }

    MapViewer {
        width: 1fr;
    }

    ParameterPanel {
        width: 32;
    }

    StatusBar {
        dock: bottom;
        height: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("h", "scroll_left", "Scroll Left", show=False),
        Binding("left", "scroll_left", "Scroll Left", show=False),
        Binding("l", "scroll_right", "Scroll Right", show=False),
        Binding("right", "scroll_right", "Scroll Right", show=False),
        Binding("j", "scroll_down", "Scroll Down", show=False),
        Binding("down", "scroll_down", "Scroll Down", show=False),
        Binding("k", "scroll_up", "Scroll Up", show=False),
        Binding("up", "scroll_up", "Scroll Up", show=False),
        Binding("r", "randomize_seed", "Random Seed", show=True),
        Binding("s", "save", "Save", show=True),
        Binding("/", "toggle_legend", "Legend", show=True),
        Binding("?", "toggle_help", "Help", show=True),
        Binding("plus", "zoom_in", "Zoom In", show=True),
        Binding("equal", "zoom_in", "Zoom In", show=False),
        Binding("minus", "zoom_out", "Zoom Out", show=True),
        Binding("zero", "reset_zoom", "Reset Zoom", show=False),
    ]

    def __init__(
        self,
        config: TerrainConfig | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the map viewer application.

        Args:
            config: TerrainConfig to use. If None, creates from settings or defaults.
            settings: Settings instance for persistence. If None, loads from file.
        """
        super().__init__()
        self._settings = settings or Settings.load()

        # Build or use provided TerrainConfig
        if config:
            self._config = config
        elif self._settings.terrain:
            self._config = TerrainConfig(**self._settings.terrain)
        else:
            self._config = TerrainConfig()

        # Ensure seed is set
        if self._config.seed is None:
            self._config = TerrainConfig(
                seed=random.randint(0, 2**31 - 1),
                **{k: v for k, v in asdict(self._config).items() if k != "seed"}
            )

        # Initialize terrain generation components
        self._generator = TerrainGenerator(self._config)
        self._terrain_grid: TerrainGrid | None = None

        # Track unsaved changes
        self._dirty = False

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        # Create terrain grid with current config
        self._terrain_grid = TerrainGrid(self._generator)

        # Create map viewer and parameter panel
        yield MapViewer(self._terrain_grid)
        yield ParameterPanel(
            self._config,
            on_change=self._on_param_change,
            on_save=self._on_save,
            on_seed_change=self._on_seed_change,
        )
        yield StatusBar()
        yield LegendOverlay()

    def on_mount(self) -> None:
        """Set up periodic refresh after mounting."""
        self.set_interval(1 / 30, self._refresh_display)

    def _refresh_display(self) -> None:
        """Refresh the map display."""
        try:
            map_viewer = self.query_one(MapViewer)
            map_viewer.refresh()
        except Exception as exc:
            logger.debug("_refresh_display: %s", exc)

    # ------------------------------------------------------------------
    # Parameter change callbacks
    # ------------------------------------------------------------------

    def _on_param_change(
        self,
        config: TerrainConfig,
        param_name: str,
        new_value: int | float,
    ) -> None:
        """Handle parameter change from the panel.

        Regenerates terrain with the same seed but new parameter values.

        Args:
            config: The updated TerrainConfig.
            param_name: Name of the changed parameter.
            new_value: The new parameter value.
        """
        self._config = config
        self._dirty = True

        # Re-create generator with updated config (preserving seed)
        self._generator = TerrainGenerator(self._config)

        # Re-create terrain grid to clear cache
        self._terrain_grid = TerrainGrid(self._generator)

        # Update the map viewer
        try:
            map_viewer = self.query_one(MapViewer)
            map_viewer._terrain_grid = self._terrain_grid
            map_viewer.refresh()
        except Exception as exc:
            logger.warning("Failed to update map viewer: %s", exc)

        # Update the parameter panel
        try:
            panel = self.query_one(ParameterPanel)
            panel.update_config(self._config)
        except Exception as exc:
            logger.warning("Failed to update parameter panel: %s", exc)

    def _on_seed_change(self) -> None:
        """Handle seed randomization request.

        Generates a new random seed and regenerates terrain.
        """
        new_seed = random.randint(0, 2**31 - 1)

        # Create new config with new seed
        config_dict = {
            k: v for k, v in asdict(self._config).items()
            if k != "seed"
        }
        config_dict["seed"] = new_seed
        self._config = TerrainConfig(**config_dict)

        # Re-create generator
        self._generator = TerrainGenerator(self._config)

        # Re-create terrain grid
        self._terrain_grid = TerrainGrid(self._generator)

        # Update displays
        self._dirty = True
        try:
            map_viewer = self.query_one(MapViewer)
            map_viewer._terrain_grid = self._terrain_grid
            map_viewer.refresh()
        except Exception:
            pass

        try:
            panel = self.query_one(ParameterPanel)
            panel.update_config(self._config)
        except Exception:
            pass

    def _on_save(self, config: TerrainConfig) -> None:
        """Handle save request.

        Persists the current terrain configuration to the settings file.

        Args:
            config: The TerrainConfig to save.
        """
        # Update settings terrain dict
        config_dict = asdict(config)
        self._settings.terrain = config_dict
        self._settings.save()

        self._dirty = False
        logger.info("Saved terrain configuration to ~/.hamlet/config.json")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_scroll_left(self) -> None:
        """Scroll the viewport left by one cell."""
        try:
            map_viewer = self.query_one(MapViewer)
            map_viewer.scroll(-1, 0)
        except Exception as exc:
            logger.debug("scroll_left: %s", exc)

    def action_scroll_right(self) -> None:
        """Scroll the viewport right by one cell."""
        try:
            map_viewer = self.query_one(MapViewer)
            map_viewer.scroll(1, 0)
        except Exception as exc:
            logger.debug("scroll_right: %s", exc)

    def action_scroll_up(self) -> None:
        """Scroll the viewport up by one cell."""
        try:
            map_viewer = self.query_one(MapViewer)
            map_viewer.scroll(0, -1)
        except Exception as exc:
            logger.debug("scroll_up: %s", exc)

    def action_scroll_down(self) -> None:
        """Scroll the viewport down by one cell."""
        try:
            map_viewer = self.query_one(MapViewer)
            map_viewer.scroll(0, 1)
        except Exception as exc:
            logger.debug("scroll_down: %s", exc)

    def action_randomize_seed(self) -> None:
        """Randomize the terrain seed."""
        self._on_seed_change()

    def action_save(self) -> None:
        """Save the current configuration."""
        self._on_save(self._config)

    def action_toggle_legend(self) -> None:
        """Toggle the legend overlay visibility."""
        try:
            overlay = self.query_one(LegendOverlay)
            overlay.display = not overlay.display
        except Exception as exc:
            logger.debug("toggle_legend: %s", exc)

    def action_toggle_help(self) -> None:
        """Toggle the help overlay."""
        pass

    def action_zoom_in(self) -> None:
        """Increase zoom level."""
        try:
            map_viewer = self.query_one(MapViewer)
            map_viewer.zoom_in()
            self._update_status_bar()
        except Exception as exc:
            logger.debug("zoom_in: %s", exc)

    def action_zoom_out(self) -> None:
        """Decrease zoom level."""
        try:
            map_viewer = self.query_one(MapViewer)
            map_viewer.zoom_out()
            self._update_status_bar()
        except Exception as exc:
            logger.debug("zoom_out: %s", exc)

    def action_reset_zoom(self) -> None:
        """Reset zoom level to 1x."""
        try:
            map_viewer = self.query_one(MapViewer)
            map_viewer.reset_zoom()
            self._update_status_bar()
        except Exception as exc:
            logger.debug("reset_zoom: %s", exc)

    def _update_status_bar(self) -> None:
        """Update the status bar with current zoom level."""
        try:
            map_viewer = self.query_one(MapViewer)
            status_bar = self.query_one(StatusBar)
            status_bar.update_zoom(map_viewer.zoom_level)
        except Exception as exc:
            logger.debug("update_status_bar: %s", exc)

    async def run_async(self, **kwargs: object) -> None:
        """Start the Map TUI application asynchronously."""
        await super().run_async(**kwargs)