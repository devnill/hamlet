"""Tests for RemoteWorldState."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from hamlet.tui.remote_world_state import RemoteWorldState
from hamlet.world_state.parsers import parse_structure


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.fetch_state = AsyncMock(return_value={
        "agents": [],
        "structures": [],
        "villages": [],
        "projects": [],
        "animation_frames": {"agent-1": 2}
    })
    # fetch_events returns a list directly (not a dict)
    provider.fetch_events = AsyncMock(return_value=[])
    return provider


@pytest.fixture
def remote_state(mock_provider):
    return RemoteWorldState(mock_provider)
async def test_get_all_agents_empty_before_refresh(remote_state):
    agents = await remote_state.get_all_agents()
    assert agents == []
async def test_get_animation_frame_returns_default(remote_state):
    frame = remote_state.get_animation_frame("unknown-agent")
    assert frame == 0
async def test_get_animation_frame_after_refresh(remote_state, mock_provider):
    await remote_state.refresh()
    frame = remote_state.get_animation_frame("agent-1")
    assert frame == 2
async def test_get_event_log_uses_oldest_first(remote_state, mock_provider):
    # fetch_events returns a list directly
    mock_provider.fetch_events = AsyncMock(return_value=[
        {"id": "e1", "timestamp": None, "session_id": "", "project_id": "",
         "hook_type": "", "tool_name": None, "summary": ""},
        {"id": "e2", "timestamp": None, "session_id": "", "project_id": "",
         "hook_type": "", "tool_name": None, "summary": ""},
        {"id": "e3", "timestamp": None, "session_id": "", "project_id": "",
         "hook_type": "", "tool_name": None, "summary": ""},
    ])
    await remote_state.refresh()
    log = await remote_state.get_event_log(limit=2)
    assert len(log) == 2
    assert log[0].id == "e1"  # oldest first (insertion order)
    assert log[1].id == "e2"
async def test_refresh_retains_stale_on_exception(remote_state, mock_provider):
    # Set initial state
    await remote_state.refresh()
    initial_frame = remote_state.get_animation_frame("agent-1")
    assert initial_frame == 2

    # Make next refresh fail
    mock_provider.fetch_state = AsyncMock(side_effect=Exception("network error"))
    await remote_state.refresh()

    # Stale data retained
    frame_after_failure = remote_state.get_animation_frame("agent-1")
    assert frame_after_failure == initial_frame
async def test_get_all_agents_after_refresh(mock_provider):
    mock_provider.fetch_state = AsyncMock(return_value={
        "agents": [
            {
                "id": "a1",
                "session_id": "s1",
                "project_id": "p1",
                "village_id": "v1",
                "inferred_type": "general",
                "color": "white",
                "position": {"x": 1, "y": 2},
                "last_seen": None,
                "state": "active",
                "parent_id": None,
                "current_activity": None,
                "total_work_units": 0,
                "created_at": None,
                "updated_at": None,
            }
        ],
        "structures": [],
        "villages": [],
        "projects": [],
        "animation_frames": {},
    })
    state = RemoteWorldState(mock_provider)
    await state.refresh()
    agents = await state.get_all_agents()
    assert len(agents) == 1
    assert agents[0].id == "a1"
async def test_get_event_log_respects_limit(remote_state, mock_provider):
    events = [
        {"id": f"e{i}", "timestamp": None, "session_id": "", "project_id": "",
         "hook_type": "", "tool_name": None, "summary": ""}
        for i in range(10)
    ]
    mock_provider.fetch_events = AsyncMock(return_value=events)
    await remote_state.refresh()
    log = await remote_state.get_event_log(limit=5)
    assert len(log) == 5
    assert log[0].id == "e0"
async def test_events_fetch_failure_retains_stale_events(remote_state, mock_provider):
    events = [
        {"id": "e1", "timestamp": None, "session_id": "", "project_id": "",
         "hook_type": "", "tool_name": None, "summary": ""}
    ]
    mock_provider.fetch_events = AsyncMock(return_value=events)
    await remote_state.refresh()
    log = await remote_state.get_event_log()
    assert len(log) == 1

    # Second refresh: events fetch fails
    mock_provider.fetch_events = AsyncMock(side_effect=Exception("timeout"))
    await remote_state.refresh()

    # Stale events retained
    log_after = await remote_state.get_event_log()
    assert len(log_after) == 1
    assert log_after[0].id == "e1"


def test_parse_structure_reads_size_tier():
    result = parse_structure({
        "id": "s1",
        "village_id": "v1",
        "type": "house",
        "size_tier": 3,
    })
    assert result.size_tier == 3


def test_parse_structure_defaults_size_tier_to_1():
    result = parse_structure({
        "id": "s1",
        "village_id": "v1",
        "type": "house",
    })
    assert result.size_tier == 1


# ---------------------------------------------------------------------------
# Terrain query tests
# ---------------------------------------------------------------------------

async def test_get_terrain_at_returns_terrain_from_provider():
    """Test that get_terrain_at fetches terrain from provider and returns TerrainType."""
    provider = MagicMock()
    provider.fetch_terrain = AsyncMock(return_value={"terrain": "forest", "passable": True})
    state = RemoteWorldState(provider)

    terrain = await state.get_terrain_at(10, 20)

    assert terrain.value == "forest"
    provider.fetch_terrain.assert_called_once_with(10, 20)


async def test_get_terrain_at_defaults_to_plain():
    """Test that get_terrain_at defaults to PLAIN if provider returns empty dict."""
    provider = MagicMock()
    provider.fetch_terrain = AsyncMock(return_value={})
    state = RemoteWorldState(provider)

    terrain = await state.get_terrain_at(0, 0)

    assert terrain.value == "plain"


async def test_is_passable_returns_passable_from_provider():
    """Test that is_passable returns the passable field from provider."""
    provider = MagicMock()
    provider.fetch_terrain = AsyncMock(return_value={"terrain": "water", "passable": False})
    state = RemoteWorldState(provider)

    result = await state.is_passable(5, 10)

    assert result is False
    provider.fetch_terrain.assert_called_once_with(5, 10)


async def test_is_passable_defaults_to_true():
    """Test that is_passable defaults to True if provider returns empty dict."""
    provider = MagicMock()
    provider.fetch_terrain = AsyncMock(return_value={})
    state = RemoteWorldState(provider)

    result = await state.is_passable(0, 0)

    assert result is True


# ---------------------------------------------------------------------------
# Per-item try_parse resilience tests
# ---------------------------------------------------------------------------

async def test_malformed_agent_does_not_drop_valid_agents(mock_provider):
    """A single malformed agent dict must not cause all agents to be lost."""
    good_agent = {
        "id": "a1",
        "session_id": "s1",
        "project_id": "p1",
        "village_id": "v1",
        "inferred_type": "general",
        "color": "white",
        "position": {"x": 1, "y": 2},
        "last_seen": None,
        "state": "active",
        "parent_id": None,
        "current_activity": None,
        "total_work_units": 0,
        "created_at": None,
        "updated_at": None,
    }
    # inferred_type value "INVALID_TYPE" will raise ValueError in AgentType()
    bad_agent = {"id": "bad", "inferred_type": "INVALID_TYPE"}
    mock_provider.fetch_state = AsyncMock(return_value={
        "agents": [good_agent, bad_agent],
        "structures": [],
        "villages": [],
        "projects": [],
        "animation_frames": {},
    })
    state = RemoteWorldState(mock_provider)
    await state.refresh()
    agents = await state.get_all_agents()
    assert len(agents) == 1
    assert agents[0].id == "a1"


async def test_malformed_structure_does_not_drop_valid_structures(mock_provider):
    """A single malformed structure dict must not cause all structures to be lost."""
    good_structure = {
        "id": "s1",
        "village_id": "v1",
        "type": "house",
        "position": {"x": 0, "y": 0},
        "stage": 0,
        "material": "wood",
        "work_units": 0,
        "work_required": 100,
        "size_tier": 1,
        "created_at": None,
        "updated_at": None,
    }
    # "type" value "INVALID_TYPE" will raise ValueError in StructureType()
    bad_structure = {"id": "bad", "type": "INVALID_STRUCTURE_TYPE"}
    mock_provider.fetch_state = AsyncMock(return_value={
        "agents": [],
        "structures": [good_structure, bad_structure],
        "villages": [],
        "projects": [],
        "animation_frames": {},
    })
    state = RemoteWorldState(mock_provider)
    await state.refresh()
    structures = await state.get_all_structures()
    assert len(structures) == 1
    assert structures[0].id == "s1"


async def test_malformed_event_log_entry_does_not_drop_valid_entries(mock_provider):
    """A single malformed event dict must not cause all event log entries to be lost."""
    good_event = {
        "id": "e1",
        "timestamp": None,
        "session_id": "",
        "project_id": "",
        "hook_type": "",
        "tool_name": None,
        "summary": "ok",
    }
    # None is not a dict; parse_event_log_entry will raise AttributeError
    bad_event = None
    mock_provider.fetch_events = AsyncMock(return_value=[good_event, bad_event])
    state = RemoteWorldState(mock_provider)
    await state.refresh()
    log = await state.get_event_log()
    assert len(log) == 1
    assert log[0].id == "e1"
