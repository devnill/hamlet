"""Settings configuration for Hamlet.

Config file format (~/.hamlet/config.json):
{
    "db_path": "~/.hamlet/world.db",
    "mcp_port": 8080,
    "tick_rate": 30.0,
    "theme": "default",
    "event_log_max_entries": 1000,
    "activity_model": "claude-haiku-4-5-20251001",
    "zombie_despawn_seconds": 300,
    "zombie_threshold_seconds": 300,
    "min_village_distance": 15,
    "renderer": "auto",
    "terrain": {
        "seed": null,
        "world_size": 200,
        "water_frequency": 0.02,
        "mountain_frequency": 0.015,
        "forest_threshold": 0.55,
        "meadow_threshold": 0.1,
        "water_threshold": -0.25,
        "mountain_threshold": 0.75,
        "octaves": 4,
        "lacunarity": 2.0,
        "persistence": 0.5,
        "elevation_scale": 0.03,
        "moisture_scale": 0.04,
        "domain_warp_strength": 0.5,
        "smoothing_passes": 4,
        "forest_grove_count": 15,
        "forest_growth_iterations": 8,
        "min_lake_size": 10,
        "lake_expansion_factor": 1.5,
        "ridge_count": null
    }
}

Note: The terrain object accepts many additional parameters (region_scale,
region_blending, river_count, pond_count, min_pond_size, max_pond_size,
water_percentage_target, forest_water_adjacency_bonus,
forest_region_bias_strength, forest_percentage_target, and more).
See TerrainConfig in src/hamlet/world_state/terrain.py for the full list
with defaults and descriptions.
"""

import json
from dataclasses import dataclass, asdict, fields, field
from pathlib import Path
from typing import Optional, Any

from .paths import CONFIG_PATH, ensure_hamlet_dir


@dataclass
class Settings:
    """Application settings with sensible defaults."""

    db_path: str = "~/.hamlet/world.db"
    mcp_port: int = 8080
    tick_rate: float = 30.0
    theme: str = "default"
    event_log_max_entries: int = 1000
    activity_model: str = "claude-haiku-4-5-20251001"
    zombie_despawn_seconds: int = 300
    zombie_threshold_seconds: int = 300
    min_village_distance: int = 15
    renderer: str = "auto"
    # Terrain configuration as dict for JSON serialization
    # Actual TerrainConfig is constructed from this in app_factory
    terrain: dict[str, Any] = field(default_factory=dict)

    def _validate(self) -> None:
        """Validate settings values, raising ValueError for invalid fields.

        Raises:
            ValueError: If any field value fails validation, with a message
                indicating the field name, constraint, and actual value.
        """
        if not isinstance(self.db_path, str) or not self.db_path:
            raise ValueError(
                f"db_path must be a non-empty string, got: {self.db_path!r}"
            )
        if isinstance(self.mcp_port, bool) or not isinstance(self.mcp_port, int):
            raise ValueError(
                f"mcp_port must be an integer, got: {self.mcp_port!r}"
            )
        if not (1 <= self.mcp_port <= 65535):
            raise ValueError(
                f"mcp_port must be between 1 and 65535, got: {self.mcp_port!r}"
            )
        if not isinstance(self.activity_model, str) or not self.activity_model:
            raise ValueError(
                f"activity_model must be a non-empty string, got: {self.activity_model!r}"
            )
        if (
            isinstance(self.zombie_threshold_seconds, bool)
            or not isinstance(self.zombie_threshold_seconds, int)
        ):
            raise ValueError(
                f"zombie_threshold_seconds must be an integer, got: {self.zombie_threshold_seconds!r}"
            )
        if self.zombie_threshold_seconds <= 0:
            raise ValueError(
                f"zombie_threshold_seconds must be > 0, got: {self.zombie_threshold_seconds!r}"
            )
        if isinstance(self.min_village_distance, bool) or not isinstance(self.min_village_distance, int):
            raise ValueError(
                f"min_village_distance must be an integer, got: {self.min_village_distance!r}"
            )
        if self.min_village_distance <= 0:
            raise ValueError(
                f"min_village_distance must be > 0, got: {self.min_village_distance!r}"
            )
        valid_renderers = {"auto", "textual", "kitty"}
        if self.renderer not in valid_renderers:
            raise ValueError(
                f"renderer must be one of {sorted(valid_renderers)}, got: {self.renderer!r}"
            )
        # terrain is a dict, validation of its contents happens in TerrainConfig

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from config file or create defaults.

        Returns:
            Settings instance loaded from file or with default values.

        Raises:
            ValueError: If loaded or default settings fail validation.
        """
        ensure_hamlet_dir()
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text())
            known = {f.name for f in fields(cls)}
            settings = cls(**{k: v for k, v in data.items() if k in known})
            settings._validate()
            return settings
        # Create defaults
        settings = cls()
        settings._validate()
        settings.save()
        return settings

    def diff(self, other: "Settings") -> dict[str, tuple[Any, Any]]:
        """Return {field_name: (old_value, new_value)} for fields that differ."""
        changes = {}
        for f in fields(self.__class__):
            old = getattr(self, f.name)
            new = getattr(other, f.name)
            if old != new:
                changes[f.name] = (old, new)
        return changes

    def save(self) -> None:
        """Persist settings to config file."""
        ensure_hamlet_dir()
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2))