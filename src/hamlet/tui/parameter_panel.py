"""ParameterPanel widget — terrain configuration adjustment for map viewer mode."""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Callable

from textual.widgets import Static
from textual.containers import Vertical
from textual.binding import Binding

if TYPE_CHECKING:
    from hamlet.world_state.terrain import TerrainConfig

_log = logging.getLogger(__name__)

__all__ = ["ParameterPanel"]


# Parameter definitions: (name, display_name, min_val, max_val, step, description)
TERRAIN_PARAMS = [
    ("elevation_scale", "Elevation Scale", 0.01, 0.2, 0.01, "Scale for elevation noise"),
    ("moisture_scale", "Moisture Scale", 0.01, 0.2, 0.01, "Scale for moisture noise"),
    ("domain_warp_strength", "Domain Warp", 0.0, 2.0, 0.1, "Terrain distortion strength"),
    ("smoothing_passes", "Smoothing", 0, 10, 1, "CA smoothing iterations"),
    ("forest_grove_count", "Forest Groves", 0, 50, 1, "Number of forest grove seeds"),
    ("forest_growth_iterations", "Forest Growth", 0, 20, 1, "Growth iterations per grove"),
    ("min_lake_size", "Min Lake Size", 1, 50, 1, "Minimum water cells for lakes"),
    ("lake_expansion_factor", "Lake Expansion", 1.0, 3.0, 0.1, "Lake expansion multiplier"),
    ("octaves", "Noise Octaves", 1, 8, 1, "Number of noise layers"),
    ("lacunarity", "Lacunarity", 1.0, 4.0, 0.1, "Frequency multiplier per octave"),
    ("persistence", "Persistence", 0.1, 1.0, 0.1, "Amplitude decay per octave"),
    ("water_threshold", "Water Threshold", -1.0, 0.5, 0.05, "Elevation threshold for water"),
    ("mountain_threshold", "Mountain Threshold", 0.3, 1.0, 0.05, "Elevation threshold for mountains"),
    ("forest_threshold", "Forest Threshold", 0.0, 1.0, 0.05, "Moisture threshold for forest"),
    ("meadow_threshold", "Meadow Threshold", -1.0, 0.5, 0.05, "Moisture threshold for meadow"),
    ("region_scale", "Region Scale", 50.0, 200.0, 10.0, "Biome region size (cells)"),
    ("region_blending", "Region Blend", 0.0, 1.0, 0.1, "Biome transition sharpness"),
    ("river_count", "Rivers", 0, 10, 1, "Number of rivers (0=auto)"),
    ("pond_count", "Ponds", 0, 20, 1, "Number of ponds (0=auto)"),
    ("min_pond_size", "Min Pond", 3, 10, 1, "Minimum pond cells"),
    ("max_pond_size", "Max Pond", 10, 30, 1, "Maximum pond cells"),
    ("water_percentage_target", "Water %", 0.0, 50.0, 1.0, "Target water coverage"),
    ("forest_water_adjacency_bonus", "Water Bonus", 0.0, 1.0, 0.1, "Forest spawn bonus near water"),
    ("forest_region_bias_strength", "Forest Bias", 0.0, 1.0, 0.1, "Regional forest density bias"),
    ("forest_percentage_target", "Forest %", 0.0, 50.0, 1.0, "Target forest coverage"),
]


class ParameterPanel(Static):
    """Side panel displaying and editing terrain configuration parameters.

    Provides a list of terrain parameters with controls to adjust them.
    Changes trigger terrain regeneration with the same seed.
    """

    DEFAULT_CSS = """
    ParameterPanel {
        width: 32;
        height: 100%;
        dock: right;
        background: $surface;
        border-left: solid $primary;
    }
    """

    BINDINGS = [
        Binding("up", "prev_param", "Previous", show=False),
        Binding("down", "next_param", "Next", show=False),
        Binding("left", "decrease", "Decrease", show=False),
        Binding("right", "increase", "Increase", show=False),
        Binding("r", "randomize_seed", "Random Seed", show=True),
        Binding("s", "save", "Save", show=True),
    ]

    def __init__(
        self,
        terrain_config: "TerrainConfig",
        on_change: Callable | None = None,
        on_save: Callable | None = None,
        on_seed_change: Callable | None = None,
    ) -> None:
        """Initialize the parameter panel.

        Args:
            terrain_config: The TerrainConfig to display and edit.
            on_change: Callback when a parameter changes (config, param_name, new_value).
            on_save: Callback when save is requested.
            on_seed_change: Callback when seed randomization is requested.
        """
        super().__init__()
        self._config = terrain_config
        self._on_change = on_change
        self._on_save = on_save
        self._on_seed_change = on_seed_change
        self._selected_index = 0
        self._params = [(name, *rest) for name, *rest in TERRAIN_PARAMS]

    @property
    def current_seed(self) -> int:
        """Return the current seed value."""
        return self._config.seed if self._config.seed is not None else 0

    def render(self) -> str:
        """Render the parameter panel."""
        lines = []

        # Header with seed
        seed = self._config.seed if self._config.seed is not None else "random"
        lines.append(f"[bold]Terrain Parameters[/bold]")
        lines.append(f"[dim]Seed: {seed}[/dim]")
        lines.append("")

        # Parameter list
        for i, (name, display, min_val, max_val, step, desc) in enumerate(self._params):
            value = getattr(self._config, name, None)
            if value is None:
                value = "auto"

            # Highlight selected row
            if i == self._selected_index:
                prefix = "[bold cyan]►[/bold cyan] "
                style = "bold"
            else:
                prefix = "  "
                style = ""

            # Format value
            if isinstance(value, float):
                value_str = f"{value:.2f}"
            elif isinstance(value, int):
                value_str = str(value)
            else:
                value_str = str(value)

            lines.append(f"{prefix}[{style}]{display}[/{style}]: {value_str}")
            lines.append(f"    [dim]{desc}[/dim]")

        # Footer with controls
        lines.append("")
        lines.append("[dim]↑↓ Navigate  ←→ Adjust[/dim]")
        lines.append("[dim]R Random seed  S Save[/dim]")

        return "\n".join(lines)

    def action_prev_param(self) -> None:
        """Move selection to previous parameter."""
        if self._selected_index > 0:
            self._selected_index -= 1
            self.refresh()

    def action_next_param(self) -> None:
        """Move selection to next parameter."""
        if self._selected_index < len(self._params) - 1:
            self._selected_index += 1
            self.refresh()

    def action_decrease(self) -> None:
        """Decrease the selected parameter value."""
        self._adjust_param(-1)

    def action_increase(self) -> None:
        """Increase the selected parameter value."""
        self._adjust_param(1)

    def _adjust_param(self, direction: int) -> None:
        """Adjust the selected parameter by one step.

        Args:
            direction: -1 to decrease, 1 to increase.
        """
        if not self._params:
            return

        name, display, min_val, max_val, step, desc = self._params[self._selected_index]
        current = getattr(self._config, name)

        if current is None:
            # Handle None/auto values - set to midpoint
            if isinstance(min_val, int):
                new_value = (min_val + max_val) // 2
            else:
                new_value = (min_val + max_val) / 2
        else:
            new_value = current + (step * direction)

        # Clamp to range
        new_value = max(min_val, min(max_val, new_value))

        # Update config
        setattr(self._config, name, new_value)

        # Notify callback
        if self._on_change:
            self._on_change(self._config, name, new_value)

        self.refresh()

    def action_randomize_seed(self) -> None:
        """Request a new random seed."""
        if self._on_seed_change:
            self._on_seed_change()

    def action_save(self) -> None:
        """Request to save the current configuration."""
        if self._on_save:
            self._on_save(self._config)

    def update_config(self, config: "TerrainConfig") -> None:
        """Update the displayed configuration."""
        self._config = config
        self.refresh()