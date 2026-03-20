"""Simulation state dataclass."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class SimulationState:
    """Runtime state of the simulation engine."""
    tick_count: int = 0
    last_tick_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    running: bool = False


__all__ = ["SimulationState"]
