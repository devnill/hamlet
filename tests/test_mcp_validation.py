"""Tests for MCP server event validation."""
from __future__ import annotations

import pytest

from hamlet.mcp_server.validation import validate_event, ValidationResult


class TestValidation:
    """Tests for the validate_event function."""

    def test_validate_event_accepts_valid_payload(self) -> None:
        """Test that validate_event accepts a valid event payload."""
        payload = {
            "jsonrpc": "2.0",
            "method": "hamlet/event",
            "params": {
                "session_id": "sess1",
                "project_id": "proj1",
                "hook_type": "PreToolUse",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
        result = validate_event(payload)
        assert result.valid is True
        assert result.payload == payload
        assert result.error is None

    def test_validate_event_rejects_missing_jsonrpc(self) -> None:
        """Test that validate_event rejects payload missing jsonrpc field."""
        payload = {
            "method": "hamlet/event",
            "params": {}
        }
        result = validate_event(payload)
        assert result.valid is False
        assert result.payload is None
        assert result.error is not None
        assert "jsonrpc" in result.error

    def test_validate_event_rejects_invalid_hook_type(self) -> None:
        """Test that validate_event rejects invalid hook_type value."""
        payload = {
            "jsonrpc": "2.0",
            "method": "hamlet/event",
            "params": {
                "session_id": "sess1",
                "project_id": "proj1",
                "hook_type": "InvalidHookType",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
        result = validate_event(payload)
        assert result.valid is False
        assert result.payload is None
        assert result.error is not None
        assert "hook_type" in result.error or "'InvalidHookType'" in result.error
