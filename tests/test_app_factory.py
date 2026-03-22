"""Tests for app_factory.build_components wiring."""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def test_build_components_wires_zombie_threshold_seconds():
    """build_components passes zombie_threshold_seconds from Settings to AgentInferenceEngine."""
    # Stub heavy third-party modules so app_factory can be imported without
    # a full installed environment (e.g. no aiosqlite in the test runner).
    aiosqlite_stub = MagicMock()
    modules_to_stub = {
        "aiosqlite": aiosqlite_stub,
    }
    with patch.dict(sys.modules, modules_to_stub):
        from hamlet.config.settings import Settings
        from hamlet.app_factory import build_components

        settings = Settings(zombie_threshold_seconds=42)

        mock_persistence = AsyncMock()
        mock_world_state = AsyncMock()
        mock_world_state.get_all_agents = AsyncMock(return_value=[])
        mock_mcp_server = AsyncMock()
        mock_mcp_server.get_event_queue = MagicMock(return_value=AsyncMock())
        mock_event_processor = AsyncMock()
        mock_simulation = AsyncMock()

        with (
            patch("hamlet.app_factory.PersistenceFacade", return_value=mock_persistence),
            patch("hamlet.app_factory.WorldStateManager", return_value=mock_world_state),
            patch("hamlet.app_factory.MCPServer", return_value=mock_mcp_server),
            patch("hamlet.app_factory.EventProcessor", return_value=mock_event_processor),
            patch("hamlet.app_factory.SimulationEngine", return_value=mock_simulation),
        ):
            bundle = await build_components(settings)

    assert bundle.agent_inference._zombie_threshold_seconds == 42
    assert bundle.agent_inference._despawn_threshold_seconds == settings.zombie_despawn_seconds
