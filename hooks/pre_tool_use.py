#!/usr/bin/env python3
"""Send PreToolUse event to Hamlet MCP server."""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hamlet_hook_utils import find_server_url, find_config, _log_error

TIMING_DIR = Path.home() / ".hamlet" / "timing"


def record_start_time(session_id, tool_name):
    """Write a temp file with current timestamp for duration tracking."""
    try:
        TIMING_DIR.mkdir(parents=True, exist_ok=True)
        key = f"{session_id}_{tool_name}"
        (TIMING_DIR / key).write_text(str(time.time()))
    except Exception:
        pass


def main():
    """Send PreToolUse event and exit cleanly."""
    try:
        server_url = find_server_url()
        hook_input = json.load(sys.stdin)
        project_id, project_name = find_config()

        session_id = hook_input.get("session_id", "")
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input")

        record_start_time(session_id, tool_name)

        payload = {
            "jsonrpc": "2.0",
            "method": "hamlet/event",
            "params": {
                "hook_type": "PreToolUse",
                "session_id": session_id,
                "project_id": project_id,
                "project_name": project_name,
                "tool_name": tool_name,
                "tool_input": tool_input,
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
        _log_error("PreToolUse", exc)  # GP-7: log but fail silently to Claude Code
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
