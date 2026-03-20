# Decision Log — Cycle 1 (Plugin Transition, 2026-03-19)

**Cycle**: 2026-03-19
**Work items**: WI-166 through WI-168 (plugin hooks transition)
**Review verdict**: Fail — 3 critical, 3 significant findings across code quality and gap analysis.

---

## Decisions Made

### D69: Switch to async:true for all plugin hooks
All four hook entries in hooks/hooks.json use "async": true. This matches the behavior of the previous inline hooks in settings.json. The Python scripts already guarantee non-blocking behavior via sys.exit(0) in finally and a 1-second HTTP timeout, making async redundant for correctness but consistent with the prior configuration.

### D70: Remove inline hooks from ~/.claude/settings.json
The four PreToolUse/PostToolUse/Notification/Stop inline jq+curl hooks removed from ~/.claude/settings.json. Plugin hooks are now the sole delivery mechanism. extraKnownMarketplaces and all other keys preserved.

### D71: Register hamlet in marketplace with version 0.1.0
hamlet entry added to devnill/claude-marketplace with source github, repo devnill/hamlet. Version 0.1.0 matches .claude-plugin/plugin.json. Repo not yet published — entry is pre-staged for when it goes public.

---

## Findings Requiring Action

### F1 (Critical): Hook scripts not executable (gap-analysis C1)
hooks/pre_tool_use.py, post_tool_use.py, notification.py, stop.py must have execute permission (+x) to be invoked directly as commands via hooks.json. No mechanism ensures this on fresh clone or plugin install.

### F2 (Critical): start.sh uses ${BASH_SOURCE[0]} but invoked via sh (gap-analysis C2)
mcp/start.sh uses bash-only BASH_SOURCE array. mcp.json invokes via "command": "sh". On dash/POSIX sh, SCRIPT_DIR becomes empty and exec fails. MCP server cannot start on non-bash systems.

### F3 (Critical/Significant): plugin.json mcpServers path ambiguity (code-quality C1)
"./.claude-plugin/mcp.json" in plugin.json — resolution semantics need verification. If resolved from plugin.json's directory (.claude-plugin/), path becomes .claude-plugin/.claude-plugin/mcp.json which doesn't exist. Also: hooks path "./hooks/hooks.json" has the same ambiguity. Both paths work only if resolved from repo root.

### F4 (Significant): server_url from hamlet_init never read by hooks (gap-analysis S1)
mcp/server.py writes server_url to project .hamlet/config.json. find_server_url() in hooks reads only from ~/.hamlet/config.json (global). server_url in project config is dead.

### F5 (Significant): No onboarding path after plugin install (gap-analysis S2)
No guidance delivered to user after install to run hamlet_init, start daemon, or open viewer. P11 partially unmet.

### F6 (Significant): async:true on PreToolUse removes blocking capability permanently (code-quality S1)
Per design decision D69 — intentional by user request. Flagged here for record. PreToolUse is telemetry-only.

---

## Open Questions

### Q1: What is Claude Code's path resolution root for plugin.json fields?
Does Claude Code resolve "hooks" and "mcpServers" relative to the repo root or relative to plugin.json's directory (.claude-plugin/)? Resolution determines whether current paths in plugin.json are correct or need adjustment.

### Q2: Does hamlet need a README or CLAUDE.md for onboarding?
Given P11, some mechanism should guide users from "plugin installed" to "hamlet running." Options: hamlet_init response text, a skills/ directory with a /hamlet:start skill, a README in the plugin.

---

## Carried-Forward Open Questions (from prior cycles)

OQ1-OQ5 from prior session decision logs remain open (server-side concerns not touched this cycle).
