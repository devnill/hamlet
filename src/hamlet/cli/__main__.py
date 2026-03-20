"""Entry point for running hamlet.cli as a module."""
from __future__ import annotations

import sys

from hamlet.cli import main

if __name__ == "__main__":
    sys.exit(main())
