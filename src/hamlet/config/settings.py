"""Settings configuration for Hamlet."""

import json
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import Optional

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

    def save(self) -> None:
        """Persist settings to config file."""
        ensure_hamlet_dir()
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2))
