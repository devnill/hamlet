#!/usr/bin/env python3
"""Send SubagentStart event to Hamlet MCP server."""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hamlet_hook_utils import find_server_url, find_config, _log_error


def main():
    """Send SubagentStart event and exit cleanly."""
    try:
        hook_input = json.load(sys.stdin)
        cwd = hook_input.get("cwd", "")
        if cwd and os.path.isdir(cwd):
            os.chdir(cwd)
        server_url = find_server_url()
        project_id, project_name = find_config()

        payload = {
            "jsonrpc": "2.0",
            "method": "hamlet/event",
            "params": {
                "hook_type": "SubagentStart",
                "session_id": hook_input.get("session_id", ""),
                "project_id": project_id,
                "project_name": project_name,
                "agent_id": hook_input.get("agent_id", ""),
                "agent_type": hook_input.get("agent_type", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

        req = urllib.request.Request(
            server_url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=1)
    except Exception as exc:
        _log_error("SubagentStart", exc)  # GP-7: log but fail silently to Claude Code
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
