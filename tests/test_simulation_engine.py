"""Tests for SimulationEngine (work item 083).

Test framework: pytest + pytest-asyncio.
Run with: pytest tests/test_simulation_engine.py -v
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from hamlet.simulation.config import SimulationConfig
from hamlet.simulation.engine import SimulationEngine


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def world_state() -> MagicMock:
    """Return a mock WorldStateManager with empty agents and structures."""
    ws = MagicMock()
    ws._state = MagicMock()
    ws._state.agents = {}
    ws._state.structures = {}
    ws.get_all_agents = AsyncMock(return_value=[])
    ws.get_all_structures = AsyncMock(return_value=[])
    return ws


@pytest.fixture
def engine(world_state: MagicMock) -> SimulationEngine:
    """Return a SimulationEngine with mocked dependencies."""
    return SimulationEngine(world_state)


@pytest.fixture
def engine_with_updaters(world_state: MagicMock) -> SimulationEngine:
    """Return a SimulationEngine with mocked updaters."""
    agent_updater = MagicMock()
    agent_updater.update_agents = AsyncMock()
    structure_updater = MagicMock()
    structure_updater.update_structures = AsyncMock()
    return SimulationEngine(
        world_state,
        agent_updater=agent_updater,
        structure_updater=structure_updater,
    )


# -----------------------------------------------------------------------------
# Test Class: TestSimulationEngine
# -----------------------------------------------------------------------------

class TestSimulationEngine:
    """Tests for SimulationEngine lifecycle and tick behavior."""

    @pytest.mark.asyncio
    async def test_start_creates_background_task(self, engine: SimulationEngine) -> None:
        """test_start_creates_background_task - Start creates a background task."""
        await engine.start()

        assert engine._task is not None
        assert engine._state.running is True
        assert not engine._task.done()

        await engine.stop()

    @pytest.mark.asyncio
    async def test_tick_increments_tick_count(self, engine: SimulationEngine) -> None:
        """test_tick_increments_tick_count - Tick increments tick_count."""
        initial_count = engine._state.tick_count

        await engine._tick()

        assert engine._state.tick_count == initial_count + 1
        assert engine._state.last_tick_at is not None

    @pytest.mark.asyncio
    async def test_tick_calls_agent_updater(
        self, engine_with_updaters: SimulationEngine, world_state: MagicMock
    ) -> None:
        """test_tick_calls_agent_updater - Tick calls agent_updater.update_agents."""
        engine = engine_with_updaters

        await engine._tick()

        engine._agent_updater.update_agents.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_tick_calls_structure_updater(
        self, engine_with_updaters: SimulationEngine, world_state: MagicMock
    ) -> None:
        """Tick calls structure_updater.update_structures."""
        engine = engine_with_updaters

        await engine._tick()

        engine._structure_updater.update_structures.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_tick_error_in_handler_logged(
        self, engine: SimulationEngine, caplog: pytest.LogCaptureFixture
    ) -> None:
        """test_tick_error_in_handler_logged - Errors in tick handlers are logged, not raised (GP-7)."""
        # Create a mock updater that raises an exception
        mock_updater = MagicMock()
        mock_updater.update_agents = AsyncMock(side_effect=RuntimeError("boom"))
        engine._agent_updater = mock_updater

        with caplog.at_level(logging.ERROR):
            await engine._tick()

        # Verify error was logged
        assert "Error in agent update" in caplog.text
        assert "boom" in caplog.text

        # Verify engine is still functional
        assert engine._state.tick_count == 1

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, engine: SimulationEngine) -> None:
        """Stop cancels the background task."""
        await engine.start()
        assert engine._task is not None

        await engine.stop()

        assert engine._task is None
        assert engine._state.running is False

    @pytest.mark.asyncio
    async def test_set_tick_rate_valid(self, engine: SimulationEngine) -> None:
        """set_tick_rate updates the tick rate when given a positive value."""
        engine.set_tick_rate(60.0)

        assert engine._config.tick_rate == 60.0

    def test_set_tick_rate_invalid(self, engine: SimulationEngine) -> None:
        """set_tick_rate raises ValueError for non-positive rates."""
        with pytest.raises(ValueError, match="tick_rate must be positive"):
            engine.set_tick_rate(0)

        with pytest.raises(ValueError, match="tick_rate must be positive"):
            engine.set_tick_rate(-1)

    @pytest.mark.asyncio
    async def test_start_idempotent(self, engine: SimulationEngine) -> None:
        """Calling start twice does not create duplicate tasks."""
        await engine.start()
        first_task = engine._task

        await engine.start()
        second_task = engine._task

        assert first_task is second_task

        await engine.stop()

    @pytest.mark.asyncio
    async def test_get_state_returns_snapshot(self, engine: SimulationEngine) -> None:
        """get_state returns the current simulation state."""
        await engine._tick()

        state = engine.get_state()

        assert state.tick_count == 1
        assert isinstance(state.last_tick_at, datetime)
