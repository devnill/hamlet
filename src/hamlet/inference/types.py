"""Core types and data structures for the inference module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from hamlet.world_state.types import AgentType


class InferenceAction(Enum):
    """Action to take based on inference result."""

    SPAWN = "spawn"
    UPDATE = "update"
    COMPLETE = "complete"
    IDLE = "idle"


@dataclass
class InferenceResult:
    """Result of processing an event through the inference engine."""

    action: InferenceAction
    agent_id: str | None = None
    parent_id: str | None = None
    inferred_type: AgentType = AgentType.GENERAL
    position: tuple[int, int] | None = None  # (x, y) or None


@dataclass
class PendingTool:
    """A tool call that has been seen in PreToolUse but not yet PostToolUse."""

    session_id: str
    tool_name: str
    tool_input: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    estimated_agent_id: str | None = None


@dataclass
class SessionState:
    """State tracked for a single Claude Code session."""

    session_id: str
    project_id: str
    agent_ids: list[str] = field(default_factory=list)
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    active_tools: int = 0
    first_seen: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ToolWindow:
    """Sliding window of recent tool usage for type inference."""

    session_id: str
    events: list[tuple[str, datetime]] = field(default_factory=list)
    # Parallel log storing (tool_name, tool_input_str, timestamp) for rules that
    # need to inspect tool inputs (e.g. TESTER detection on Bash commands).
    input_log: list[tuple[str, str, datetime]] = field(default_factory=list)
    window_size: timedelta = field(default_factory=lambda: timedelta(minutes=5))


@dataclass
class InferenceState:
    """Global inference engine state."""

    pending_tools: dict[str, PendingTool] = field(default_factory=dict)
    sessions: dict[str, SessionState] = field(default_factory=dict)
    tool_windows: dict[str, ToolWindow] = field(default_factory=dict)
    last_seen: dict[str, datetime] = field(default_factory=dict)
    zombie_since: dict[str, datetime] = field(default_factory=dict)


TYPE_COLORS: dict[AgentType, str] = {
    AgentType.RESEARCHER: "cyan",
    AgentType.CODER: "yellow",
    AgentType.EXECUTOR: "orange1",
    AgentType.ARCHITECT: "magenta",
    AgentType.TESTER: "blue",
    AgentType.PLANNER: "dark_green",
    AgentType.GENERAL: "white",
}

__all__ = [
    "AgentType",
    "InferenceAction",
    "InferenceResult",
    "PendingTool",
    "SessionState",
    "ToolWindow",
    "InferenceState",
    "TYPE_COLORS",
]
