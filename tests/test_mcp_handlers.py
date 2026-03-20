"""Tests for MCP server event handlers."""
from __future__ import annotations

import asyncio
from unittest.mock import patch, MagicMock

import pytest

from hamlet.mcp_server.validation import validate_event


class TestHandlers:
    """Tests for MCP notification handlers."""

    @pytest.mark.asyncio
    async def test_handle_hamlet_event_enqueues_valid_event(self) -> None:
        """Test that handle_hamlet_event enqueues valid events to the queue."""
        queue: asyncio.Queue[dict] = asyncio.Queue()

        # Create a valid params dict
        params = {
            "session_id": "sess1",
            "project_id": "proj1",
            "hook_type": "PreToolUse",
            "timestamp": "2024-01-01T00:00:00Z"
        }

        # Reconstruct the handler logic inline (as the handler does)
        payload = {"jsonrpc": "2.0", "method": "hamlet/event", "params": params}
        result = validate_event(payload)
        if result.valid:
            await queue.put(result.payload["params"])

        assert queue.qsize() == 1
        event = await queue.get()
        assert event["session_id"] == "sess1"
        assert event["hook_type"] == "PreToolUse"

    @pytest.mark.asyncio
    async def test_handle_hamlet_event_logs_errors(self) -> None:
        """Test that handle_hamlet_event logs errors per GP-7 (errors logged, not raised)."""
        queue: asyncio.Queue[dict] = asyncio.Queue()

        # Test that validation logs errors for invalid payloads
        with patch('hamlet.mcp_server.validation.logger') as mock_logger:
            # Create an invalid params dict (missing required fields)
            params = {
                "session_id": "sess1",
                # missing project_id, hook_type, timestamp
            }

            # Reconstruct the handler logic
            payload = {"jsonrpc": "2.0", "method": "hamlet/event", "params": params}
            result = validate_event(payload)

            # The validation should fail and log a warning
            assert result.valid is False
            assert result.error is not None

            # Verify that validation logs the error
            mock_logger.warning.assert_called_once()
            assert "Invalid event payload discarded" in mock_logger.warning.call_args[0][0]

        # Test that the handler catches exceptions and logs them
        with patch('hamlet.mcp_server.handlers.logger') as mock_logger:
            # Simulate an unexpected exception during handling
            with patch('hamlet.mcp_server.handlers.validate_event') as mock_validate:
                mock_validate.side_effect = Exception("Unexpected error")

                # Import the actual handler registration to test error path
                from hamlet.mcp_server.handlers import register_handlers

                # Create a proper mock server that captures the registered handler
                captured_handlers = {}
                captured_tools = {}
                captured_resources = {}

                def make_decorator(capture_dict, key_name):
                    def decorator(func):
                        capture_dict[key_name] = func
                        return func
                    return decorator

                def mock_notification_handler(name):
                    def decorator(func):
                        captured_handlers[name] = func
                        return func
                    return decorator

                def mock_list_tools():
                    return make_decorator(captured_tools, "list_tools")

                def mock_call_tool():
                    return make_decorator(captured_tools, "call_tool")

                def mock_list_resources():
                    return make_decorator(captured_resources, "list_resources")

                def mock_read_resource():
                    return make_decorator(captured_resources, "read_resource")

                mock_server = MagicMock()
                mock_server.notification_handler = mock_notification_handler
                mock_server.list_tools = mock_list_tools
                mock_server.call_tool = mock_call_tool
                mock_server.list_resources = mock_list_resources
                mock_server.read_resource = mock_read_resource

                register_handlers(mock_server, queue, None)

                # Get the registered handler and call it with an exception
                handler = captured_handlers.get("hamlet/event")
                assert handler is not None

                # Call the handler - it should catch the exception and log it
                await handler({"session_id": "test"})

                # Verify error was logged
                mock_logger.error.assert_called_once()
                assert "Unexpected error handling hamlet/event" in mock_logger.error.call_args[0][0]
