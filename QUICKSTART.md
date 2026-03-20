# Hamlet Quickstart

## Prerequisites

- Python 3.12+
- A virtual environment with dependencies installed (`pip install -e .` from the repo root)

## Running Hamlet

```bash
.venv/bin/hamlet
```

Or equivalently:

```bash
.venv/bin/python -m hamlet
```

Hamlet opens a Textual TUI and starts an HTTP server on `http://localhost:8080`. The village populates as Claude Code sessions send events.

**Optional config** (`~/.hamlet/config.json`, created automatically on first run):

```json
{
  "mcp_port": 8080,
  "db_path": "~/.hamlet/world.db",
  "tick_rate": 30.0
}
```

## Connecting Claude Code

Hamlet receives events via HTTP hooks. Add the following to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "jq -c --arg ht 'PreToolUse' --arg ts \"$(date -u +%Y-%m-%dT%H:%M:%S)\" '{\"jsonrpc\":\"2.0\",\"method\":\"hamlet/event\",\"params\":(. + {\"hook_type\":$ht,\"timestamp\":$ts,\"project_id\":(.project_id // \"\"),\"project_name\":(.project_name // \"\")})}' | curl -s -X POST http://localhost:8080/hamlet/event -H 'Content-Type: application/json' -d @- 2>/dev/null || true",
            "async": true
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "jq -c --arg ht 'PostToolUse' --arg ts \"$(date -u +%Y-%m-%dT%H:%M:%S)\" '{\"jsonrpc\":\"2.0\",\"method\":\"hamlet/event\",\"params\":(. + {\"hook_type\":$ht,\"timestamp\":$ts,\"project_id\":(.project_id // \"\"),\"project_name\":(.project_name // \"\")})}' | curl -s -X POST http://localhost:8080/hamlet/event -H 'Content-Type: application/json' -d @- 2>/dev/null || true",
            "async": true
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "jq -c --arg ht 'Notification' --arg ts \"$(date -u +%Y-%m-%dT%H:%M:%S)\" '{\"jsonrpc\":\"2.0\",\"method\":\"hamlet/event\",\"params\":(. + {\"hook_type\":$ht,\"timestamp\":$ts,\"project_id\":(.project_id // \"\"),\"project_name\":(.project_name // \"\")})}' | curl -s -X POST http://localhost:8080/hamlet/event -H 'Content-Type: application/json' -d @- 2>/dev/null || true",
            "async": true
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "jq -c --arg ht 'Stop' --arg ts \"$(date -u +%Y-%m-%dT%H:%M:%S)\" '{\"jsonrpc\":\"2.0\",\"method\":\"hamlet/event\",\"params\":(. + {\"hook_type\":$ht,\"timestamp\":$ts,\"project_id\":(.project_id // \"\"),\"project_name\":(.project_name // \"\")})}' | curl -s -X POST http://localhost:8080/hamlet/event -H 'Content-Type: application/json' -d @- 2>/dev/null || true",
            "async": true
          }
        ]
      }
    ]
  }
}
```

Merge this into any existing `hooks` block — don't replace the whole file.

After saving, **restart Claude Code** (or open `/hooks` in the UI) to load the new hooks. Then start working normally — agents will appear in the village as you use tools.

## Verifying the Connection

```bash
curl http://localhost:8080/hamlet/health
# {"status": "ok"}
```

If Hamlet isn't running, the hooks fail silently (`|| true`) and Claude Code is unaffected.
