"""Simulation configuration dataclass."""
from __future__ import annotations

from dataclasses import dataclass, field

# Re-exported so consumers can import STRUCTURE_RULES from hamlet.simulation.config
from hamlet.world_state.rules import STRUCTURE_RULES


@dataclass
class SimulationConfig:
    """Configuration for the simulation engine."""
    tick_rate: float = 30.0
    work_unit_scale: float = 1.0
    zombie_threshold: float = 300.0   # seconds before agent becomes zombie
    expansion_threshold: int = 20     # agents before village expands


__all__ = ["SimulationConfig", "STRUCTURE_RULES"]
