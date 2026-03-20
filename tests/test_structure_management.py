"""Tests for structure management methods in WorldStateManager (work item 037).

Run with: pytest tests/test_structure_management.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from hamlet.world_state.manager import MATERIAL_STAGES, STAGE_THRESHOLDS, WorldStateManager
from hamlet.world_state.types import (
    AgentState,
    AgentType,
    Bounds,
    Position,
    StructureType,
    Village,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_persistence() -> MagicMock:
    p = MagicMock()
    p.queue_write = AsyncMock()
    p.load_state = AsyncMock()
    return p


async def _seeded_manager(village_id: str = "v1") -> WorldStateManager:
    """Return a WorldStateManager with one village pre-seeded."""
    p = _make_persistence()
    wsm = WorldStateManager(p)
    wsm._state.villages[village_id] = Village(
        id=village_id,
        project_id="proj-1",
        name="test-village",
        center=Position(0, 0),
        bounds=Bounds(0, 0, 0, 0),
    )
    return wsm


# ---------------------------------------------------------------------------
# STAGE_THRESHOLDS / MATERIAL_STAGES constants
# ---------------------------------------------------------------------------


def test_stage_thresholds_has_all_structure_types():
    expected = {"house", "workshop", "library", "forge", "tower", "road", "well"}
    assert set(STAGE_THRESHOLDS.keys()) == expected


def test_stage_thresholds_each_has_three_entries():
    for name, thresholds in STAGE_THRESHOLDS.items():
        assert len(thresholds) == 3, f"{name} does not have 3 thresholds"


def test_material_stages_maps_all_four_stages():
    assert MATERIAL_STAGES == {0: "wood", 1: "wood", 2: "stone", 3: "brick"}


# ---------------------------------------------------------------------------
# create_structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_structure_returns_structure_with_correct_initial_state():
    wsm = await _seeded_manager()
    s = await wsm.create_structure("v1", StructureType.HOUSE, Position(1, 1))

    assert s.village_id == "v1"
    assert s.type == StructureType.HOUSE
    assert s.position == Position(1, 1)
    assert s.stage == 0
    assert s.material == MATERIAL_STAGES[0]  # "wood"
    assert s.work_units == 0
    assert s.work_required == STAGE_THRESHOLDS["house"][0]


@pytest.mark.asyncio
async def test_create_structure_added_to_village_structure_ids():
    wsm = await _seeded_manager()
    s = await wsm.create_structure("v1", StructureType.WORKSHOP, Position(2, 2))
    village = wsm._state.villages["v1"]
    assert s.id in village.structure_ids


@pytest.mark.asyncio
async def test_create_structure_queues_persistence_write():
    p = _make_persistence()
    wsm = WorldStateManager(p)
    wsm._state.villages["v1"] = Village(
        id="v1", project_id="p1", name="v",
        center=Position(0, 0), bounds=Bounds(0, 0, 0, 0),
    )
    s = await wsm.create_structure("v1", StructureType.WELL, Position(3, 3))
    p.queue_write.assert_awaited_once_with("structure", s.id, s)


# ---------------------------------------------------------------------------
# get_structure / get_structures_by_village
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_structure_returns_structure():
    wsm = await _seeded_manager()
    s = await wsm.create_structure("v1", StructureType.FORGE, Position(0, 1))
    result = await wsm.get_structure(s.id)
    assert result is s


@pytest.mark.asyncio
async def test_get_structure_returns_none_for_unknown_id():
    wsm = await _seeded_manager()
    assert await wsm.get_structure("nonexistent") is None


@pytest.mark.asyncio
async def test_get_structures_by_village_returns_all():
    wsm = await _seeded_manager()
    s1 = await wsm.create_structure("v1", StructureType.HOUSE, Position(0, 1))
    s2 = await wsm.create_structure("v1", StructureType.LIBRARY, Position(1, 0))
    results = await wsm.get_structures_by_village("v1")
    assert {r.id for r in results} == {s1.id, s2.id}


# ---------------------------------------------------------------------------
# add_work_units — stage advancement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_work_units_increments_agent_total():
    import uuid
    from datetime import UTC, datetime
    from hamlet.world_state.types import Agent

    p = _make_persistence()
    wsm = WorldStateManager(p)
    wsm._state.villages["v1"] = Village(
        id="v1", project_id="p1", name="v",
        center=Position(0, 0), bounds=Bounds(0, 0, 0, 0),
    )
    s = await wsm.create_structure("v1", StructureType.HOUSE, Position(0, 0))
    now = datetime.now(UTC)
    agent_id = str(uuid.uuid4())
    agent = Agent(
        id=agent_id, session_id="sess", project_id="p1",
        village_id="v1", position=Position(0, 0),
        state=AgentState.ACTIVE, inferred_type=AgentType.GENERAL,
        color="white", last_seen=now, created_at=now, updated_at=now,
    )
    wsm._state.agents[agent_id] = agent
    wsm._state.villages["v1"].agent_ids.append(agent_id)

    await wsm.add_work_units(agent_id, StructureType.HOUSE, 50)
    assert agent.total_work_units == 50


@pytest.mark.asyncio
async def test_add_work_units_advances_stage_at_threshold():
    import uuid
    from datetime import UTC, datetime
    from hamlet.world_state.types import Agent

    p = _make_persistence()
    wsm = WorldStateManager(p)
    wsm._state.villages["v1"] = Village(
        id="v1", project_id="p1", name="v",
        center=Position(0, 0), bounds=Bounds(0, 0, 0, 0),
    )
    s = await wsm.create_structure("v1", StructureType.HOUSE, Position(0, 0))
    threshold = STAGE_THRESHOLDS["house"][0]  # 100

    now = datetime.now(UTC)
    agent_id = str(uuid.uuid4())
    agent = Agent(
        id=agent_id, session_id="sess", project_id="p1",
        village_id="v1", position=Position(0, 0),
        state=AgentState.ACTIVE, inferred_type=AgentType.GENERAL,
        color="white", last_seen=now, created_at=now, updated_at=now,
    )
    wsm._state.agents[agent_id] = agent
    wsm._state.villages["v1"].agent_ids.append(agent_id)

    await wsm.add_work_units(agent_id, StructureType.HOUSE, threshold)
    assert s.stage == 1
    assert s.work_units == 0  # reset on advancement
    assert s.material == MATERIAL_STAGES[1]  # "wood" at stage 1


@pytest.mark.asyncio
async def test_add_work_units_stage_3_does_not_accumulate():
    """work_units must not grow unboundedly on a fully-built structure."""
    import uuid
    from datetime import UTC, datetime
    from hamlet.world_state.types import Agent

    p = _make_persistence()
    wsm = WorldStateManager(p)
    wsm._state.villages["v1"] = Village(
        id="v1", project_id="p1", name="v",
        center=Position(0, 0), bounds=Bounds(0, 0, 0, 0),
    )
    s = await wsm.create_structure("v1", StructureType.HOUSE, Position(0, 0))
    s.stage = 3
    s.work_units = 0
    s.work_required = 0

    now = datetime.now(UTC)
    agent_id = str(uuid.uuid4())
    agent = Agent(
        id=agent_id, session_id="sess", project_id="p1",
        village_id="v1", position=Position(0, 0),
        state=AgentState.ACTIVE, inferred_type=AgentType.GENERAL,
        color="white", last_seen=now, created_at=now, updated_at=now,
    )
    wsm._state.agents[agent_id] = agent
    wsm._state.villages["v1"].agent_ids.append(agent_id)

    await wsm.add_work_units(agent_id, StructureType.HOUSE, 500)
    assert s.work_units == 0  # must not accumulate


@pytest.mark.asyncio
async def test_add_work_units_material_advances_to_stone_at_stage_2():
    import uuid
    from datetime import UTC, datetime
    from hamlet.world_state.types import Agent

    p = _make_persistence()
    wsm = WorldStateManager(p)
    wsm._state.villages["v1"] = Village(
        id="v1", project_id="p1", name="v",
        center=Position(0, 0), bounds=Bounds(0, 0, 0, 0),
    )
    s = await wsm.create_structure("v1", StructureType.HOUSE, Position(0, 0))
    # Fast-forward to stage 1 to set up stage 1→2 transition
    s.stage = 1
    s.material = MATERIAL_STAGES[1]
    s.work_units = 0
    s.work_required = STAGE_THRESHOLDS["house"][1]

    now = datetime.now(UTC)
    agent_id = str(uuid.uuid4())
    agent = Agent(
        id=agent_id, session_id="sess", project_id="p1",
        village_id="v1", position=Position(0, 0),
        state=AgentState.ACTIVE, inferred_type=AgentType.GENERAL,
        color="white", last_seen=now, created_at=now, updated_at=now,
    )
    wsm._state.agents[agent_id] = agent
    wsm._state.villages["v1"].agent_ids.append(agent_id)

    threshold_1_to_2 = STAGE_THRESHOLDS["house"][1]  # 500
    await wsm.add_work_units(agent_id, StructureType.HOUSE, threshold_1_to_2)
    assert s.stage == 2
    assert s.material == "stone"
