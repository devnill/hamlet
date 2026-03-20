## WI-130 Incremental Review

### Verdict: FAIL

### Findings

- [CRITICAL] `mcp/start.sh:2` — `SCRIPT_DIR` is derived from `CLAUDE_PLUGIN_ROOT`, an environment variable that is never guaranteed to be set. If it is unset, `SCRIPT_DIR` resolves to `/mcp`, and both the `uv run` and `python3` branches will attempt to execute `/mcp/server.py`, which does not exist. The script should derive its own directory portably: `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`.

- [CRITICAL] `mcp/start.sh:6` — The `python3` fallback runs the script directly without installing the `mcp>=1.0.0` dependency declared in the `# /// script` block. `python3` does not process PEP 723 inline script metadata; it will fail at `from mcp.server import Server` unless the caller has already installed `mcp` into their system Python. The fallback either needs to install the dependency first (`pip install mcp`) or the fallback should be documented as unsupported without a pre-installed environment.

- [SIGNIFICANT] `mcp/server.py:52` — `server_url` is hardcoded to `"http://localhost:8080/hamlet/event"`. The tool accepts no arguments (empty `inputSchema`), so there is no mechanism for the caller to supply a real server URL. Any project running against a non-local hamlet server will have a wrong `server_url` written into its config on first init without any warning. If `server_url` must be configurable, the `inputSchema` must expose an optional `server_url` parameter with the localhost value as a default, or the acceptance criterion must explicitly allow this hardcoded value.

- [MINOR] `mcp/server.py:2-4` — The `# /// script` block does not include `requires-python`, which is recommended by PEP 723. Without it, `uv run --script` will pick whatever Python version is available, which may be incompatible with the `from __future__ import annotations` and async syntax used. Add `requires-python = ">=3.10"` (or `>=3.11` to match the rest of the project if applicable).

- [MINOR] `mcp/server.py:48` — `config_dir.mkdir(exist_ok=True)` does not pass `parents=True`. If for any reason the cwd itself does not exist at call time (edge case in some containerised or chroot environments), this will raise `FileNotFoundError`. Using `parents=True` costs nothing and is more robust.
