# Code Quality Review — Cycle 1 (Plugin Hooks Transition)

Scope: cross-cutting review of WI-166, WI-167, WI-168 — hooks.json async configuration,
plugin manifest wiring, and marketplace registration.

---

## Verdict: Fail

The `mcpServers` path in `plugin.json` is self-referential and resolves to a non-existent location, which will prevent the MCP server from starting under the plugin system.

## Critical Findings

### C1: `mcpServers` path in `plugin.json` is self-referential and will not resolve

- **File**: `/Users/dan/code/hamlet/.claude-plugin/plugin.json:9`
- **Issue**: `plugin.json` lives at `<repo>/.claude-plugin/plugin.json`. The `mcpServers` field is:
  ```json
  "mcpServers": "./.claude-plugin/mcp.json"
  ```
  If Claude Code resolves this path relative to the directory containing `plugin.json`
  (`.claude-plugin/`), the resolved path is `<repo>/.claude-plugin/.claude-plugin/mcp.json`,
  which does not exist. The actual `mcp.json` is at `<repo>/.claude-plugin/mcp.json`,
  i.e., the same directory as `plugin.json`. The correct relative reference would be
  `"./mcp.json"`.

  The `hooks` field has the same resolution question but in the opposite direction:
  ```json
  "hooks": "./hooks/hooks.json"
  ```
  If resolved relative to `.claude-plugin/`, this would be
  `<repo>/.claude-plugin/hooks/hooks.json`, which does not exist. If resolved relative
  to the repo root, it resolves correctly to `<repo>/hooks/hooks.json`.

  The two fields are therefore inconsistent with each other: one uses a path that only
  works from the repo root, the other uses a path that only works from the repo root
  but names a subdirectory (`./claude-plugin/`) that repeats the containing directory.
  At least one of the two paths is wrong regardless of which resolution root Claude
  Code applies.

- **Impact**: The MCP server (hamlet-config) will fail to start when the plugin is
  installed via the marketplace, because `mcp.json` cannot be found at the referenced
  path. The `hamlet_init` tool will be unavailable, breaking the plugin's setup flow.

- **Suggested fix**: Since both files are in the same directory, change `plugin.json` to:
  ```json
  "mcpServers": "./.claude-plugin/mcp.json"
  ```
  should become:
  ```json
  "mcpServers": "./mcp.json"
  ```
  if Claude Code resolves relative to plugin.json's containing directory. Alternatively,
  if Claude Code resolves relative to the repo root, both fields are correct and no
  change is needed — but in that case the `mcpServers` value `./.claude-plugin/mcp.json`
  resolves to `<repo>/.claude-plugin/mcp.json` which does exist. Verify the resolution
  semantics against Claude Code plugin documentation and adjust accordingly.

## Significant Findings

### S1: `async: true` on `PreToolUse` makes the 5-second `timeout` inoperative and eliminates any future ability to block tool execution

- **File**: `/Users/dan/code/hamlet/hooks/hooks.json:3-13`
- **Issue**: Claude Code's `async: true` flag causes the hook to be fired without
  waiting for its exit. The `timeout: 5` field is therefore inoperative for async
  hooks — Claude Code will not enforce it because it does not wait for the process.
  For `PreToolUse` specifically, async mode also permanently removes the ability to
  block or modify a tool call (e.g., to reject a destructive operation in the future).
  The hook scripts themselves already guarantee non-blocking behaviour via `sys.exit(0)`
  in a `finally` block and a 1-second HTTP timeout, so `async: true` is redundant for
  correctness but removes a safety valve.

- **Impact**: If a future Hamlet feature needs to inspect or gate PreToolUse events
  (e.g., blocking writes to protected paths), the async flag would need to be removed
  and all downstream latency impact re-evaluated. The current architecture bakes in a
  design constraint that is not documented as intentional.

- **Suggested fix**: Document the decision explicitly in hooks.json or a companion
  README: async is intentional, telemetry-only, and PreToolUse will never block.
  If this is not a deliberate permanent constraint, remove `async: true` from
  `PreToolUse` and rely on the existing 1-second HTTP timeout in the script for
  graceful degradation.

## Minor Findings

### M1: Timing file key includes raw tool_name, which may contain path separators

- **File**: `/Users/dan/code/hamlet/hooks/pre_tool_use.py:53-54`
- **Issue**: The timing file key is constructed as `f"{session_id}_{tool_name}"` and
  written as a filename under `~/.hamlet/timing/`. If `tool_name` contains `/` or
  other filesystem-special characters, `Path(TIMING_DIR / key)` will either create
  nested directories or raise an error. Claude Code tool names in practice are simple
  identifiers (e.g., `Bash`, `Read`) so this is low-probability, but the assumption
  is not validated.
- **Suggested fix**: Sanitize the key before use:
  ```python
  key = f"{session_id}_{tool_name}".replace("/", "_").replace("\x00", "_")
  ```

### M2: `find_server_url` and `find_config` are duplicated verbatim across all four hook scripts

- **Files**:
  - `/Users/dan/code/hamlet/hooks/pre_tool_use.py:19-46`
  - `/Users/dan/code/hamlet/hooks/post_tool_use.py:19-46`
  - `/Users/dan/code/hamlet/hooks/notification.py:15-42`
  - `/Users/dan/code/hamlet/hooks/stop.py:15-42`
- **Issue**: `find_server_url()`, `find_config()`, `_cwd_hash()`, and `_log_error()`
  are identical across all four files. A bug fix or behaviour change in any of these
  functions must be applied in four places.
- **Suggested fix**: Extract to a shared `hamlet_hook_utils.py` module in the same
  `hooks/` directory and import it. Each hook script already uses `#!/usr/bin/env python3`
  so a local import works without any packaging.

### M3: Marketplace entry version does not match plugin.json version (both 0.1.0 — acceptable — but source field omits branch/tag)

- **File**: `/Users/dan/code/claude-marketplace/.claude-plugin/marketplace.json:59-66`
- **Issue**: The hamlet entry uses `"source": "github"` with only `"repo"`, no `"branch"`
  or `"tag"` field. The version is declared as `0.1.0` but the marketplace installer
  will pull whatever is on the default branch at install time, which may not correspond
  to the declared version as the repo evolves.
- **Suggested fix**: Pin the source to a tag or commit SHA once `0.1.0` is tagged:
  ```json
  "source": {
    "source": "github",
    "repo": "devnill/hamlet",
    "tag": "v0.1.0"
  }
  ```

## Unmet Acceptance Criteria

None.
