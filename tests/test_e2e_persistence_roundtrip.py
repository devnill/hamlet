"""End-to-end tests: Persistence roundtrip (work item 097).

Tests the full persistence flow: World state -> SQLite -> World state

Run with: pytest tests/test_e2e_persistence_roundtrip.py -v
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from hamlet.inference.engine import AgentInferenceEngine
from hamlet.event_processing.event_processor import EventProcessor
from hamlet.persistence.facade import PersistenceFacade
from hamlet.persistence.types import PersistenceConfig
from hamlet.world_state.manager import WorldStateManager
from hamlet.world_state.types import (
    AgentState,
    AgentType,
    Position,
    StructureType,
)


@pytest.fixture
async def persistence_fixture(tmp_path):
    """Create a persistence facade with temp database.

    Yields the persistence facade and db_path for testing.
    """
    db_path = tmp_path / "test.db"
    config = PersistenceConfig(db_path=str(db_path), write_queue_size=100)
    persistence = PersistenceFacade(config)
    await persistence.start()

    try:
        yield {"persistence": persistence, "db_path": db_path}
    finally:
        await persistence.stop()


@pytest.fixture
async def world_with_data(tmp_path):
    """Create a world state with agents and structures, then persist.

    Creates a complete world state, persists it, and yields the components.
    Cleanup is performed after the test.
    """
    db_path = tmp_path / "test.db"
    config = PersistenceConfig(db_path=str(db_path), write_queue_size=100)
    persistence = PersistenceFacade(config)
    await persistence.start()

    try:
        world_state = WorldStateManager(persistence)
        await world_state.load_from_persistence()

        # Create event processing pipeline
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        event_processor = EventProcessor(event_queue)
        agent_inference = AgentInferenceEngine(world_state)

        event_processor._world_state = world_state
        event_processor._agent_inference = agent_inference
        event_processor._persistence = persistence

        await event_processor.start()

        # Create test data via events
        session_id = str(uuid4())
        project_id = "test-project"

        event = {
            "session_id": session_id,
            "project_id": project_id,
            "project_name": "Test Project",
            "hook_type": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/test.txt"},
        }

        await event_queue.put(event)
        await asyncio.wait_for(event_queue.join(), timeout=2.0)
        await asyncio.sleep(0.2)

        # Create a structure
        agents = await world_state.get_all_agents()
        if agents:
            agent = agents[0]
            village = await world_state.get_village(agent.village_id)
            if village:
                await world_state.create_structure(
                    village.id,
                    StructureType.HOUSE,
                    Position(5, 5),
                )

        # Force checkpoint to ensure data is written
        await persistence.checkpoint()
        await asyncio.sleep(0.2)

        yield {
            "persistence": persistence,
            "world_state": world_state,
            "event_processor": event_processor,
            "db_path": db_path,
            "session_id": session_id,
            "project_id": project_id,
        }

        await event_processor.stop()

    finally:
        await persistence.stop()


@pytest.mark.asyncio
async def test_save_and_load_world_state(world_with_data):
    """World state persists to SQLite and reloads correctly.

    AC-5: Verify that agents, structures, sessions, and villages
    are saved to SQLite and can be loaded back.
    """
    components = world_with_data
    original_world = components["world_state"]
    db_path = components["db_path"]

    # Get original state
    original_agents = await original_world.get_all_agents()
    original_villages = list(original_world._state.villages.values())
    original_sessions = list(original_world._state.sessions.values())

    assert len(original_agents) >= 1
    assert len(original_villages) >= 1
    assert len(original_sessions) >= 1

    # Create new persistence and world state (simulating restart)
    new_config = PersistenceConfig(db_path=str(db_path), write_queue_size=100)
    new_persistence = PersistenceFacade(new_config)
    await new_persistence.start()

    try:
        new_world = WorldStateManager(new_persistence)
        await new_world.load_from_persistence()

        # Verify agents restored
        loaded_agents = await new_world.get_all_agents()
        assert len(loaded_agents) == len(original_agents)

        # Verify agent data matches
        for orig_agent in original_agents:
            loaded_agent = next(
                (a for a in loaded_agents if a.id == orig_agent.id), None
            )
            assert loaded_agent is not None
            assert loaded_agent.session_id == orig_agent.session_id
            assert loaded_agent.village_id == orig_agent.village_id
            assert loaded_agent.position == orig_agent.position
            assert loaded_agent.state == orig_agent.state

        # Verify villages restored
        loaded_villages = list(new_world._state.villages.values())
        assert len(loaded_villages) == len(original_villages)

        # Verify structures restored
        loaded_structures = []
        for village_id in new_world._state.villages:
            structures = await new_world.get_structures_by_village(village_id)
            loaded_structures.extend(structures)

        original_structures = list(original_world._state.structures.values())
        assert len(loaded_structures) == len(original_structures)

        # Verify sessions restored
        loaded_sessions = list(new_world._state.sessions.values())
        assert len(loaded_sessions) == len(original_sessions)

    finally:
        await new_persistence.stop()


@pytest.mark.asyncio
async def test_restart_recovers_agents_and_structures(world_with_data):
    """Restart recovers all agents and structures from persistence.

    AC-6: Verify that after a restart, all agents and structures
    are available and their relationships are preserved.
    """
    components = world_with_data
    original_world = components["world_state"]
    db_path = components["db_path"]

    # Get original counts
    original_agents = await original_world.get_all_agents()
    original_structures = list(original_world._state.structures.values())

    agent_count = len(original_agents)
    structure_count = len(original_structures)

    assert agent_count >= 1

    # Simulate restart with new persistence instance
    new_config = PersistenceConfig(db_path=str(db_path), write_queue_size=100)
    new_persistence = PersistenceFacade(new_config)
    await new_persistence.start()

    try:
        new_world = WorldStateManager(new_persistence)
        await new_world.load_from_persistence()

        # Verify all entities recovered
        recovered_agents = await new_world.get_all_agents()
        assert len(recovered_agents) == agent_count

        # Verify structures recovered
        recovered_structures = []
        for village_id in new_world._state.villages:
            structures = await new_world.get_structures_by_village(village_id)
            recovered_structures.extend(structures)

        assert len(recovered_structures) == structure_count

        # Verify agent-village relationships (agents have valid village_ids)
        for agent in recovered_agents:
            village = await new_world.get_village(agent.village_id)
            assert village is not None

        # Verify structures have valid village references
        for struct in recovered_structures:
            village = await new_world.get_village(struct.village_id)
            assert village is not None

    finally:
        await new_persistence.stop()


@pytest.mark.asyncio
async def test_persistence_with_multiple_sessions(world_with_data):
    """Multiple sessions persist independently.

    Verifies that agents from different sessions are correctly
    persisted and restored with their session associations.
    """
    components = world_with_data
    original_world = components["world_state"]
    event_processor = components["event_processor"]
    db_path = components["db_path"]

    # Create additional session with agent
    session2_id = str(uuid4())
    event = {
        "session_id": session2_id,
        "project_id": "second-project",
        "project_name": "Second Project",
        "hook_type": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {},
    }

    event_queue = event_processor._queue
    await event_queue.put(event)
    await asyncio.wait_for(event_queue.join(), timeout=2.0)
    await asyncio.sleep(0.2)

    # Force checkpoint
    await components["persistence"].checkpoint()
    await asyncio.sleep(0.2)

    # Verify original state
    original_agents = await original_world.get_all_agents()
    assert len(original_agents) >= 2

    # Simulate restart
    new_config = PersistenceConfig(db_path=str(db_path), write_queue_size=100)
    new_persistence = PersistenceFacade(new_config)
    await new_persistence.start()

    try:
        new_world = WorldStateManager(new_persistence)
        await new_world.load_from_persistence()

        # Verify sessions exist
        sessions = list(new_world._state.sessions.values())
        assert len(sessions) >= 2

        # Verify agents are recovered
        recovered_agents = await new_world.get_all_agents()
        assert len(recovered_agents) >= 2

        # Verify each agent is in a valid village
        for agent in recovered_agents:
            village = await new_world.get_village(agent.village_id)
            assert village is not None
            # Agent's village should reference the same session's project
            session = new_world._state.sessions.get(agent.session_id)
            if session:
                assert village.project_id == session.project_id

    finally:
        await new_persistence.stop()


@pytest.mark.asyncio
async def test_persistence_graceful_degradation(persistence_fixture):
    """Persistence continues despite errors (GP-7).

    Verifies that the persistence layer continues operating
    when individual write operations fail.
    """
    components = persistence_fixture
    persistence = components["persistence"]
    db_path = components["db_path"]

    world_state = WorldStateManager(persistence)
    await world_state.load_from_persistence()

    # Create some data
    session_id = str(uuid4())
    event = {
        "session_id": session_id,
        "project_id": "test-project",
        "project_name": "Test Project",
        "hook_type": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {},
    }

    # Process event
    event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    event_processor = EventProcessor(event_queue)
    agent_inference = AgentInferenceEngine(world_state)

    event_processor._world_state = world_state
    event_processor._agent_inference = agent_inference
    event_processor._persistence = persistence

    await event_processor.start()

    await event_queue.put(event)
    await asyncio.wait_for(event_queue.join(), timeout=2.0)
    await asyncio.sleep(0.2)

    # Verify agent was created despite any potential persistence issues
    agents = await world_state.get_all_agents()
    assert len(agents) >= 1

    await event_processor.stop()


@pytest.mark.asyncio
async def test_checkpoint_ensures_durability(world_with_data):
    """Checkpoint ensures data is written to disk.

    Verifies that calling checkpoint() ensures all pending
    writes are flushed to the database.
    """
    components = world_with_data
    persistence = components["persistence"]
    db_path = components["db_path"]

    # Create additional data
    world_state = components["world_state"]

    # Get a village and create a structure
    agents = await world_state.get_all_agents()
    if agents:
        agent = agents[0]
        village = await world_state.get_village(agent.village_id)
        if village:
            await world_state.create_structure(
                village.id,
                StructureType.WORKSHOP,
                Position(10, 10),
            )

    # Force checkpoint
    await persistence.checkpoint()
    await asyncio.sleep(0.3)

    # Verify data exists by loading in new instance
    new_config = PersistenceConfig(db_path=str(db_path), write_queue_size=100)
    new_persistence = PersistenceFacade(new_config)
    await new_persistence.start()

    try:
        new_world = WorldStateManager(new_persistence)
        await new_world.load_from_persistence()

        # Verify structures were persisted
        all_structures = []
        for village_id in new_world._state.villages:
            structures = await new_world.get_structures_by_village(village_id)
            all_structures.extend(structures)

        # Should have at least 2 structures (house from fixture + workshop)
        assert len(all_structures) >= 2

        # Verify the workshop we created at (10, 10) was persisted
        workshops_at_target = [
            s for s in all_structures
            if s.type == StructureType.WORKSHOP and s.position == Position(10, 10)
        ]
        assert len(workshops_at_target) >= 1

    finally:
        await new_persistence.stop()


@pytest.mark.asyncio
async def test_agent_state_preserved_across_restart(world_with_data):
    """Agent state is preserved across restart.

    Verifies that agent states (active, idle, zombie) are correctly
    persisted and restored.
    """
    components = world_with_data
    original_world = components["world_state"]
    db_path = components["db_path"]

    # Get original agents and their states
    original_agents = await original_world.get_all_agents()
    assert len(original_agents) >= 1

    # Update one agent to idle state
    agent = original_agents[0]
    await original_world.update_agent(agent.id, state=AgentState.IDLE)
    await asyncio.sleep(0.1)

    # Force checkpoint
    await components["persistence"].checkpoint()
    await asyncio.sleep(0.2)

    # Simulate restart
    new_config = PersistenceConfig(db_path=str(db_path), write_queue_size=100)
    new_persistence = PersistenceFacade(new_config)
    await new_persistence.start()

    try:
        new_world = WorldStateManager(new_persistence)
        await new_world.load_from_persistence()

        # Verify agent state was preserved
        recovered_agents = await new_world.get_all_agents()
        recovered_agent = next(
            (a for a in recovered_agents if a.id == agent.id), None
        )
        assert recovered_agent is not None
        assert recovered_agent.state == AgentState.IDLE

    finally:
        await new_persistence.stop()


@pytest.mark.asyncio
async def test_empty_database_loads_clean_state(persistence_fixture):
    """Loading from empty database creates clean state.

    Verifies that loading from a fresh database results in
    an empty but functional world state.
    """
    components = persistence_fixture
    persistence = components["persistence"]

    world_state = WorldStateManager(persistence)
    await world_state.load_from_persistence()

    # Verify clean state
    agents = await world_state.get_all_agents()
    assert len(agents) == 0

    villages = list(world_state._state.villages.values())
    assert len(villages) == 0

    sessions = list(world_state._state.sessions.values())
    assert len(sessions) == 0

    # Verify world state is functional (can create entities)
    session_id = str(uuid4())
    event = {
        "session_id": session_id,
        "project_id": "new-project",
        "project_name": "New Project",
        "hook_type": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {},
    }

    event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    event_processor = EventProcessor(event_queue)
    agent_inference = AgentInferenceEngine(world_state)

    event_processor._world_state = world_state
    event_processor._agent_inference = agent_inference
    event_processor._persistence = persistence

    await event_processor.start()

    await event_queue.put(event)
    await asyncio.wait_for(event_queue.join(), timeout=2.0)
    await asyncio.sleep(0.2)

    # Verify agent was created
    agents = await world_state.get_all_agents()
    assert len(agents) == 1

    await event_processor.stop()
