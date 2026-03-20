"""Path constants for Hamlet configuration."""

from pathlib import Path

HAMLET_DIR = Path.home() / ".hamlet"
CONFIG_PATH = HAMLET_DIR / "config.json"
DB_PATH = HAMLET_DIR / "world.db"


def ensure_hamlet_dir() -> None:
    """Ensure the Hamlet config directory exists."""
    HAMLET_DIR.mkdir(parents=True, exist_ok=True)
