"""Event schema validation for Hamlet MCP server."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError, validate

logger = logging.getLogger(__name__)

EVENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["jsonrpc", "method", "params"],
    "properties": {
        "jsonrpc": {"type": "string", "const": "2.0"},
        "method": {"type": "string", "const": "hamlet/event"},
        "params": {
            "type": "object",
            "required": ["session_id", "timestamp", "hook_type", "project_id"],
            "properties": {
                "session_id": {"type": "string"},
                "timestamp": {
                    "type": "string",
                    "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
                },
                "hook_type": {
                    "type": "string",
                    "enum": ["PreToolUse", "PostToolUse", "Notification", "Stop", "SessionStart", "SessionEnd", "SubagentStart", "SubagentStop", "TeammateIdle", "TaskCompleted", "PostToolUseFailure", "UserPromptSubmit", "PreCompact", "PostCompact", "StopFailure"],
                },
                "project_id": {"type": "string"},
                "project_name": {"type": "string"},
                "tool_name": {"type": ["string", "null"]},
                "tool_input": {"type": ["object", "null"]},
                "tool_output": {"type": ["object", "string", "null"]},
                "success": {"type": ["boolean", "null"]},
                "duration_ms": {"type": ["integer", "null"]},
                "notification_type": {"type": ["string", "null"]},
                "notification_message": {"type": ["string", "null"]},
                "stop_reason": {"type": ["string", "null"]},
                "agent_id": {"type": ["string", "null"]},
                "agent_type": {"type": ["string", "null"]},
                "source": {"type": ["string", "null"]},
                "reason": {"type": ["string", "null"]},
                "task_id": {"type": ["string", "null"]},
                "task_subject": {"type": ["string", "null"]},
                "task_description": {"type": ["string", "null"]},
                "teammate_name": {"type": ["string", "null"]},
                "error": {"type": ["object", "string", "null"]},
                "is_interrupt": {"type": ["boolean", "null"]},
                "prompt": {"type": ["string", "null"]},
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}


@dataclass
class ValidationResult:
    """Result of validating an incoming hook event payload."""

    valid: bool
    payload: dict[str, Any] | None
    error: str | None


def validate_event(payload: dict[str, Any]) -> ValidationResult:
    """Validate an incoming MCP hook event payload.

    Returns a ValidationResult. If invalid, logs at WARN level and returns
    a result with valid=False. Never raises.
    """
    try:
        validate(instance=payload, schema=EVENT_SCHEMA)
        return ValidationResult(valid=True, payload=payload, error=None)
    except ValidationError as exc:
        logger.warning("Invalid event payload discarded: %s", exc.message)
        return ValidationResult(valid=False, payload=None, error=exc.message)
    except Exception as exc:
        logger.warning("Unexpected validation error: %s", exc, exc_info=True)
        return ValidationResult(valid=False, payload=None, error=str(exc))


__all__ = ["ValidationResult", "validate_event", "EVENT_SCHEMA"]
