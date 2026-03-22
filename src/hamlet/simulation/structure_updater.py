"""Structure progression system for the Hamlet simulation.

Advances structures through build stages based on accumulated work units,
updating material type at each stage transition.
"""
from __future__ import annotations

from typing import Any

from hamlet.simulation.config import SimulationConfig
from hamlet.world_state.rules import STRUCTURE_RULES
from hamlet.world_state.types import Structure, StructureType

__all__ = ["StructureUpdater"]


class StructureUpdater:
    """Updates structure stages and materials based on accumulated work units."""

    def __init__(self, config: SimulationConfig) -> None:
        self._config = config

    def _compute_target_tier(self, structure: "Structure") -> int:
        """Return highest tier whose threshold <= structure.work_units."""
        thresholds = self._config.size_tier_thresholds
        target = 1
        for tier in sorted(thresholds.keys()):
            if structure.work_units >= thresholds[tier]:
                target = tier
        return target

    async def update_structures(self, structures: list[Structure], world_state: Any) -> None:
        """Advance structures whose work_units meet or exceed the current stage threshold."""
        for structure in structures:
            # Stage advancement: only for incomplete structures
            if structure.stage < 3:
                rules = STRUCTURE_RULES.get(structure.type)
                if rules is not None:
                    thresholds = rules["thresholds"]
                    if structure.stage < len(thresholds):
                        threshold = thresholds[structure.stage]
                        if structure.work_units >= threshold:
                            new_stage = structure.stage + 1
                            materials = rules["materials"]
                            new_material = materials[min(new_stage, len(materials) - 1)]
                            await world_state.update_structure(
                                structure.id,
                                stage=new_stage,
                                material=new_material,
                                work_units=0,
                            )

            # Size tier upgrade: applies to all structures
            target_tier = self._compute_target_tier(structure)
            if target_tier > structure.size_tier:
                await world_state.upgrade_structure_tier(structure.id, target_tier)
