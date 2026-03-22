# hamlet — Developer Notes

## Installation and Updates

hamlet is installed via pipx. **Source code changes do not take effect until you reinstall.**

```bash
pipx install --force /Users/dan/code/hamlet   # reinstall from local source
```

After reinstalling, restart the service:

```bash
hamlet service stop && hamlet service start
```

Or in one step:

```bash
pipx install --force /Users/dan/code/hamlet && hamlet service stop && hamlet service start
```

Check the installed version:

```bash
pipx list | grep hamlet
hamlet service status
```

## Running

Start the daemon first, then the viewer as a separate process:

```bash
hamlet daemon          # or: python -m hamlet daemon
hamlet                 # or: hamlet view  (connects to running daemon)
```

The daemon and viewer are separate processes. The viewer will not work without a running daemon.

The production daemon runs as a launchd service:

```bash
hamlet service status    # check if running
hamlet service start     # start the service
hamlet service stop      # stop the service
hamlet service restart   # stop then start (note: use stop && start if restart fails)
```

## Testing

Run from the project root:

```bash
pytest
pytest --tb=short      # with coverage/short tracebacks
```

- `asyncio_mode = "auto"` is set in `pyproject.toml` — do not add `@pytest.mark.asyncio` decorators; they are unnecessary and may cause warnings
- Test files live in `tests/`, named `test_{module}.py`
- Hook scripts call `sys.exit(0)` in their `finally` blocks — tests must either catch `SystemExit` or mock `sys.exit`

## Architecture

**Event pipeline order:**

```
Hook Script → HTTP POST → MCPServer (aiohttp) → asyncio.Queue
    → EventProcessor → WorldStateManager
                     → AgentInferenceEngine
                     → PersistenceFacade
```

**Two separate MCP servers** (commonly confused):
- `mcp/server.py` — the plugin MCP server, stdio transport, exposes the `hamlet_init` tool to Claude Code
- `src/hamlet/mcp_server/server.py` — the application's HTTP event endpoint (aiohttp), receives hook events; this is what hook scripts POST to

**WorldStateManager locking:**
- All world state mutations acquire `self._lock` (`asyncio.Lock`, not `threading.RLock`)
- Use `async with self._lock` — the lock is not re-entrant
- Methods that acquire `self._lock` must not call other methods that also acquire it (deadlock)

**Hook script pattern** (stdlib only, no venv):

Hooks that receive a `cwd` field (all v0.4.0+ hooks: SessionStart, SessionEnd, SubagentStart, SubagentStop, TeammateIdle, TaskCompleted, PostToolUseFailure, UserPromptSubmit, PreCompact, PostCompact, StopFailure):
```python
hook_input = json.load(sys.stdin)
cwd = hook_input.get("cwd", "")
if cwd and os.path.isdir(cwd):
    os.chdir(cwd)
server_url = find_server_url()
project_id, project_name = find_config()
# build payload, then:
urllib.request.urlopen(req, timeout=1)
finally:
    sys.exit(0)
```

Original hooks (PreToolUse, PostToolUse, Notification, Stop) call `find_server_url()` before reading stdin and do not use `os.chdir`.

## Gotchas

- **PreToolUse and PreCompact are synchronous hooks** — no `"async": true` in `hooks.json`. They block Claude Code until they return. All other hooks are async.

- **`sys.exit(0)` in all hook `finally` blocks** — this is intentional (silent failure). Tests that call hook `main()` functions must catch `SystemExit` or mock `sys.exit`.

- **asyncio.Lock is not re-entrant** — `WorldStateManager._lock` is an `asyncio.Lock`. Calling an internal method that also acquires the lock from within a locked section will deadlock. Do not refactor methods to call each other if both acquire the lock.

- **`persistence/saver.py` was deleted** — this file was removed in WI-194 (startup deduplication). Do not reference or recreate it.

- **Hook scripts use stdlib only** — hooks run outside the venv, so they use `urllib.request` instead of `aiohttp`. Do not add third-party imports to hook scripts.

- **Hook error logging** — hook errors are logged to `~/.hamlet/hooks.log`, not to stderr. If a hook silently fails, check there first.
