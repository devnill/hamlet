"""Configuration module for Hamlet."""

from .paths import HAMLET_DIR, CONFIG_PATH, DB_PATH, ensure_hamlet_dir
from .settings import Settings

__all__ = [
    "HAMLET_DIR",
    "CONFIG_PATH",
    "DB_PATH",
    "ensure_hamlet_dir",
    "Settings",
]
