# Hamlet

Terminal-based idle game for Claude Code agent activity visualization.

![Screenshot placeholder](docs/screenshot.png)

## What is Hamlet?

Hamlet turns your Claude Code sessions into a living ASCII village. Each agent becomes a `@` character that moves, works, and builds structures in real-time. Watch your codebase come alive as agents construct buildings, roads, and settlements.

## Installation

```bash
pip install hamlet
```

Requires Python 3.12+ and Claude Code.

## Quick Start

1. **Install hooks** (one-time setup):
   ```bash
   hamlet install
   ```

2. **Run Hamlet**:
   ```bash
   hamlet
   ```

3. **Use Claude Code normally** - your village will grow as you work!

## Usage

- `hamlet install` — inject hooks into `~/.claude/settings.json` (skips if plugin already active)
- `hamlet uninstall` — remove hooks from `~/.claude/settings.json`
- `hamlet daemon` — start backend server
- `hamlet` or `hamlet view` — open TUI viewer (daemon must be running)
- `hamlet init` — initialize hamlet for current project

## Controls

In the TUI viewer:

- Arrow keys or `h/j/k/l` — scroll viewport
- `f` — toggle follow mode
- `/` — toggle legend
- `?` — toggle help
- `q` — quit

## Configuration

Edit `~/.hamlet/config.json`:

```json
{
  "db_path": "~/.hamlet/world.db",
  "mcp_port": 8080,
  "tick_rate": 30.0,
  "theme": "default",
  "event_log_max_entries": 1000
}
```

## Requirements

- Python 3.12+
- Claude Code

## How It Works

- 15 hook types (PreToolUse, PostToolUse, Notification, Stop, SessionStart, SessionEnd, SubagentStart, SubagentStop, TeammateIdle, TaskCompleted, PostToolUseFailure, UserPromptSubmit, PreCompact, PostCompact, StopFailure) send Claude Code events to Hamlet
- Hooks are configured via `hamlet install` (writes to `~/.claude/settings.json`) or automatically via the Claude Code plugin (no manual setup needed)
- Agent inference detects spawns and activity types
- World simulation advances construction and animations
- TUI renders the ASCII village at 30 FPS
- SQLite persists your world across sessions

## Troubleshooting

**Hamlet won't start**
- Check Python version: `python --version` (need 3.12+)
- Try: `pip install --upgrade hamlet`

**Agents not appearing**
- Run `hamlet install` to configure hooks
- Check Claude Code is using the hooks

**Village not persisting**
- Check `~/.hamlet/` directory exists and is writable

## Uninstall

```bash
hamlet uninstall
pip uninstall hamlet
```

## License

MIT
