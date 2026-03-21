"""Tests for ExpansionManager (work item 084).

Test framework: pytest + pytest-asyncio.
Run with: pytest tests/test_expansion.py -v
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from hamlet.simulation.config import SimulationConfig
from hamlet.simulation.expansion import ExpansionManager
from hamlet.world_state.types import Agent, AgentState, AgentType, Position, Village


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def config() -> SimulationConfig:
    """Return a SimulationConfig with default settings."""
    return SimulationConfig(expansion_threshold=3)


@pytest.fixture
def expansion_mgr(config: SimulationConfig) -> ExpansionManager:
    """Return an ExpansionManager with mocked config."""
    return ExpansionManager(config)


@pytest.fixture
def village() -> Village:
    """Return a test village."""
    return Village(
        id="village-1",
        project_id="project-1",
        name="Test Village",
        center=Position(0, 0),
    )


@pytest.fixture
def agents() -> list[Agent]:
    """Return a list of test agents above expansion threshold."""
    return [
        Agent(
            id=f"agent-{i}",
            session_id="session-1",
            project_id="project-1",
            village_id="village-1",
            inferred_type=AgentType.GENERAL,
            state=AgentState.ACTIVE,
        )
        for i in range(5)
    ]


# -----------------------------------------------------------------------------
# Test Class: TestExpansionManager
# -----------------------------------------------------------------------------

class TestExpansionManager:
    """Tests for ExpansionManager village expansion and road building."""

    def test_check_village_expansion_finds_clear_site(
        self,
        expansion_mgr: ExpansionManager,
        village: Village,
        agents: list[Agent],
    ) -> None:
        """test_check_village_expansion_finds_clear_site - Expansion returns a clear site when agents exceed threshold."""
        # No other villages, so any site should be clear
        all_villages = [village]

        result = expansion_mgr.check_village_expansion(village, agents, all_villages)

        # Should return a Position (not None)
        assert result is not None
        assert isinstance(result, Position)
        # Site should be at least 20 cells away from village center
        distance = (result.x ** 2 + result.y ** 2) ** 0.5
        assert distance >= 20

    def test_check_village_expansion_returns_none_below_threshold(
        self,
        expansion_mgr: ExpansionManager,
        village: Village,
    ) -> None:
        """Expansion returns None when agents are below threshold."""
        # Create only 1 agent (below threshold of 3)
        few_agents = [
            Agent(
                id="agent-1",
                session_id="session-1",
                project_id="project-1",
                village_id="village-1",
                inferred_type=AgentType.GENERAL,
                state=AgentState.ACTIVE,
            )
        ]
        all_villages = [village]

        result = expansion_mgr.check_village_expansion(village, few_agents, all_villages)

        assert result is None

    def test_check_village_expansion_respects_min_distance(
        self,
        expansion_mgr: ExpansionManager,
        village: Village,
        agents: list[Agent],
    ) -> None:
        """Expansion site is at least min_distance from all existing villages."""
        # Create another village close to potential expansion sites
        other_village = Village(
            id="village-2",
            project_id="project-2",
            name="Other Village",
            center=Position(35, 0),  # Close to where expansion might be considered
        )
        all_villages = [village, other_village]

        result = expansion_mgr.check_village_expansion(village, agents, all_villages)

        if result is not None:
            # Verify the site is at least 15 cells from the other village
            dist_to_other = ((other_village.center.x - result.x) ** 2 +
                           (other_village.center.y - result.y) ** 2) ** 0.5
            assert dist_to_other >= 15

    async def test_process_expansion_creates_roads(
        self,
        expansion_mgr: ExpansionManager,
        village: Village,
        agents: list[Agent],
    ) -> None:
        """test_process_expansion_creates_roads - process_expansion creates roads when expansion site is found."""
        # Create mock world_state
        world_state = MagicMock()
        world_state.get_all_villages = AsyncMock(return_value=[village])
        world_state.get_all_agents = AsyncMock(return_value=agents)
        world_state.create_structure = AsyncMock()
        world_state.found_village = AsyncMock(return_value=MagicMock())

        # Set up village with agent IDs
        village.agent_ids = [agent.id for agent in agents]

        await expansion_mgr.process_expansion(world_state)

        # Verify create_structure was called for road segments
        assert world_state.create_structure.called
        # All calls should be for ROAD type
        for call in world_state.create_structure.call_args_list:
            args = call[0]
            assert args[1].value == "road"  # StructureType.ROAD

    def test_bresenham_line_algorithm(
        self,
        expansion_mgr: ExpansionManager,
    ) -> None:
        """Bresenham's line algorithm returns correct points."""
        points = expansion_mgr._bresenham(0, 0, 3, 3)

        # Should include start and end points
        assert (0, 0) in points
        assert (3, 3) in points
        # Should have reasonable number of points for diagonal
        assert len(points) >= 4

    def test_bresenham_horizontal_line(
        self,
        expansion_mgr: ExpansionManager,
    ) -> None:
        """Bresenham handles horizontal lines correctly."""
        points = expansion_mgr._bresenham(0, 0, 5, 0)

        assert (0, 0) in points
        assert (5, 0) in points
        assert len(points) == 6  # 0,1,2,3,4,5

    def test_bresenham_vertical_line(
        self,
        expansion_mgr: ExpansionManager,
    ) -> None:
        """Bresenham handles vertical lines correctly."""
        points = expansion_mgr._bresenham(0, 0, 0, 5)

        assert (0, 0) in points
        assert (0, 5) in points
        assert len(points) == 6  # 0,1,2,3,4,5

    def test_is_clear_site_true_when_far_enough(
        self,
        expansion_mgr: ExpansionManager,
    ) -> None:
        """_is_clear_site returns True when position is far from all villages."""
        villages = [
            Village(id="v1", project_id="p1", name="V1", center=Position(0, 0)),
            Village(id="v2", project_id="p2", name="V2", center=Position(100, 0)),
        ]

        result = expansion_mgr._is_clear_site(Position(50, 0), villages, min_distance=15)

        assert result is True

    def test_is_clear_site_false_when_too_close(
        self,
        expansion_mgr: ExpansionManager,
    ) -> None:
        """_is_clear_site returns False when position is too close to a village."""
        villages = [
            Village(id="v1", project_id="p1", name="V1", center=Position(0, 0)),
        ]

        result = expansion_mgr._is_clear_site(Position(10, 0), villages, min_distance=15)

        assert result is False

    async def test_create_road_between_creates_structures(
        self,
        expansion_mgr: ExpansionManager,
    ) -> None:
        """create_road_between creates structures along the line."""
        world_state = MagicMock()
        world_state.create_structure = AsyncMock()

        await expansion_mgr.create_road_between(
            world_state, "village-1", Position(0, 0), Position(3, 0)
        )

        # Should create 4 structures (positions 0,1,2,3)
        assert world_state.create_structure.call_count == 4

    async def test_process_expansion_calls_found_village(
        self,
        expansion_mgr: ExpansionManager,
        village: Village,
        agents: list[Agent],
    ) -> None:
        """process_expansion calls found_village when an expansion site is found."""
        world_state = MagicMock()
        world_state.get_all_villages = AsyncMock(return_value=[village])
        world_state.get_all_agents = AsyncMock(return_value=agents)
        world_state.create_structure = AsyncMock()
        world_state.found_village = AsyncMock(return_value=MagicMock())

        village.agent_ids = [agent.id for agent in agents]

        await expansion_mgr.process_expansion(world_state)

        # found_village must have been called exactly once with the correct args.
        # New signature: found_village(originating_village_id, project_id, site, name)
        assert world_state.found_village.called
        call_kwargs = world_state.found_village.call_args
        called_originating_id = call_kwargs[0][0]
        called_project_id = call_kwargs[0][1]
        called_name = call_kwargs[0][3]
        assert called_originating_id == village.id
        assert called_project_id == village.project_id
        assert "Outpost" in called_name

    async def test_process_expansion_no_duplicate_village(
        self,
        expansion_mgr: ExpansionManager,
        village: Village,
        agents: list[Agent],
    ) -> None:
        """A second process_expansion call does not found a duplicate village at the same site.

        After the first expansion, the outpost village appears in all_villages.
        On the second tick, _is_clear_site returns False for sites within 15
        cells of the outpost, so the exact same site is never passed to
        found_village again.  The found_village idempotency guard (5-cell
        radius) also ensures that even if a very close site were selected, the
        existing outpost would be returned rather than a duplicate being created.
        """
        captured: dict[str, Any] = {}

        def _capture_outpost(orig_id: str, pid: str, site: Position, name: str) -> Village:
            v = Village(
                id="outpost-1",
                project_id=pid,
                name=name,
                center=site,
            )
            captured["outpost"] = v
            return v

        world_state = MagicMock()
        world_state.create_structure = AsyncMock()
        world_state.found_village = AsyncMock(side_effect=_capture_outpost)

        village.agent_ids = [agent.id for agent in agents]

        # Tick 1: only original village — expansion site found, outpost founded.
        world_state.get_all_villages = AsyncMock(return_value=[village])
        world_state.get_all_agents = AsyncMock(return_value=agents)
        await expansion_mgr.process_expansion(world_state)

        assert world_state.found_village.call_count == 1
        outpost = captured.get("outpost")
        assert outpost is not None
        tick1_site = world_state.found_village.call_args[0][2]

        # Tick 2: both villages present — site near outpost is no longer clear.
        world_state.found_village.reset_mock()
        world_state.get_all_villages = AsyncMock(return_value=[village, outpost])
        await expansion_mgr.process_expansion(world_state)

        # If found_village was called, the site must be at least 15 cells from
        # the outpost (i.e., _is_clear_site blocked the original location).
        for call in world_state.found_village.call_args_list:
            new_site: Position = call[0][2]
            dist_to_outpost = (
                (new_site.x - tick1_site.x) ** 2
                + (new_site.y - tick1_site.y) ** 2
            ) ** 0.5
            assert dist_to_outpost >= 15, (
                f"found_village called at {new_site} which is only {dist_to_outpost:.1f} "
                f"cells from the outpost at {tick1_site}"
            )

    async def test_has_expanded_true_blocks_expansion(
        self,
        expansion_mgr: ExpansionManager,
        agents: list[Agent],
    ) -> None:
        """A village with agents >= threshold and has_expanded=True does NOT trigger
        road building or found_village on subsequent ticks."""
        expanded_village = Village(
            id="village-expanded",
            project_id="project-1",
            name="Expanded Village",
            center=Position(0, 0),
            has_expanded=True,
        )
        expanded_village.agent_ids = [agent.id for agent in agents]

        world_state = MagicMock()
        world_state.get_all_villages = AsyncMock(return_value=[expanded_village])
        world_state.get_all_agents = AsyncMock(return_value=agents)
        world_state.create_structure = AsyncMock()
        world_state.found_village = AsyncMock()

        await expansion_mgr.process_expansion(world_state)

        # Neither road building nor village founding should happen.
        world_state.create_structure.assert_not_called()
        world_state.found_village.assert_not_called()

    async def test_has_expanded_false_triggers_expansion_exactly_once(
        self,
        expansion_mgr: ExpansionManager,
        agents: list[Agent],
    ) -> None:
        """A village with agents >= threshold and has_expanded=False triggers
        expansion exactly once; after the call has_expanded is set to True on
        the village object (via the world_state.found_village side-effect), so
        a second process_expansion call with the flag already set does nothing."""
        village = Village(
            id="village-fresh",
            project_id="project-fresh",
            name="Fresh Village",
            center=Position(0, 0),
            has_expanded=False,
        )
        village.agent_ids = [agent.id for agent in agents]

        def _set_expanded(orig_id: str, pid: str, site: Position, name: str) -> Village:
            # Simulate manager setting has_expanded on the originating village.
            village.has_expanded = True
            return Village(id="outpost-x", project_id=pid, name=name, center=site)

        world_state = MagicMock()
        world_state.create_structure = AsyncMock()
        world_state.found_village = AsyncMock(side_effect=_set_expanded)

        # Tick 1: has_expanded is False — expansion fires.
        world_state.get_all_villages = AsyncMock(return_value=[village])
        world_state.get_all_agents = AsyncMock(return_value=agents)
        await expansion_mgr.process_expansion(world_state)

        assert world_state.found_village.call_count == 1
        assert village.has_expanded is True

        # Tick 2: has_expanded is now True — expansion must not fire again.
        world_state.found_village.reset_mock()
        world_state.create_structure.reset_mock()
        world_state.get_all_villages = AsyncMock(return_value=[village])
        await expansion_mgr.process_expansion(world_state)

        world_state.found_village.assert_not_called()
        world_state.create_structure.assert_not_called()
