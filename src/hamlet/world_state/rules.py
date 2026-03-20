"""Structure progression rules — single source of truth for stage thresholds and materials."""
from __future__ import annotations

from .types import StructureType

__all__ = ["STRUCTURE_RULES", "TOOL_TO_STRUCTURE"]

TOOL_TO_STRUCTURE: dict[str, StructureType] = {
    "Read": StructureType.LIBRARY,
    "Grep": StructureType.LIBRARY,
    "Glob": StructureType.LIBRARY,
    "Write": StructureType.WORKSHOP,
    "Edit": StructureType.WORKSHOP,
    "Bash": StructureType.FORGE,
}

STRUCTURE_RULES: dict[StructureType, dict] = {
    StructureType.HOUSE:     {"thresholds": [100, 500, 1000],   "materials": ["wood", "wood", "stone", "brick"]},
    StructureType.WORKSHOP:  {"thresholds": [150, 750, 1500],   "materials": ["wood", "wood", "stone", "brick"]},
    StructureType.LIBRARY:   {"thresholds": [200, 1000, 2000],  "materials": ["wood", "wood", "stone", "brick"]},
    StructureType.FORGE:     {"thresholds": [300, 1500, 3000],  "materials": ["wood", "wood", "stone", "brick"]},
    StructureType.TOWER:     {"thresholds": [500, 2500, 5000],  "materials": ["wood", "wood", "stone", "brick"]},
    StructureType.ROAD:      {"thresholds": [50, 200, 400],     "materials": ["wood", "wood", "stone", "brick"]},
    StructureType.WELL:      {"thresholds": [75, 300, 600],     "materials": ["wood", "wood", "stone", "brick"]},
}
