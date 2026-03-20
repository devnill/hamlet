"""Pytest configuration for the hamlet test suite."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src directory to Python path for imports
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))
