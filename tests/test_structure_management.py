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
    # Structure write + village bounds update (bounds expanded from 0,0,0,0 to include 3,3)
    assert p.queue_write.call_count == 2
    p.queue_write.assert_any_await("structure", s.id, s)
    p.queue_write.assert_any_await("village", "v1", wsm._state.villages["v1"])


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


# ---------------------------------------------------------------------------
# WI-293: pending work units for non-existent structures
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_work_units_accumulates_in_pending_pool_when_structure_missing():
    """When structure type doesn't exist, work units go to pending pool (WI-293)."""
    import uuid
    from datetime import UTC, datetime
    from hamlet.world_state.types import Agent

    p = _make_persistence()
    wsm = WorldStateManager(p)
    wsm._state.villages["v1"] = Village(
        id="v1", project_id="p1", name="v",
        center=Position(0, 0), bounds=Bounds(0, 0, 0, 0),
    )
    # No structures created — LIBRARY doesn't exist in village

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

    # Add work units for LIBRARY which doesn't exist
    await wsm.add_work_units(agent_id, StructureType.LIBRARY, 200)

    # Agent's total_work_units should still be updated
    assert agent.total_work_units == 200

    # Pending pool should have the units
    assert "v1" in wsm._state.pending_work_units
    assert StructureType.LIBRARY in wsm._state.pending_work_units["v1"]
    assert wsm._state.pending_work_units["v1"][StructureType.LIBRARY] == 200


@pytest.mark.asyncio
async def test_add_work_units_accumulates_multiple_calls_in_pending_pool():
    """Multiple calls accumulate pending work units correctly (WI-293)."""
    import uuid
    from datetime import UTC, datetime
    from hamlet.world_state.types import Agent

    p = _make_persistence()
    wsm = WorldStateManager(p)
    wsm._state.villages["v1"] = Village(
        id="v1", project_id="p1", name="v",
        center=Position(0, 0), bounds=Bounds(0, 0, 0, 0),
    )

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

    # Multiple calls add to pending pool
    await wsm.add_work_units(agent_id, StructureType.LIBRARY, 100)
    await wsm.add_work_units(agent_id, StructureType.LIBRARY, 150)
    await wsm.add_work_units(agent_id, StructureType.FORGE, 50)

    assert agent.total_work_units == 300  # 100 + 150 + 50
    assert wsm._state.pending_work_units["v1"][StructureType.LIBRARY] == 250
    assert wsm._state.pending_work_units["v1"][StructureType.FORGE] == 50


@pytest.mark.asyncio
async def test_create_structure_applies_pending_work_units():
    """When structure is created, pending work units are applied (WI-293)."""
    import uuid
    from datetime import UTC, datetime
    from hamlet.world_state.types import Agent

    p = _make_persistence()
    wsm = WorldStateManager(p)
    wsm._state.villages["v1"] = Village(
        id="v1", project_id="p1", name="v",
        center=Position(0, 0), bounds=Bounds(0, 0, 0, 0),
    )

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

    # Accumulate pending work units before structure exists
    # Use 150 units (below threshold 200) so stage doesn't advance
    await wsm.add_work_units(agent_id, StructureType.LIBRARY, 150)

    # Create the structure
    s = await wsm.create_structure("v1", StructureType.LIBRARY, Position(1, 0))

    # Pending units should be applied to the new structure
    assert s.work_units == 150
    assert s.stage == 0  # No advancement since 150 < 200
    # Pending units should be cleared
    assert StructureType.LIBRARY not in wsm._state.pending_work_units.get("v1", {})


@pytest.mark.asyncio
async def test_create_structure_applies_pending_units_with_stage_advancement():
    """Pending units can cause stage advancement on new structure (WI-293)."""
    import uuid
    from datetime import UTC, datetime
    from hamlet.world_state.types import Agent

    p = _make_persistence()
    wsm = WorldStateManager(p)
    wsm._state.villages["v1"] = Village(
        id="v1", project_id="p1", name="v",
        center=Position(0, 0), bounds=Bounds(0, 0, 0, 0),
    )

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

    # LIBRARY threshold for stage 0->1 is 200
    # Accumulate enough pending units to advance stage
    await wsm.add_work_units(agent_id, StructureType.LIBRARY, 250)

    # Create the structure
    s = await wsm.create_structure("v1", StructureType.LIBRARY, Position(1, 0))

    # Should have advanced to stage 1, work_units reset
    assert s.stage == 1
    assert s.work_units == 0  # 250 - 200 = 50, but reset on advancement
    assert s.material == "wood"  # stage 1 material


@pytest.mark.asyncio
async def test_pending_work_units_per_village_isolation():
    """Pending work units are isolated per village (WI-293)."""
    import uuid
    from datetime import UTC, datetime
    from hamlet.world_state.types import Agent

    p = _make_persistence()
    wsm = WorldStateManager(p)

    # Two villages
    for vid in ["v1", "v2"]:
        wsm._state.villages[vid] = Village(
            id=vid, project_id=f"p-{vid}", name=f"village-{vid}",
            center=Position(0, 0), bounds=Bounds(0, 0, 0, 0),
        )

    now = datetime.now(UTC)

    # Agent in village v1
    agent1_id = str(uuid.uuid4())
    agent1 = Agent(
        id=agent1_id, session_id="sess1", project_id="p-v1",
        village_id="v1", position=Position(0, 0),
        state=AgentState.ACTIVE, inferred_type=AgentType.GENERAL,
        color="white", last_seen=now, created_at=now, updated_at=now,
    )
    wsm._state.agents[agent1_id] = agent1
    wsm._state.villages["v1"].agent_ids.append(agent1_id)

    # Agent in village v2
    agent2_id = str(uuid.uuid4())
    agent2 = Agent(
        id=agent2_id, session_id="sess2", project_id="p-v2",
        village_id="v2", position=Position(0, 0),
        state=AgentState.ACTIVE, inferred_type=AgentType.GENERAL,
        color="white", last_seen=now, created_at=now, updated_at=now,
    )
    wsm._state.agents[agent2_id] = agent2
    wsm._state.villages["v2"].agent_ids.append(agent2_id)

    # Add pending units in each village
    await wsm.add_work_units(agent1_id, StructureType.LIBRARY, 100)
    await wsm.add_work_units(agent2_id, StructureType.LIBRARY, 200)

    # Each village has its own pending pool
    assert wsm._state.pending_work_units["v1"][StructureType.LIBRARY] == 100
    assert wsm._state.pending_work_units["v2"][StructureType.LIBRARY] == 200

    # Create structure in v1 — only v1's pending units should be applied
    s1 = await wsm.create_structure("v1", StructureType.LIBRARY, Position(1, 0))
    assert s1.work_units == 100

    # v2's pending units should remain
    assert wsm._state.pending_work_units["v2"][StructureType.LIBRARY] == 200


@pytest.mark.asyncio
async def test_add_work_units_existing_structure_no_pending():
    """When structure exists, work units go directly to structure (not pending)."""
    import uuid
    from datetime import UTC, datetime
    from hamlet.world_state.types import Agent

    p = _make_persistence()
    wsm = WorldStateManager(p)
    wsm._state.villages["v1"] = Village(
        id="v1", project_id="p1", name="v",
        center=Position(0, 0), bounds=Bounds(0, 0, 0, 0),
    )

    # Create the structure first
    s = await wsm.create_structure("v1", StructureType.LIBRARY, Position(0, 0))

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

    # Add work units when structure already exists
    await wsm.add_work_units(agent_id, StructureType.LIBRARY, 100)

    # Work units go directly to structure
    assert s.work_units == 100
    # No pending units created
    assert "v1" not in wsm._state.pending_work_units or StructureType.LIBRARY not in wsm._state.pending_work_units.get("v1", {})
