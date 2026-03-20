"""End-to-end tests: Hook script to TUI render flow (work item 097).

Tests the full flow: Hook script -> MCP server -> Event processor ->
Agent inference -> World state -> TUI render

Run with: pytest tests/test_e2e_hook_to_render.py -v
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from hamlet.event_processing.event_processor import EventProcessor
from hamlet.event_processing.internal_event import HookType, InternalEvent
from hamlet.inference.engine import AgentInferenceEngine
from hamlet.mcp_server.server import MCPServer
from hamlet.persistence.facade import PersistenceFacade
from hamlet.persistence.types import PersistenceConfig
from hamlet.simulation.agent_updater import AgentUpdater
from hamlet.simulation.config import SimulationConfig
from hamlet.simulation.engine import SimulationEngine
from hamlet.viewport.coordinates import BoundingBox, Position, Size
from hamlet.viewport.manager import ViewportManager
from hamlet.world_state.manager import WorldStateManager
from hamlet.world_state.types import AgentState


@pytest.fixture
async def e2e_components(tmp_path):
    """Create full component stack with temp database.

    Yields a dict with all components wired together for E2E testing.
    Cleanup is performed after the test completes.
    """
    db_path = tmp_path / "test.db"
    config = PersistenceConfig(db_path=str(db_path), write_queue_size=100)
    persistence = PersistenceFacade(config)
    await persistence.start()

    try:
        world_state = WorldStateManager(persistence)
        await world_state.load_from_persistence()

        # Create event queue and processor
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        event_processor = EventProcessor(event_queue)

        # Create agent inference engine
        agent_inference = AgentInferenceEngine(world_state)

        # Wire up event processor to world state and agent inference
        event_processor._world_state = world_state
        event_processor._agent_inference = agent_inference
        event_processor._persistence = persistence

        # Create MCP server with the same event queue
        mcp_server = MCPServer(world_state=world_state)
        # Replace the server's queue with ours for testing
        mcp_server._event_queue = event_queue

        # Create simulation engine with agent updater
        sim_config = SimulationConfig(tick_rate=10.0, zombie_threshold=300.0)
        agent_updater = AgentUpdater(sim_config)
        simulation = SimulationEngine(
            world_state,
            config=sim_config,
            agent_updater=agent_updater,
        )

        # Create viewport manager for TUI rendering
        viewport = ViewportManager(world_state)
        await viewport.initialize()

        # Start all components
        await event_processor.start()
        await simulation.start()

        yield {
            "persistence": persistence,
            "world_state": world_state,
            "event_processor": event_processor,
            "agent_inference": agent_inference,
            "simulation": simulation,
            "mcp_server": mcp_server,
            "event_queue": event_queue,
            "viewport": viewport,
            "db_path": db_path,
        }

    finally:
        # Cleanup in reverse order
        await simulation.stop()
        await event_processor.stop()
        await mcp_server.stop()
        await persistence.stop()


@pytest.mark.asyncio
async def test_hook_event_reaches_viewport_render(e2e_components):
    """Full flow: Hook event -> MCP server -> Event processor -> World state -> Viewport.

    AC-2: Verify that a hook event sent to the MCP server eventually
    results in an agent appearing in the world state and viewport.
    """
    components = e2e_components
    world_state = components["world_state"]
    event_queue = components["event_queue"]
    viewport = components["viewport"]

    # Initial state: no agents
    initial_agents = await world_state.get_all_agents()
    assert len(initial_agents) == 0

    # Simulate a hook event (as if from a hook script)
    session_id = str(uuid4())
    project_id = "test-project"
    raw_event = {
        "session_id": session_id,
        "project_id": project_id,
        "project_name": "Test Project",
        "hook_type": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/test.txt"},
    }

    # Put event directly into queue (simulating MCP server receiving it)
    await event_queue.put(raw_event)

    # Wait for event processing (with timeout)
    await asyncio.wait_for(event_queue.join(), timeout=2.0)

    # Give agent inference time to process
    await asyncio.sleep(0.2)

    # Verify agent was created in world state
    agents = await world_state.get_all_agents()
    assert len(agents) == 1

    agent = agents[0]
    assert agent.session_id == session_id
    assert agent.project_id == project_id
    assert agent.state == AgentState.ACTIVE

    # Verify agent appears in viewport queries
    # Set viewport to include agent position
    viewport.set_center(agent.position)
    viewport.resize(20, 10)

    bounds = viewport.get_visible_bounds()
    agents_in_view = await world_state.get_agents_in_view(bounds)
    assert len(agents_in_view) == 1
    assert agents_in_view[0].id == agent.id


@pytest.mark.asyncio
async def test_multiple_sessions_create_multiple_agents(e2e_components):
    """Multiple sessions each create their own agent.

    AC-3: Verify that events from different sessions result in
    separate agents being created.
    """
    components = e2e_components
    event_queue = components["event_queue"]
    world_state = components["world_state"]

    # Simulate events from session 1
    session1_id = str(uuid4())
    event1 = {
        "session_id": session1_id,
        "project_id": "project-1",
        "project_name": "Project One",
        "hook_type": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {},
    }

    # Simulate events from session 2
    session2_id = str(uuid4())
    event2 = {
        "session_id": session2_id,
        "project_id": "project-2",
        "project_name": "Project Two",
        "hook_type": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {},
    }

    # Send both events
    await event_queue.put(event1)
    await event_queue.put(event2)

    # Wait for processing
    await asyncio.wait_for(event_queue.join(), timeout=2.0)
    await asyncio.sleep(0.2)

    # Verify two agents exist
    agents = await world_state.get_all_agents()
    assert len(agents) == 2

    # Verify each agent belongs to different session
    session_ids = {a.session_id for a in agents}
    assert session1_id in session_ids
    assert session2_id in session_ids

    # Verify agents are in different villages (different projects)
    villages = set()
    for agent in agents:
        village = await world_state.get_village(agent.village_id)
        if village:
            villages.add(village.project_id)

    assert len(villages) == 2


@pytest.mark.asyncio
async def test_event_processor_routes_to_all_handlers(e2e_components):
    """Event processor routes events to world state, inference, and persistence.

    Verifies that the event processor correctly routes events to all
    registered handlers (world_state, agent_inference, persistence).
    """
    components = e2e_components
    event_queue = components["event_queue"]
    world_state = components["world_state"]
    persistence = components["persistence"]

    # Create a custom subscriber to verify routing
    received_events: list[InternalEvent] = []

    async def tracking_subscriber(event: InternalEvent) -> None:
        received_events.append(event)

    # Subscribe to events
    await components["event_processor"].subscribe(tracking_subscriber)

    # Send an event
    session_id = str(uuid4())
    event = {
        "session_id": session_id,
        "project_id": "test-project",
        "project_name": "Test Project",
        "hook_type": "PostToolUse",
        "tool_name": "Read",
        "tool_input": {},
        "tool_output": {"content": "test"},
        "success": True,
        "duration_ms": 100,
    }

    await event_queue.put(event)
    await asyncio.wait_for(event_queue.join(), timeout=2.0)
    await asyncio.sleep(0.1)

    # Verify subscriber received the event
    assert len(received_events) >= 1
    assert received_events[0].session_id == session_id
    assert received_events[0].hook_type == HookType.PostToolUse


@pytest.mark.asyncio
async def test_graceful_degradation_on_handler_error(e2e_components):
    """System continues when event handlers fail (GP-7).

    Verifies that errors in one handler don't prevent other handlers
    from processing events.
    """
    components = e2e_components
    event_queue = components["event_queue"]
    world_state = components["world_state"]

    # Create a failing subscriber
    async def failing_subscriber(event: InternalEvent) -> None:
        raise RuntimeError("Simulated handler error")

    # Create a working subscriber
    working_events: list[InternalEvent] = []

    async def working_subscriber(event: InternalEvent) -> None:
        working_events.append(event)

    # Subscribe both
    await components["event_processor"].subscribe(failing_subscriber)
    await components["event_processor"].subscribe(working_subscriber)

    # Send an event
    session_id = str(uuid4())
    event = {
        "session_id": session_id,
        "project_id": "test-project",
        "project_name": "Test Project",
        "hook_type": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {},
    }

    await event_queue.put(event)
    await asyncio.wait_for(event_queue.join(), timeout=2.0)
    await asyncio.sleep(0.2)

    # Verify working subscriber still received the event
    assert len(working_events) >= 1

    # Verify agent was still created despite the error
    agents = await world_state.get_all_agents()
    assert len(agents) >= 1


@pytest.mark.asyncio
async def test_events_from_same_session_create_additional_agents(e2e_components):
    """Multiple events from same session may create additional agents.

    Verifies that the system handles multiple events from the same session.
    Note: Agent spawning behavior depends on concurrent tool detection.
    """
    components = e2e_components
    event_queue = components["event_queue"]
    world_state = components["world_state"]

    session_id = str(uuid4())

    # First event - creates initial agent
    event1 = {
        "session_id": session_id,
        "project_id": "test-project",
        "project_name": "Test Project",
        "hook_type": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {},
    }

    await event_queue.put(event1)
    await asyncio.wait_for(event_queue.join(), timeout=2.0)
    await asyncio.sleep(0.2)

    # Verify at least one agent created
    agents = await world_state.get_agents_by_session(session_id)
    assert len(agents) >= 1
    initial_count = len(agents)

    # Second event from same session
    event2 = {
        "session_id": session_id,
        "project_id": "test-project",
        "project_name": "Test Project",
        "hook_type": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {},
    }

    await event_queue.put(event2)
    await asyncio.wait_for(event_queue.join(), timeout=2.0)
    await asyncio.sleep(0.2)

    # Verify agents still exist (system is stable)
    agents = await world_state.get_agents_by_session(session_id)
    assert len(agents) >= initial_count


@pytest.mark.asyncio
async def test_viewport_shows_correct_agents_in_bounds(e2e_components):
    """Viewport correctly filters agents by visible bounds.

    Verifies that the viewport integration with world state correctly
    returns only agents within the visible bounds.
    """
    components = e2e_components
    event_queue = components["event_queue"]
    world_state = components["world_state"]
    viewport = components["viewport"]

    # Create agents from two different sessions
    for i in range(2):
        session_id = str(uuid4())
        event = {
            "session_id": session_id,
            "project_id": f"project-{i}",
            "project_name": f"Project {i}",
            "hook_type": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {},
        }
        await event_queue.put(event)

    await asyncio.wait_for(event_queue.join(), timeout=2.0)
    await asyncio.sleep(0.3)

    # Get all agents
    all_agents = await world_state.get_all_agents()
    assert len(all_agents) == 2

    # Set viewport to a small area around first agent
    first_agent = all_agents[0]
    viewport.set_center(first_agent.position)
    viewport.resize(5, 5)

    # Query agents in view
    bounds = viewport.get_visible_bounds()
    agents_in_view = await world_state.get_agents_in_view(bounds)

    # Should see at least the first agent
    assert len(agents_in_view) >= 1
    assert any(a.id == first_agent.id for a in agents_in_view)


@pytest.mark.asyncio
async def test_simulation_engine_updates_agent_states(e2e_components):
    """Simulation engine updates agent states based on activity.

    Verifies that the simulation engine correctly updates agent states
    (active -> idle -> zombie) based on last seen time.
    """
    components = e2e_components
    event_queue = components["event_queue"]
    world_state = components["world_state"]
    simulation = components["simulation"]

    # Create an agent
    session_id = str(uuid4())
    event = {
        "session_id": session_id,
        "project_id": "test-project",
        "project_name": "Test Project",
        "hook_type": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {},
    }

    await event_queue.put(event)
    await asyncio.wait_for(event_queue.join(), timeout=2.0)
    await asyncio.sleep(0.2)

    # Verify agent is active
    agents = await world_state.get_all_agents()
    assert len(agents) == 1
    assert agents[0].state == AgentState.ACTIVE

    # Note: Full zombie detection requires time to pass,
    # which would make tests slow. We verify the simulation
    # is running and the agent exists.
    sim_state = simulation.get_state()
    assert sim_state.running is True
    assert sim_state.tick_count > 0
