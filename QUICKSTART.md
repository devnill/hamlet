# Hamlet Quickstart

## Prerequisites

- Python 3.12+
- `pip install hamlet` (or `pip install -e .` for development installs)

## Step 1: Initialize your project (one-time per project)

**If you have the hamlet Claude Code plugin installed:**

Inside a Claude Code session, run:

```
/hamlet:init
```

This invokes the `hamlet_init` MCP skill, which creates `.hamlet/config.json` in your project with a unique project ID. The daemon uses this ID to track the project as its own village.

**Otherwise (CLI fallback):**

```bash
hamlet init
```

## Step 2: Connect Claude Code (one-time global setup)

**If you used the hamlet plugin (`/hamlet:init`):** hooks are registered automatically — skip this step.

**Otherwise:**

```bash
hamlet install
```

Restart Claude Code after running this command to load the new hooks.

## Step 3: Start the daemon (in a separate terminal or background)

```bash
hamlet daemon
```

The daemon runs the HTTP event server and simulation engine. Keep this running while you work.

## Step 4: Open the viewer (in your working terminal)

```bash
hamlet
# or: hamlet view
```

The viewer connects to the running daemon. Agents appear in the village as you use Claude Code.

## Verifying the connection

```bash
curl http://localhost:8080/hamlet/health
# {"status": "ok"}
```

If `hamlet daemon` isn't running, the curl will fail and hooks will fail silently without affecting Claude Code.

## Optional config

`~/.hamlet/config.json`:

```json
{
  "mcp_port": 8080,
  "db_path": "~/.hamlet/world.db",
  "tick_rate": 30.0,
  "theme": "default",
  "event_log_max_entries": 1000,
  "activity_model": "claude-haiku-4-5-20251001"
}
```
