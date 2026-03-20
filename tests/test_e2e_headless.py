"""Headless integration tests for Hamlet.

Starts the full backend stack (persistence, world state, simulation,
MCP HTTP server) with no TUI, and exercises it through the same HTTP
endpoint that the Claude Code hooks use.  These tests catch runtime
crashes that unit tests and mock-based tests cannot.

Run with: pytest tests/test_e2e_headless.py -v
"""
from __future__ import annotations

import asyncio
import socket
from datetime import UTC, datetime
from uuid import uuid4

import aiohttp
import pytest

from hamlet.event_processing.event_processor import EventProcessor
from hamlet.inference.engine import AgentInferenceEngine
from hamlet.mcp_server.server import MCPServer
from hamlet.persistence.facade import PersistenceFacade
from hamlet.persistence.types import PersistenceConfig
from hamlet.simulation.agent_updater import AgentUpdater
from hamlet.simulation.config import SimulationConfig
from hamlet.simulation.engine import SimulationEngine
from hamlet.world_state.manager import WorldStateManager
from hamlet.world_state.types import AgentState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _free_port() -> int:
    """Return a free TCP port on localhost."""
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _rpc_event(
    session_id: str,
    hook_type: str,
    project_id: str = "test-project",
    project_name: str = "Test Project",
    **kwargs,
) -> dict:
    """Build a valid JSON-RPC 2.0 hamlet event payload."""
    params: dict = {
        "session_id": session_id,
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S"),
        "hook_type": hook_type,
        "project_id": project_id,
        "project_name": project_name,
    }
    params.update(kwargs)
    return {"jsonrpc": "2.0", "method": "hamlet/event", "params": params}


async def _post(port: int, payload: dict) -> tuple[int, dict]:
    """POST payload to /hamlet/event; return (status_code, response_json)."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"http://localhost:{port}/hamlet/event",
            json=payload,
        ) as resp:
            return resp.status, await resp.json()


async def _get(port: int, path: str) -> tuple[int, dict]:
    """GET a path on the server; return (status_code, response_json)."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://localhost:{port}{path}") as resp:
            return resp.status, await resp.json()


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def backend(tmp_path):
    """Full backend stack with real HTTP server — no TUI.

    Yields a dict with:
        port        — the HTTP server port
        world_state — WorldStateManager
        simulation  — SimulationEngine
        persistence — PersistenceFacade
        db_path     — Path to the SQLite database
    """
    port = _free_port()
    db_path = tmp_path / "hamlet_test.db"

    persistence = PersistenceFacade(
        PersistenceConfig(db_path=str(db_path), write_queue_size=100)
    )
    await persistence.start()

    try:
        world_state = WorldStateManager(persistence)
        await world_state.load_from_persistence()

        agent_inference = AgentInferenceEngine(world_state)

        mcp_server = MCPServer(world_state=world_state, port=port)
        await mcp_server.start()

        event_queue = mcp_server.get_event_queue()
        event_processor = EventProcessor(
            event_queue=event_queue,
            world_state=world_state,
            agent_inference=agent_inference,
            persistence=persistence,
        )
        await event_processor.start()

        sim_config = SimulationConfig(tick_rate=10.0, zombie_threshold=300.0)
        agent_updater = AgentUpdater(sim_config)
        simulation = SimulationEngine(
            world_state,
            config=sim_config,
            agent_updater=agent_updater,
            agent_inference=agent_inference,
        )
        await simulation.start()

        yield {
            "port": port,
            "world_state": world_state,
            "persistence": persistence,
            "simulation": simulation,
            "db_path": db_path,
        }

    finally:
        await simulation.stop()
        await event_processor.stop()
        await mcp_server.stop()
        await persistence.stop()


# ---------------------------------------------------------------------------
# Tests: HTTP server basics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint(backend):
    """GET /hamlet/health returns 200 with status ok."""
    status, body = await _get(backend["port"], "/hamlet/health")
    assert status == 200
    assert body.get("status") == "ok"


@pytest.mark.asyncio
async def test_invalid_json_rpc_rejected(backend):
    """POST without required JSON-RPC fields returns 400."""
    status, body = await _post(backend["port"], {"session_id": "x", "hook_type": "PreToolUse"})
    assert status == 400
    assert "error" in body


@pytest.mark.asyncio
async def test_invalid_hook_type_rejected(backend):
    """POST with an unknown hook_type returns 400."""
    payload = _rpc_event(str(uuid4()), "UnknownHookType")
    status, body = await _post(backend["port"], payload)
    assert status == 400
    assert "error" in body


@pytest.mark.asyncio
async def test_get_to_event_endpoint_rejected(backend):
    """GET /hamlet/event (not POST) returns 405."""
    status, _ = await _get(backend["port"], "/hamlet/event")
    assert status == 405


# ---------------------------------------------------------------------------
# Tests: Event → world state
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pretooluse_event_creates_agent(backend):
    """PreToolUse event via HTTP results in an agent in world state."""
    port = backend["port"]
    world_state = backend["world_state"]

    session_id = str(uuid4())
    payload = _rpc_event(
        session_id,
        "PreToolUse",
        tool_name="Read",
        tool_input={"file_path": "/tmp/test.txt"},
    )

    status, body = await _post(port, payload)
    assert status == 200
    assert body.get("status") == "ok"

    # Give event processor time to handle it
    await asyncio.sleep(0.3)

    agents = await world_state.get_all_agents()
    assert len(agents) >= 1

    agent = next((a for a in agents if a.session_id == session_id), None)
    assert agent is not None
    assert agent.state == AgentState.ACTIVE


@pytest.mark.asyncio
async def test_posttooluse_event_processed(backend):
    """PostToolUse event is accepted and processed without error."""
    port = backend["port"]
    world_state = backend["world_state"]

    session_id = str(uuid4())

    # First create the session with PreToolUse
    pre = _rpc_event(session_id, "PreToolUse", tool_name="Write", tool_input={})
    await _post(port, pre)
    await asyncio.sleep(0.2)

    # Then send PostToolUse
    post = _rpc_event(
        session_id,
        "PostToolUse",
        tool_name="Write",
        tool_input={},
        success=True,
        duration_ms=150,
    )
    status, body = await _post(port, post)
    assert status == 200

    await asyncio.sleep(0.2)

    agents = await world_state.get_agents_by_session(session_id)
    assert len(agents) >= 1


@pytest.mark.asyncio
async def test_stop_event_processed(backend):
    """Stop event is accepted and does not crash the backend."""
    port = backend["port"]
    world_state = backend["world_state"]

    session_id = str(uuid4())

    # Create agent first
    pre = _rpc_event(session_id, "PreToolUse", tool_name="Bash", tool_input={})
    await _post(port, pre)
    await asyncio.sleep(0.2)

    # Send Stop
    stop = _rpc_event(session_id, "Stop", stop_reason="tool")
    status, body = await _post(port, stop)
    assert status == 200

    await asyncio.sleep(0.2)

    # Agent should still exist (stop doesn't delete it)
    agents = await world_state.get_agents_by_session(session_id)
    assert len(agents) >= 1


@pytest.mark.asyncio
async def test_notification_event_processed(backend):
    """Notification event is accepted and does not crash the backend."""
    port = backend["port"]

    session_id = str(uuid4())
    payload = _rpc_event(
        session_id,
        "Notification",
        notification_type="permission_request",
        notification_message="Allow bash?",
    )
    status, body = await _post(port, payload)
    assert status == 200


# ---------------------------------------------------------------------------
# Tests: Multi-session / multi-project
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_two_sessions_create_two_agents(backend):
    """Events from two different sessions produce two separate agents."""
    port = backend["port"]
    world_state = backend["world_state"]

    session_a = str(uuid4())
    session_b = str(uuid4())

    await _post(port, _rpc_event(session_a, "PreToolUse", project_id="proj-a", tool_name="Read", tool_input={}))
    await _post(port, _rpc_event(session_b, "PreToolUse", project_id="proj-b", tool_name="Write", tool_input={}))

    await asyncio.sleep(0.4)

    all_agents = await world_state.get_all_agents()
    session_ids = {a.session_id for a in all_agents}

    assert session_a in session_ids
    assert session_b in session_ids


@pytest.mark.asyncio
async def test_different_projects_get_separate_villages(backend):
    """Agents from different projects end up in different villages."""
    port = backend["port"]
    world_state = backend["world_state"]

    session_a = str(uuid4())
    session_b = str(uuid4())

    await _post(port, _rpc_event(session_a, "PreToolUse", project_id="alpha", project_name="Alpha", tool_name="Read", tool_input={}))
    await _post(port, _rpc_event(session_b, "PreToolUse", project_id="beta", project_name="Beta", tool_name="Read", tool_input={}))

    await asyncio.sleep(0.4)

    agents = await world_state.get_all_agents()
    assert len(agents) >= 2

    village_ids = {a.village_id for a in agents}
    # Two different projects → two different villages
    assert len(village_ids) == 2


@pytest.mark.asyncio
async def test_rapid_events_do_not_crash(backend):
    """Ten rapid-fire events from different sessions are all handled."""
    port = backend["port"]
    world_state = backend["world_state"]

    session_ids = [str(uuid4()) for _ in range(10)]

    # Fire all events concurrently
    results = await asyncio.gather(*[
        _post(port, _rpc_event(sid, "PreToolUse", project_id=f"proj-{i}", tool_name="Read", tool_input={}))
        for i, sid in enumerate(session_ids)
    ])

    # All requests should be accepted
    for status, body in results:
        assert status == 200

    await asyncio.sleep(0.8)

    # All sessions should have agents
    all_agents = await world_state.get_all_agents()
    seen_sessions = {a.session_id for a in all_agents}
    for sid in session_ids:
        assert sid in seen_sessions


# ---------------------------------------------------------------------------
# Tests: Simulation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simulation_is_running(backend):
    """Simulation engine starts and accumulates ticks."""
    simulation = backend["simulation"]
    await asyncio.sleep(0.3)
    state = simulation.get_state()
    assert state.running is True
    assert state.tick_count > 0


@pytest.mark.asyncio
async def test_simulation_ticks_while_processing_events(backend):
    """Simulation keeps ticking while events are being processed."""
    port = backend["port"]
    simulation = backend["simulation"]

    await asyncio.sleep(0.1)
    ticks_before = simulation.get_state().tick_count

    # Send a batch of events
    for _ in range(5):
        session_id = str(uuid4())
        await _post(port, _rpc_event(session_id, "PreToolUse", tool_name="Read", tool_input={}))

    await asyncio.sleep(0.3)
    ticks_after = simulation.get_state().tick_count

    assert ticks_after > ticks_before


# ---------------------------------------------------------------------------
# Tests: Persistence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agents_persist_across_restart(backend):
    """Agents created via HTTP survive a persistence stop/start cycle."""
    port = backend["port"]
    world_state = backend["world_state"]
    persistence = backend["persistence"]
    db_path = backend["db_path"]

    session_id = str(uuid4())
    await _post(port, _rpc_event(session_id, "PreToolUse", tool_name="Read", tool_input={}))
    await asyncio.sleep(0.3)

    agents_before = await world_state.get_all_agents()
    assert len(agents_before) >= 1

    # Flush to disk
    await persistence.checkpoint()
    await asyncio.sleep(0.2)

    # Load a fresh world state from the same DB
    new_persistence = PersistenceFacade(
        PersistenceConfig(db_path=str(db_path), write_queue_size=100)
    )
    await new_persistence.start()
    try:
        new_world = WorldStateManager(new_persistence)
        await new_world.load_from_persistence()

        agents_after = await new_world.get_all_agents()
        assert len(agents_after) == len(agents_before)

        restored_ids = {a.session_id for a in agents_after}
        assert session_id in restored_ids
    finally:
        await new_persistence.stop()


@pytest.mark.asyncio
async def test_event_log_populated(backend):
    """Events sent via HTTP appear in the world state event log."""
    port = backend["port"]
    world_state = backend["world_state"]

    session_id = str(uuid4())
    await _post(port, _rpc_event(session_id, "PreToolUse", tool_name="Read", tool_input={}))
    await asyncio.sleep(0.3)

    log = await world_state.get_event_log(limit=10)
    assert len(log) >= 1
