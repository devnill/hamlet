"""Internal event data structure for normalized hook events."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class HookType(Enum):
    """Types of hook events from Claude Code.

    Each hook type corresponds to a specific point in the Claude Code
    tool execution lifecycle.
    """
    PreToolUse = "PreToolUse"
    PostToolUse = "PostToolUse"
    Notification = "Notification"
    Stop = "Stop"


@dataclass
class InternalEvent:
    """Normalized event structure for internal processing.

    This dataclass represents a hook event that has been validated,
    normalized, and enriched with sequence numbers and timestamps.

    Attributes:
        id: UUID string uniquely identifying this event.
        sequence: Monotonic sequence number assigned during processing.
        received_at: Timestamp when the event was received.
        session_id: UUID of the Claude Code session that generated this event.
        project_id: ID of the project (codebase) this event belongs to.
        project_name: Human-readable name of the project.
        hook_type: Type of hook that generated this event.
        tool_name: Name of the tool (for PreToolUse/PostToolUse), or None.
        tool_input: Tool input parameters, or None.
        tool_output: Tool output data (for PostToolUse), or None.
        success: Whether the tool call succeeded (for PostToolUse), or None.
        duration_ms: Duration of tool call in milliseconds, or None.
        raw_payload: Original event payload for debugging.
    """
    id: str
    sequence: int
    received_at: datetime
    session_id: str
    project_id: str
    project_name: str
    hook_type: HookType
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    success: bool | None = None
    duration_ms: int | None = None
    notification_message: str | None = None
    stop_reason: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate event fields after initialization.

        Raises:
            ValueError: If hook_type is invalid or id is empty.
        """
        if not self.id:
            raise ValueError("Event id cannot be empty")

        if not isinstance(self.hook_type, HookType):
            raise ValueError(
                f"Invalid hook_type: {self.hook_type}. "
                f"Must be one of: {[h.value for h in HookType]}"
            )

