#!/usr/bin/env python3
# /// script
# dependencies = ["mcp>=1.0.0"]
# ///
"""Hamlet plugin MCP server — exposes hamlet_init tool."""
from __future__ import annotations
import asyncio
import json
import uuid
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("hamlet-config")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="hamlet_init",
            description=(
                "Initialize hamlet for the current project. Creates .hamlet/config.json "
                "with a unique project_id, project_name, and server_url. "
                "Optionally accepts a path argument to specify the project root "
                "(defaults to current working directory) and a server_url argument "
                "to set a custom daemon endpoint (defaults to http://localhost:8080/hamlet/event). "
                "Run this once per project before using hamlet."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project root directory. Defaults to current working directory."
                    },
                    "server_url": {
                        "type": "string",
                        "description": "URL of the hamlet daemon event endpoint. Defaults to http://localhost:8080/hamlet/event."
                    }
                },
                "required": []
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "hamlet_init":
        raise ValueError(f"Unknown tool: {name}")

    arguments = arguments or {}
    project_root = Path(arguments["path"]).resolve() if arguments.get("path") else Path.cwd()
    config_dir = project_root / ".hamlet"
    config_path = config_dir / "config.json"

    if config_path.exists():
        existing = json.loads(config_path.read_text())
        return [TextContent(
            type="text",
            text=(
                f"Hamlet config already exists at {config_path}:\n{json.dumps(existing, indent=2)}\n"
                "No changes made.\n\n"
                "To use a different host or port, edit server_url in .hamlet/config.json."
            )
        )]

    config_dir.mkdir(exist_ok=True)
    default_server_url = "http://localhost:8080/hamlet/event"
    config = {
        "project_id": str(uuid.uuid4()),
        "project_name": project_root.name,
        "server_url": arguments.get("server_url") or default_server_url
    }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    return [TextContent(
        type="text",
        text=(
            f"Created {config_path}:\n{json.dumps(config, indent=2)}\n\n"
            "Next steps:\n"
            "1. Start the hamlet daemon:  hamlet daemon\n"
            "2. Open the viewer:          hamlet\n"
            "The viewer will show your village as Claude Code agents work.\n\n"
            "To use a different host or port, edit server_url in .hamlet/config.json."
        )
    )]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
