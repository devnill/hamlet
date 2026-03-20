---
## Refinement Interview — 2026-03-19

**Context**: Post-convergence open items from brrr session (plugin delivery cycle). User requested all open items be addressed. Architect confirmed that `hamlet daemon` and `hamlet` CLI commands already exist, so that open item is resolved with no work required.

**Q: Item 5 (hook utility duplication) was accepted as a P2 trade-off in WI-170. Do you want to extract to a shared module, or keep it deferred?**
A: Let's keep it DRY. If something breaks, it should be handled then.

**Q: For the mcp import check improvement, should I verify against the actual import in mcp/server.py and use that symbol?**
A: Let you pick whatever the most pythonic option is.

**Decision**: Use `from mcp.server import Server` — matches the actual import in mcp/server.py and verifies the core class is available, not just the top-level namespace.

**Scope confirmed:**
1. Extract `_cwd_hash`, `find_server_url`, `find_config`, `_log_error` from the four hook scripts into `hooks/hamlet_hook_utils.py`. Import via `sys.path.insert(0, str(Path(__file__).parent))`.
2. Delete the four dead `.sh` wrapper files from `hooks/`.
3. Improve `mcp/start.sh` import check: `python3 -c "from mcp.server import Server"`.
4. Add `server_url` optional parameter to `hamlet_init` in `mcp/server.py`.

**Not changing**: All other source files. Architecture unchanged. Guiding principles unchanged.
