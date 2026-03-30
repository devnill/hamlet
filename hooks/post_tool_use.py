#!/usr/bin/env python3
"""Send PostToolUse event to Hamlet MCP server."""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hamlet_hook_utils import find_server_url, find_config, _log_error

TIMING_DIR = Path.home() / ".hamlet" / "timing"


def compute_duration(session_id, tool_name):
    """Read timing temp file and return elapsed milliseconds."""
    key = f"{session_id}_{tool_name}"
    timing_file = TIMING_DIR / key
    if timing_file.exists():
        try:
            start = float(timing_file.read_text())
            timing_file.unlink()
            return int((time.time() - start) * 1000)
        except Exception:
            pass
    return None


def main():
    """Send PostToolUse event and exit cleanly."""
    try:
        server_url = find_server_url()
        hook_input = json.load(sys.stdin)
        project_id, project_name = find_config()

        session_id = hook_input.get("session_id", "")
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input")
        tool_output = hook_input.get("tool_output")
        success = hook_input.get("success", True)
        duration_ms = hook_input.get("duration_ms") or compute_duration(session_id, tool_name)

        params = {
            "hook_type": "PostToolUse",
            "session_id": session_id,
            "project_id": project_id,
            "project_name": project_name,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_output": tool_output,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        payload = {
            "jsonrpc": "2.0",
            "method": "hamlet/event",
            "params": params
        }

        req = urllib.request.Request(
            server_url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=1)
    except Exception as exc:
        _log_error("PostToolUse", exc)  # GP-7: log but fail silently to Claude Code
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
