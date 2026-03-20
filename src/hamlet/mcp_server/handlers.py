"""MCP event notification handlers for Hamlet."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from mcp.server import Server
from mcp.types import AnyUrl, Resource, TextContent, Tool

from .validation import validate_event

logger = logging.getLogger(__name__)


def register_handlers(server: Server, event_queue: asyncio.Queue, world_state: Any) -> None:
    """Register all MCP notification handlers on the server."""
    _start_time = time.monotonic()

    @server.notification_handler("hamlet/event")
    async def handle_hamlet_event(params: dict[str, Any]) -> None:
        """Handle hamlet/event notifications from hook scripts."""
        try:
            # Reconstruct full JSON-RPC envelope for validation
            payload = {"jsonrpc": "2.0", "method": "hamlet/event", "params": params}
            result = validate_event(payload)
            if result.valid:
                # Enqueue only the params dict — consumers expect the flat event fields
                await event_queue.put(result.payload["params"])
        except Exception as exc:
            logger.error("Unexpected error handling hamlet/event: %s", exc, exc_info=True)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available MCP tools."""
        return [
            Tool(
                name="hamlet_status",
                description="Returns Hamlet server status including event queue size and uptime.",
                inputSchema={"type": "object", "properties": {}},
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Dispatch MCP tool calls."""
        try:
            if name == "hamlet_status":
                uptime = time.monotonic() - _start_time
                status = {
                    "queue_size": event_queue.qsize(),
                    "uptime_seconds": round(uptime, 3),
                }
                return [TextContent(type="text", text=json.dumps(status))]
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
        except Exception as exc:
            logger.error("Unexpected error calling tool %s: %s", name, exc, exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(exc)}))]

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        """List available MCP resources."""
        return [
            Resource(
                uri=AnyUrl("hamlet://world"),
                name="World State",
                mimeType="application/json",
            )
        ]

    @server.read_resource()
    async def read_resource(uri: AnyUrl) -> str:
        """Read an MCP resource by URI."""
        try:
            if str(uri) == "hamlet://world":
                if world_state is None:
                    return json.dumps({"error": "world_state not configured"})
                projects = await world_state.get_projects()
                agents = await world_state.get_all_agents()
                structures = await world_state.get_all_structures()
                summary = {
                    "projects": [p.id for p in projects],
                    "agents": [a.id for a in agents],
                    "structures": [s.id for s in structures],
                }
                return json.dumps(summary)
            return json.dumps({"error": f"Unknown resource: {uri}"})
        except Exception as exc:
            logger.error("Unexpected error reading resource %s: %s", uri, exc, exc_info=True)
            return json.dumps({"error": str(exc)})
