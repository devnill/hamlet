"""Tests for type inference rules and sliding window (work item 024).

Test framework: pytest + pytest-asyncio.
Run with: pytest tests/test_type_inference.py -v
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from hamlet.event_processing.internal_event import HookType, InternalEvent
from hamlet.inference.engine import AgentInferenceEngine
from hamlet.inference.rules import TYPE_RULES
from hamlet.inference.types import AgentType, ToolWindow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    session_id: str | None = None,
    tool_name: str = "Bash",
    hook_type: HookType = HookType.PostToolUse,
    event_id: str | None = None,
    duration_ms: int | None = None,
    tool_input: dict | None = None,
) -> InternalEvent:
    """Return a minimal InternalEvent for testing."""
    return InternalEvent(
        id=event_id or str(uuid4()),
        sequence=1,
        received_at=datetime.now(UTC),
        session_id=session_id or str(uuid4()),
        project_id="proj-1",
        project_name="test-project",
        hook_type=hook_type,
        tool_name=tool_name,
        tool_input=tool_input if tool_input is not None else {},
        duration_ms=duration_ms,
    )


def _make_world_state() -> MagicMock:
    """Return a mock WorldStateManager."""
    ws = MagicMock()
    mock_session = MagicMock()
    mock_session.id = str(uuid4())

    mock_agent = MagicMock()
    mock_agent.id = str(uuid4())
    mock_agent.last_seen = datetime.now(UTC)

    ws.get_or_create_session = AsyncMock(return_value=mock_session)
    ws.get_or_create_agent = AsyncMock(return_value=mock_agent)
    ws.get_agents_by_session = AsyncMock(return_value=[mock_agent])
    ws.update_agent = AsyncMock(return_value=None)
    ws.add_work_units = AsyncMock(return_value=None)
    return ws


def _engine_with_window(
    session_id: str,
    tool_names: list[str],
    tool_inputs: list[str] | None = None,
) -> tuple[AgentInferenceEngine, MagicMock]:
    """Create an engine and pre-populate its tool window with *tool_names*.

    *tool_inputs* is an optional parallel list of input strings for input_log.
    When omitted, empty strings are used so TESTER refinement is exercised
    but no test keywords are present (Bash events stay EXECUTOR).
    """
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    state = engine.get_inference_state()
    now = datetime.now(UTC)
    inputs = tool_inputs if tool_inputs is not None else [""] * len(tool_names)
    state.tool_windows[session_id] = ToolWindow(
        session_id=session_id,
        events=[(name, now) for name in tool_names],
        input_log=[(name, inp, now) for name, inp in zip(tool_names, inputs)],
    )
    return engine, ws


# ---------------------------------------------------------------------------
# Tests: TYPE_RULES structure
# ---------------------------------------------------------------------------


def test_type_rules_has_four_entries():
    assert len(TYPE_RULES) == 4


def test_type_rules_researcher_entry():
    patterns, ratio, agent_type = TYPE_RULES[0]
    assert set(patterns) == {"Read", "Grep", "Glob"}
    assert ratio == 0.6
    assert agent_type == AgentType.RESEARCHER


def test_type_rules_coder_entry():
    patterns, ratio, agent_type = TYPE_RULES[1]
    assert set(patterns) == {"Write", "Edit"}
    assert ratio == 0.6
    assert agent_type == AgentType.CODER


def test_type_rules_executor_entry():
    patterns, ratio, agent_type = TYPE_RULES[2]
    assert set(patterns) == {"Bash"}
    assert ratio == 0.5
    assert agent_type == AgentType.EXECUTOR


def test_type_rules_architect_entry():
    patterns, ratio, agent_type = TYPE_RULES[3]
    assert set(patterns) == {"Task"}
    assert ratio == 0.4
    assert agent_type == AgentType.ARCHITECT


# ---------------------------------------------------------------------------
# Tests: _infer_type
# ---------------------------------------------------------------------------


def test_infer_type_returns_general_with_no_window():
    """Session with no ToolWindow at all → GENERAL."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    result = engine._infer_type("nonexistent-session")
    assert result == AgentType.GENERAL


def test_infer_type_returns_general_with_fewer_than_10_events():
    """Fewer than 10 events in the window → GENERAL regardless of tool mix."""
    session_id = str(uuid4())
    # 9 Read events — would qualify as RESEARCHER if there were 10+
    engine, _ = _engine_with_window(session_id, ["Read"] * 9)
    result = engine._infer_type(session_id)
    assert result == AgentType.GENERAL


def test_infer_type_returns_general_with_exactly_9_events():
    session_id = str(uuid4())
    engine, _ = _engine_with_window(session_id, ["Bash"] * 9)
    assert engine._infer_type(session_id) == AgentType.GENERAL


def test_infer_type_returns_researcher_when_read_grep_glob_ratio_meets_threshold():
    """10 events, 7 Read → ratio 0.7 ≥ 0.6 → RESEARCHER."""
    session_id = str(uuid4())
    tools = ["Read"] * 7 + ["Bash"] * 3
    engine, _ = _engine_with_window(session_id, tools)
    assert engine._infer_type(session_id) == AgentType.RESEARCHER


def test_infer_type_researcher_mixed_grep_glob():
    """Grep and Glob also count toward RESEARCHER."""
    session_id = str(uuid4())
    tools = ["Grep"] * 4 + ["Glob"] * 3 + ["Bash"] * 3
    engine, _ = _engine_with_window(session_id, tools)
    # 7/10 = 0.7 ≥ 0.6
    assert engine._infer_type(session_id) == AgentType.RESEARCHER


def test_infer_type_returns_coder_when_write_edit_ratio_meets_threshold():
    """10 events, 6 Write → ratio 0.6 ≥ 0.6 → CODER."""
    session_id = str(uuid4())
    tools = ["Write"] * 6 + ["Bash"] * 4
    engine, _ = _engine_with_window(session_id, tools)
    assert engine._infer_type(session_id) == AgentType.CODER


def test_infer_type_coder_edit_counts():
    """Edit also counts toward CODER."""
    session_id = str(uuid4())
    tools = ["Edit"] * 7 + ["Bash"] * 3
    engine, _ = _engine_with_window(session_id, tools)
    assert engine._infer_type(session_id) == AgentType.CODER


def test_infer_type_returns_executor_when_bash_ratio_meets_threshold():
    """10 events, 6 Bash → ratio 0.6 ≥ 0.5 → EXECUTOR (first matching rule wins)."""
    session_id = str(uuid4())
    tools = ["Bash"] * 6 + ["Task"] * 4
    engine, _ = _engine_with_window(session_id, tools)
    # Bash rule has minimum_ratio=0.5 and comes before Task rule
    assert engine._infer_type(session_id) == AgentType.EXECUTOR


def test_infer_type_returns_architect_when_task_ratio_meets_threshold():
    """10 events, 5 Task → ratio 0.5 ≥ 0.4 → ARCHITECT."""
    session_id = str(uuid4())
    tools = ["Task"] * 5 + ["Read"] * 5
    engine, _ = _engine_with_window(session_id, tools)
    # Read is 0.5 which does NOT meet RESEARCHER threshold (0.6)
    # Task is 0.5 which DOES meet ARCHITECT threshold (0.4)
    assert engine._infer_type(session_id) == AgentType.ARCHITECT


def test_infer_type_returns_general_when_no_rule_matches():
    """Even with 10+ events, return GENERAL when no rule's threshold is met."""
    session_id = str(uuid4())
    # 3 Read (0.3 < 0.6), 3 Write (0.3 < 0.6), 2 Bash (0.2 < 0.5), 2 Task (0.2 < 0.4)
    tools = ["Read"] * 3 + ["Write"] * 3 + ["Bash"] * 2 + ["Task"] * 2
    engine, _ = _engine_with_window(session_id, tools)
    assert engine._infer_type(session_id) == AgentType.GENERAL


def test_infer_type_first_matching_rule_wins():
    """When multiple rules could match, the first rule in TYPE_RULES wins."""
    session_id = str(uuid4())
    # 6 Read (0.6 ≥ 0.6 → RESEARCHER) + 4 Task (0.4 ≥ 0.4 → ARCHITECT) — both rules match.
    # RESEARCHER is rule 0, ARCHITECT is rule 3 → RESEARCHER wins (first match).
    tools = ["Read"] * 6 + ["Task"] * 4
    engine, _ = _engine_with_window(session_id, tools)
    # RESEARCHER rule comes before ARCHITECT in TYPE_RULES → RESEARCHER wins
    assert engine._infer_type(session_id) == AgentType.RESEARCHER


def test_infer_type_exactly_at_threshold():
    """Ratio exactly equal to minimum_ratio should qualify."""
    session_id = str(uuid4())
    # 6 Bash out of 10 → ratio 0.6 ≥ 0.5 → EXECUTOR
    tools = ["Bash"] * 6 + ["Read"] * 4
    engine, _ = _engine_with_window(session_id, tools)
    assert engine._infer_type(session_id) == AgentType.EXECUTOR


def test_infer_type_just_below_threshold():
    """Ratio just below minimum_ratio should NOT qualify."""
    session_id = str(uuid4())
    # 5 Read, 4 Bash, 1 Write — no rule meets its minimum_ratio
    # Read: 5/10=0.5 < 0.6, Write: 1/10=0.1 < 0.6, Bash: 4/10=0.4 < 0.5, Task: 0 < 0.4
    tools = ["Read"] * 5 + ["Bash"] * 4 + ["Write"] * 1
    engine, _ = _engine_with_window(session_id, tools)
    assert engine._infer_type(session_id) == AgentType.GENERAL


# ---------------------------------------------------------------------------
# Tests: _update_tool_window
# ---------------------------------------------------------------------------


def test_update_tool_window_adds_event_to_new_window():
    """_update_tool_window creates a ToolWindow and adds the event."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    event = _make_event(tool_name="Read")

    engine._update_tool_window(event)

    state = engine.get_inference_state()
    assert event.session_id in state.tool_windows
    window = state.tool_windows[event.session_id]
    assert len(window.events) == 1
    assert window.events[0][0] == "Read"


def test_update_tool_window_appends_to_existing_window():
    """Subsequent calls append additional events."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    session_id = str(uuid4())

    for tool in ["Read", "Grep", "Bash"]:
        engine._update_tool_window(_make_event(session_id=session_id, tool_name=tool))

    state = engine.get_inference_state()
    names = [name for name, _ in state.tool_windows[session_id].events]
    assert names == ["Read", "Grep", "Bash"]


def test_update_tool_window_prunes_old_events():
    """Events older than window_size are removed when new events are added."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    session_id = str(uuid4())

    # Pre-populate window with an event 10 minutes in the past (outside 5-min window).
    old_ts = datetime.now(UTC) - timedelta(minutes=10)
    state = engine.get_inference_state()
    state.tool_windows[session_id] = ToolWindow(
        session_id=session_id,
        events=[("OldTool", old_ts)],
    )

    # Adding a new current event should prune the old one.
    engine._update_tool_window(_make_event(session_id=session_id, tool_name="Read"))

    window = state.tool_windows[session_id]
    assert len(window.events) == 1
    assert window.events[0][0] == "Read"


def test_update_tool_window_keeps_recent_events():
    """Events within window_size are not pruned."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    session_id = str(uuid4())

    # Event 1 minute ago — inside the 5-minute window.
    recent_ts = datetime.now(UTC) - timedelta(minutes=1)
    state = engine.get_inference_state()
    state.tool_windows[session_id] = ToolWindow(
        session_id=session_id,
        events=[("RecentTool", recent_ts)],
    )

    engine._update_tool_window(_make_event(session_id=session_id, tool_name="Bash"))

    window = state.tool_windows[session_id]
    assert len(window.events) == 2


def test_update_tool_window_handles_none_tool_name():
    """Events with no tool_name are stored as empty string without error."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    event = _make_event(tool_name=None)  # type: ignore[arg-type]

    engine._update_tool_window(event)

    state = engine.get_inference_state()
    assert state.tool_windows[event.session_id].events[0][0] == ""


# ---------------------------------------------------------------------------
# Tests: _handle_post_tool_use (integration)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_post_tool_use_calls_update_tool_window_and_infer_type():
    """_handle_post_tool_use populates the tool window."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    event = _make_event(tool_name="Read")

    await engine._handle_post_tool_use(event)

    state = engine.get_inference_state()
    assert event.session_id in state.tool_windows
    assert len(state.tool_windows[event.session_id].events) == 1


@pytest.mark.asyncio
async def test_handle_post_tool_use_updates_agent_when_type_inferred():
    """When enough events exist, _handle_post_tool_use updates the agent type."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)

    session_id = str(uuid4())
    # Pre-seed session state with an agent_id so update_agent is called.
    from hamlet.inference.types import SessionState
    state = engine.get_inference_state()
    state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=["agent-xyz"],
    )

    # Pre-seed 9 Read events so the 10th (added by handle_post_tool_use) triggers RESEARCHER.
    now = datetime.now(UTC)
    state.tool_windows[session_id] = ToolWindow(
        session_id=session_id,
        events=[("Read", now)] * 9,
    )

    event = _make_event(session_id=session_id, tool_name="Read")
    await engine._handle_post_tool_use(event)

    from hamlet.world_state.types import AgentType as WSAgentType
    ws.update_agent.assert_awaited_once_with(
        "agent-xyz", inferred_type=WSAgentType.RESEARCHER, color="cyan"
    )


@pytest.mark.asyncio
async def test_handle_post_tool_use_no_agent_does_not_call_update():
    """With no agent_ids on the session, update_agent is not called."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    event = _make_event(tool_name="Bash")

    # No session pre-seeded → agent_ids list will be empty / session absent
    await engine._handle_post_tool_use(event)

    ws.update_agent.assert_not_called()


@pytest.mark.asyncio
async def test_handle_post_tool_use_update_agent_error_does_not_raise():
    """If update_agent raises, _handle_post_tool_use swallows the error gracefully."""
    from unittest.mock import AsyncMock
    ws = _make_world_state()
    ws.update_agent = AsyncMock(side_effect=RuntimeError("db error"))
    engine = AgentInferenceEngine(ws)

    session_id = str(uuid4())
    from hamlet.inference.types import SessionState
    state = engine.get_inference_state()
    state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=["agent-abc"],
    )
    # Pre-seed 9 events so the 10th triggers type inference
    now = datetime.now(UTC)
    state.tool_windows[session_id] = ToolWindow(
        session_id=session_id,
        events=[("Read", now)] * 9,
    )

    event = _make_event(session_id=session_id, tool_name="Read")
    # Must not raise even though update_agent raises
    await engine._handle_post_tool_use(event)


# ---------------------------------------------------------------------------
# Tests: TESTER detection (post-rule refinement)
# ---------------------------------------------------------------------------


def test_tester_detection_overrides_executor_when_majority_bash_has_test_keywords():
    """EXECUTOR is overridden to TESTER when ≥50% of Bash events contain test keywords."""
    session_id = str(uuid4())
    # 6 Bash (0.6 ≥ 0.5 → EXECUTOR by rule), 4 Read — EXECUTOR before refinement.
    # 4 of 6 Bash inputs contain "pytest" (4/6 = 0.667 ≥ 0.5) → promoted to TESTER.
    tool_names = ["Bash"] * 6 + ["Read"] * 4
    tool_inputs = ["pytest tests/"] * 4 + ["ls -la"] * 2 + [""] * 4
    engine, _ = _engine_with_window(session_id, tool_names, tool_inputs)
    assert engine._infer_type(session_id) == AgentType.TESTER


def test_tester_detection_at_exactly_50_percent_threshold():
    """Exactly 50% test-keyword Bash events meets the threshold → TESTER."""
    session_id = str(uuid4())
    # 10 Bash (1.0 ≥ 0.5 → EXECUTOR), 5 with pytest, 5 without → 5/10 = 0.5 exactly.
    tool_names = ["Bash"] * 10
    tool_inputs = ["pytest tests/"] * 5 + ["echo hello"] * 5
    engine, _ = _engine_with_window(session_id, tool_names, tool_inputs)
    assert engine._infer_type(session_id) == AgentType.TESTER


def test_tester_detection_below_threshold_stays_executor():
    """Below 50% test-keyword Bash events → stays EXECUTOR."""
    session_id = str(uuid4())
    # 10 Bash → EXECUTOR; 4/10 = 0.4 < 0.5 → no promotion.
    tool_names = ["Bash"] * 10
    tool_inputs = ["pytest tests/"] * 4 + ["make build"] * 6
    engine, _ = _engine_with_window(session_id, tool_names, tool_inputs)
    assert engine._infer_type(session_id) == AgentType.EXECUTOR


def test_tester_detection_no_bash_events_stays_executor():
    """No Bash events in input_log → TESTER refinement skipped → EXECUTOR."""
    session_id = str(uuid4())
    # 6 Bash (via tool_names) but input_log has empty strings → no test keywords.
    tool_names = ["Bash"] * 6 + ["Read"] * 4
    engine, _ = _engine_with_window(session_id, tool_names)  # no tool_inputs → empty strings
    assert engine._infer_type(session_id) == AgentType.EXECUTOR


def test_tester_detection_unittest_keyword_triggers():
    """'unittest' keyword in Bash input also triggers TESTER promotion."""
    session_id = str(uuid4())
    tool_names = ["Bash"] * 10
    tool_inputs = ["python -m unittest discover"] * 6 + ["git status"] * 4
    engine, _ = _engine_with_window(session_id, tool_names, tool_inputs)
    assert engine._infer_type(session_id) == AgentType.TESTER


# ---------------------------------------------------------------------------
# Tests: work unit accumulation (_handle_post_tool_use)
# ---------------------------------------------------------------------------


def _pre_seed_session(engine: AgentInferenceEngine, session_id: str, agent_id: str) -> None:
    """Pre-seed a session with one agent so the work-unit block is reachable."""
    from hamlet.inference.types import SessionState
    state = engine.get_inference_state()
    state.sessions[session_id] = SessionState(
        session_id=session_id,
        project_id="proj-1",
        agent_ids=[agent_id],
    )
    now = datetime.now(UTC)
    state.tool_windows[session_id] = ToolWindow(
        session_id=session_id,
        events=[("Bash", now)] * 9,
        input_log=[("Bash", "", now)] * 9,
    )


@pytest.mark.asyncio
async def test_work_units_none_duration_ms_gives_1():
    """When duration_ms is None, work units are 1 (minimum floor for any completed tool call)."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    session_id, agent_id = str(uuid4()), "agent-wu-1"
    _pre_seed_session(engine, session_id, agent_id)

    from hamlet.world_state.types import StructureType
    event = _make_event(session_id=session_id, tool_name="Bash", duration_ms=None)
    await engine._handle_post_tool_use(event)

    ws.add_work_units.assert_awaited_once_with(agent_id, StructureType.FORGE, 1)


@pytest.mark.asyncio
async def test_work_units_formula_500ms():
    """duration_ms=500 → max(1, int(500 * 1.0)) = 500 work units."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    session_id, agent_id = str(uuid4()), "agent-wu-2"
    _pre_seed_session(engine, session_id, agent_id)

    from hamlet.world_state.types import StructureType
    event = _make_event(session_id=session_id, tool_name="Bash", duration_ms=500)
    await engine._handle_post_tool_use(event)

    ws.add_work_units.assert_awaited_once_with(agent_id, StructureType.FORGE, 500)


@pytest.mark.asyncio
async def test_work_units_formula_small_duration():
    """duration_ms=99 → max(1, int(99 * 1.0)) = 99 work units."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    session_id, agent_id = str(uuid4()), "agent-wu-3"
    _pre_seed_session(engine, session_id, agent_id)

    from hamlet.world_state.types import StructureType
    event = _make_event(session_id=session_id, tool_name="Bash", duration_ms=99)
    await engine._handle_post_tool_use(event)

    ws.add_work_units.assert_awaited_once_with(agent_id, StructureType.FORGE, 99)


@pytest.mark.asyncio
async def test_work_units_read_tool_maps_to_library():
    """Read tool maps to LIBRARY structure type."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    session_id, agent_id = str(uuid4()), "agent-wu-4"
    # Pre-seed with Read events for RESEARCHER inference
    from hamlet.inference.types import SessionState
    state = engine.get_inference_state()
    state.sessions[session_id] = SessionState(
        session_id=session_id, project_id="proj-1", agent_ids=[agent_id]
    )
    now = datetime.now(UTC)
    state.tool_windows[session_id] = ToolWindow(
        session_id=session_id,
        events=[("Read", now)] * 9,
        input_log=[("Read", "", now)] * 9,
    )

    from hamlet.world_state.types import StructureType
    event = _make_event(session_id=session_id, tool_name="Read", duration_ms=200)
    await engine._handle_post_tool_use(event)

    ws.add_work_units.assert_awaited_once_with(agent_id, StructureType.LIBRARY, 200)


@pytest.mark.asyncio
async def test_work_units_unknown_tool_name_skipped():
    """Tool not in TOOL_TO_STRUCTURE → add_work_units not called."""
    ws = _make_world_state()
    engine = AgentInferenceEngine(ws)
    session_id, agent_id = str(uuid4()), "agent-wu-5"
    _pre_seed_session(engine, session_id, agent_id)

    event = _make_event(session_id=session_id, tool_name="Task")
    await engine._handle_post_tool_use(event)

    ws.add_work_units.assert_not_called()
