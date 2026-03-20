# WI-130 Status — Create plugin MCP server

## Files Created

- `/Users/dan/code/hamlet/mcp/server.py` — Standalone MCP server exposing `hamlet_init` tool via stdio transport. Includes `# /// script` metadata with `mcp>=1.0.0` dependency. No hamlet package imports.
- `/Users/dan/code/hamlet/mcp/start.sh` — Launch script using `uv run --script` if uv is available, falling back to `python3`.

## Executable Permissions Confirmed

```
-rwxr-xr-x  mcp/server.py
-rwxr-xr-x  mcp/start.sh
```

Both files have executable bit set (chmod +x applied).

## mcp Dependency in pyproject.toml

`mcp>=1.0.0` is already listed in the `[project] dependencies` section of `/Users/dan/code/hamlet/pyproject.toml`. No changes needed.

## Implementation Notes

- `hamlet_init` creates `.hamlet/config.json` with a random UUID `project_id`, `project_name` derived from `Path.cwd().name`, and `server_url` set to `http://localhost:8080/hamlet/event`.
- If `.hamlet/config.json` already exists, the tool returns its contents without overwriting.
- `mcp/start.sh` uses `$CLAUDE_PLUGIN_ROOT` to locate `server.py` at runtime.
