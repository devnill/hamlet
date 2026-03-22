"""Tests for StructureUpdater (work item 083).

Test framework: pytest + pytest-asyncio.
Run with: pytest tests/test_structure_updater.py -v
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from hamlet.simulation.config import SimulationConfig
from hamlet.simulation.structure_updater import STRUCTURE_RULES, StructureUpdater
from hamlet.world_state.types import Position, Structure, StructureType


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def config() -> SimulationConfig:
    """Return a default simulation config."""
    return SimulationConfig()


@pytest.fixture
def updater(config: SimulationConfig) -> StructureUpdater:
    """Return a StructureUpdater with default config."""
    return StructureUpdater(config)


@pytest.fixture
def world_state() -> MagicMock:
    """Return a mock WorldStateManager."""
    ws = MagicMock()
    ws.update_structure = AsyncMock()
    ws.upgrade_structure_tier = AsyncMock()
    return ws


def _make_structure(
    structure_type: StructureType = StructureType.HOUSE,
    stage: int = 0,
    work_units: int = 0,
    material: str = "wood",
    size_tier: int = 1,
) -> Structure:
    """Create a Structure with given properties."""
    return Structure(
        id=str(uuid4()),
        village_id=str(uuid4()),
        type=structure_type,
        stage=stage,
        material=material,
        work_units=work_units,
        position=Position(0, 0),
        size_tier=size_tier,
    )


# -----------------------------------------------------------------------------
# Test Class: TestStructureUpdater
# -----------------------------------------------------------------------------

class TestStructureUpdater:
    """Tests for StructureUpdater stage advancement logic."""
    async def test_stage_advances_at_threshold(
        self, updater: StructureUpdater, world_state: MagicMock
    ) -> None:
        """test_stage_advances_at_threshold - Stage advances when work_units meets threshold."""
        # House threshold for stage 0 -> 1 is 100 work units
        structure = _make_structure(
            structure_type=StructureType.HOUSE,
            stage=0,
            work_units=100,
        )

        await updater.update_structures([structure], world_state)

        world_state.update_structure.assert_awaited_once()
        call_args = world_state.update_structure.await_args
        assert call_args is not None
        update_data = call_args.kwargs
        assert update_data["stage"] == 1
    async def test_material_updates_with_stage(
        self, updater: StructureUpdater, world_state: MagicMock
    ) -> None:
        """test_material_updates_with_stage - Material updates when stage advances."""
        # House: stage 0 -> 1, material changes from "wood" to "wood" (same for stage 1)
        # Actually per STRUCTURE_RULES: materials are ["wood", "wood", "stone", "brick"]
        # So stage 0 -> 1 should still be "wood", stage 1 -> 2 is "stone"
        structure = _make_structure(
            structure_type=StructureType.HOUSE,
            stage=0,
            work_units=100,
            material="wood",
        )

        await updater.update_structures([structure], world_state)

        call_args = world_state.update_structure.await_args
        assert call_args is not None
        update_data = call_args.kwargs
        assert update_data["stage"] == 1
        assert update_data["material"] == "wood"  # Stage 1 material for house
    async def test_stage_1_to_2_material_change(
        self, updater: StructureUpdater, world_state: MagicMock
    ) -> None:
        """Material changes from wood to stone when advancing from stage 1 to 2."""
        # House: stage 1 -> 2, material changes from "wood" to "stone"
        structure = _make_structure(
            structure_type=StructureType.HOUSE,
            stage=1,
            work_units=500,  # Threshold for stage 1 -> 2
            material="wood",
        )

        await updater.update_structures([structure], world_state)

        call_args = world_state.update_structure.await_args
        assert call_args is not None
        update_data = call_args.kwargs
        assert update_data["stage"] == 2
        assert update_data["material"] == "stone"
    async def test_work_units_reset_on_advance(
        self, updater: StructureUpdater, world_state: MagicMock
    ) -> None:
        """work_units is reset to 0 when stage advances."""
        structure = _make_structure(
            structure_type=StructureType.HOUSE,
            stage=0,
            work_units=150,  # Exceeds threshold
        )

        await updater.update_structures([structure], world_state)

        call_args = world_state.update_structure.await_args
        assert call_args is not None
        update_data = call_args.kwargs
        assert update_data["work_units"] == 0
    async def test_no_advance_below_threshold(
        self, updater: StructureUpdater, world_state: MagicMock
    ) -> None:
        """Stage does not advance when work_units is below threshold."""
        structure = _make_structure(
            structure_type=StructureType.HOUSE,
            stage=0,
            work_units=99,  # Just below threshold
        )

        await updater.update_structures([structure], world_state)

        world_state.update_structure.assert_not_awaited()

    async def test_stage_3_no_change(self, updater: StructureUpdater, world_state: MagicMock) -> None:
        """Stage 3 structure at max tier does not trigger any state changes."""
        structure = _make_structure(
            structure_type=StructureType.HOUSE,
            stage=3,
            work_units=9999,
            size_tier=4,  # Already at max tier — no upgrade triggered
        )

        await updater.update_structures([structure], world_state)

        world_state.update_structure.assert_not_awaited()
        world_state.upgrade_structure_tier.assert_not_awaited()
    async def test_different_structure_types(
        self, updater: StructureUpdater, world_state: MagicMock
    ) -> None:
        """Different structure types have different thresholds."""
        # Workshop: thresholds [150, 750, 1500]
        workshop = _make_structure(
            structure_type=StructureType.WORKSHOP,
            stage=0,
            work_units=150,  # Workshop threshold
        )

        await updater.update_structures([workshop], world_state)

        world_state.update_structure.assert_awaited_once()
        call_args = world_state.update_structure.await_args
        assert call_args is not None
        update_data = call_args.kwargs
        assert update_data["stage"] == 1
    async def test_library_stage_advance(
        self, updater: StructureUpdater, world_state: MagicMock
    ) -> None:
        """Library advances with its specific thresholds."""
        # Library: thresholds [200, 1000, 2000]
        library = _make_structure(
            structure_type=StructureType.LIBRARY,
            stage=0,
            work_units=200,
        )

        await updater.update_structures([library], world_state)

        world_state.update_structure.assert_awaited_once()
        call_args = world_state.update_structure.await_args
        assert call_args is not None
        update_data = call_args.kwargs
        assert update_data["stage"] == 1
    async def test_empty_structure_list(self, updater: StructureUpdater, world_state: MagicMock) -> None:
        """Empty structure list does nothing."""
        await updater.update_structures([], world_state)

        world_state.update_structure.assert_not_awaited()
    async def test_multiple_structures_some_advance(
        self, updater: StructureUpdater, world_state: MagicMock
    ) -> None:
        """Multiple structures with different work units update correctly."""
        ready_house = _make_structure(
            structure_type=StructureType.HOUSE,
            stage=0,
            work_units=100,  # Ready to advance
        )
        not_ready_house = _make_structure(
            structure_type=StructureType.HOUSE,
            stage=0,
            work_units=50,  # Not ready
        )

        await updater.update_structures([ready_house, not_ready_house], world_state)

        # Only ready_house should trigger an update
        assert world_state.update_structure.await_count == 1
        call_args = world_state.update_structure.await_args
        assert call_args is not None
        # Verify it was called for the ready house
        assert call_args[0][0] == ready_house.id
    async def test_stage_2_to_3_final_stage(
        self, updater: StructureUpdater, world_state: MagicMock
    ) -> None:
        """Stage 2 to 3 advances to final stage with brick material."""
        # House: stage 2 -> 3, material changes from "stone" to "brick"
        structure = _make_structure(
            structure_type=StructureType.HOUSE,
            stage=2,
            work_units=1000,  # Threshold for stage 2 -> 3
            material="stone",
        )

        await updater.update_structures([structure], world_state)

        call_args = world_state.update_structure.await_args
        assert call_args is not None
        update_data = call_args.kwargs
        assert update_data["stage"] == 3
        assert update_data["material"] == "brick"


# -----------------------------------------------------------------------------
# Test Class: TestComputeTargetTier
# -----------------------------------------------------------------------------

class TestComputeTargetTier:
    """Tests for StructureUpdater._compute_target_tier boundary conditions."""

    @pytest.mark.parametrize("work_units,expected_tier", [
        (0, 1),
        (499, 1),
        (500, 2),
        (1999, 2),
        (2000, 3),
        (4999, 3),
        (5000, 4),
        (10000, 4),
    ])
    def test_tier_boundaries(
        self, updater: StructureUpdater, work_units: int, expected_tier: int
    ) -> None:
        """_compute_target_tier returns correct tier at each boundary."""
        structure = _make_structure(work_units=work_units)
        assert updater._compute_target_tier(structure) == expected_tier


# -----------------------------------------------------------------------------
# Test Class: TestSizeTierUpgrade
# -----------------------------------------------------------------------------

class TestSizeTierUpgrade:
    """Tests for size tier upgrade logic in update_structures."""

    @pytest.fixture
    def world_state_with_tier(self) -> MagicMock:
        """Return a mock WorldStateManager with upgrade_structure_tier."""
        ws = MagicMock()
        ws.update_structure = AsyncMock()
        ws.upgrade_structure_tier = AsyncMock()
        return ws

    async def test_upgrade_called_when_tier_increases(
        self, updater: StructureUpdater, world_state_with_tier: MagicMock
    ) -> None:
        """upgrade_structure_tier is called with new tier when work_units crosses threshold."""
        # work_units=500 puts structure at tier 2, but size_tier=1
        structure = _make_structure(
            stage=3,  # Already complete so stage advancement is skipped
            work_units=500,
            size_tier=1,
        )

        await updater.update_structures([structure], world_state_with_tier)

        world_state_with_tier.upgrade_structure_tier.assert_awaited_once_with(
            structure.id, 2
        )

    async def test_upgrade_not_called_when_tier_already_at_target(
        self, updater: StructureUpdater, world_state_with_tier: MagicMock
    ) -> None:
        """upgrade_structure_tier is NOT called when size_tier already matches target."""
        # work_units=500 → target tier 2, size_tier already 2
        structure = _make_structure(
            stage=3,  # Already complete so stage advancement is skipped
            work_units=500,
            size_tier=2,
        )

        await updater.update_structures([structure], world_state_with_tier)

        world_state_with_tier.upgrade_structure_tier.assert_not_awaited()
