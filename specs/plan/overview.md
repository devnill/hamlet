# Change Plan — Refinement 2026-03-19 (refine-6: Open Items)

## Trigger
Post-convergence cleanup of deferred items from the plugin delivery brrr session. User requested all open items be addressed.

## Correction: hamlet CLI already exists
The open item "hamlet daemon/hamlet CLI don't exist yet" was a false finding. Both `hamlet daemon` and `hamlet` (no args → viewer) are fully implemented in `src/hamlet/cli/`. No work required for this item.

## What Is Changing

1. **Extract hook utilities** (`hooks/hamlet_hook_utils.py` + 4 hook scripts): `_cwd_hash`, `find_server_url`, `find_config`, and `_log_error` are duplicated across all four hook scripts. Extracting them to a shared module eliminates ~200 lines of duplicated code and ensures any future change to config-lookup logic needs to happen in exactly one place.

2. **Remove dead `.sh` wrapper files**: `hooks/pre_tool_use.sh`, `hooks/post_tool_use.sh`, `hooks/notification.sh`, and `hooks/stop.sh` are not referenced by `hooks.json` or any other config. They are dead code.

3. **Improve mcp import check** (`mcp/start.sh`): The current check `python3 -c "import mcp"` succeeds for a broken install where only the mcp namespace exists. Changing to `python3 -c "from mcp.server import Server"` verifies the specific class used by `mcp/server.py` is importable.

4. **Add `server_url` parameter to `hamlet_init`** (`mcp/server.py`): Users running hamlet on a non-default port/host currently must edit `.hamlet/config.json` manually after init. Adding an optional `server_url` input parameter allows setting it at init time.

## Scope Boundary

**Not changing**: `src/hamlet/` (all application code), tests, `hooks/hooks.json`, `.claude-plugin/`, `mcp/start.sh` (except the import check line), the daemon, TUI, world state, persistence, or the marketplace files.

## Expected Impact

After this cycle:
- Hook utility code lives in one file; any config-lookup change touches `hamlet_hook_utils.py` only
- The `hooks/` directory contains only files that are actually used
- `mcp/start.sh` gives a more accurate diagnostic for broken mcp installs
- `hamlet_init` accepts `server_url` at init time

## New Work Items
WI-174 through WI-177 (all independent, all low complexity)
