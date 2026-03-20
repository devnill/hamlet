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

Hamlet receives events via Claude Code hooks. Run the install command to configure all 15 hook types automatically:

```bash
hamlet install
```

If the hamlet Claude Code plugin is already installed, hooks are registered automatically — `hamlet install` will detect this and skip writing to `settings.json`.

After installing, **restart Claude Code** to load the new hooks. Then start working normally — agents will appear in the village as you use tools.

## Verifying the Connection

```bash
curl http://localhost:8080/hamlet/health
# {"status": "ok"}
```

If Hamlet isn't running, the hooks fail silently (`|| true`) and Claude Code is unaffected.
