## Verdict: Fail

The plugin has two critical gaps that prevent it from working on install: hook scripts lack guaranteed execute permission, and mcp/start.sh uses bash-specific BASH_SOURCE while invoked via sh.

## Critical Gaps

### C1: Hook scripts not guaranteed executable

The four hook scripts (pre_tool_use.py, post_tool_use.py, notification.py, stop.py) are registered in hooks/hooks.json as "type": "command", meaning Claude Code will invoke them directly as executables. The files contain shebangs (#!/usr/bin/env python3) but nothing ensures the execute bit is set. On a fresh clone or plugin install the files will have repository default permissions. Claude Code will receive EACCES when attempting to invoke them. The hooks will silently never fire.

There is no plugin.install hook, no post-install script, and no documented step to run `chmod +x`.

### C2: start.sh uses ${BASH_SOURCE[0]} but is invoked via sh

mcp/start.sh derives its directory with `$(dirname "${BASH_SOURCE[0]}")`. BASH_SOURCE is a bash-only array; it does not exist in POSIX sh. mcp.json invokes the script as `"command": "sh", "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/start.sh"]`. On systems where sh is dash (Debian, Ubuntu) or any non-bash POSIX shell, BASH_SOURCE[0] expands to empty string, SCRIPT_DIR is set to ".", and the exec resolves to ./server.py relative to the working directory rather than the correct absolute path. The MCP server fails to start and hamlet_init is unavailable.

Fix: Change shebang and invocation to use bash explicitly, or use $0 with POSIX-compatible dirname.

## Significant Gaps

### S1: server_url written by hamlet_init is never read by hooks

mcp/server.py writes server_url into <project>/.hamlet/config.json. The four hook scripts call find_server_url(), which reads from ~/.hamlet/config.json (global config) — not from the project config. find_config() traverses upward looking for project_id but never reads server_url from project configs. The server_url key written by hamlet_init is a dead field: never consumed. A user who configures a non-default server URL via hamlet_init will see no effect.

### S2: No onboarding guidance after plugin install

After installing the plugin, a user receives no instruction to run hamlet_init, no instruction to start the daemon, and no instruction to open the viewer. The hamlet_init MCP tool exists but nothing prompts the user to invoke it. Without hamlet_init, hooks use a hash-based fallback project ID. Principle P11 (low-friction setup — "see their first village within minutes") is unmet. No CLAUDE.md is injected, no post-install message, no guided next steps.

## Minor Gaps

### M1: plugin.json author.name is the project name, not an author
plugin.json has "author": {"name": "hamlet"}. Every other marketplace plugin uses a real author name. This placeholder was never replaced.

### M2: hamlet_init response provides no next-step guidance
When hamlet_init runs successfully, it returns the raw config JSON with no instruction on what to do next (start the daemon, open the viewer). Given P11, the tool response should tell the user the next steps.

### M3: Stale timing files accumulate on abnormal session exit
pre_tool_use.py writes a timestamp file to ~/.hamlet/timing/<session_id>_<tool_name>. post_tool_use.py deletes it when computing duration. If a session ends abnormally (crash, kill, restart), timing files are never cleaned up. No TTL, no cleanup on the Stop hook, no documented manual cleanup step.
