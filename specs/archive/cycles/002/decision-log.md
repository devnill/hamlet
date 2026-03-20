# Decision Log — Cycle 2 (Plugin Execution Fixes, 2026-03-19)

**Cycle**: 2026-03-19
**Work items**: WI-169 (plugin execution), WI-170 (server_url + onboarding)
**Review verdict**: Fail — 0 critical, 1 significant (SG1: uv/mcp silent failure)

---

## Decisions Made

### D72: Change start.sh shebang to #!/bin/sh
start.sh was changed from #!/usr/bin/env bash to #!/bin/sh. All script content is POSIX-compatible after the $0 fix. Consistent with mcp.json invoking via "command": "sh".

### D73: Three-tier server_url lookup in hooks
find_server_url() now checks: project .hamlet/config.json → ~/.hamlet/config.json → hardcoded default. This connects hamlet_init's project-level server_url write to the hook scripts that need it.

### D74: hamlet_init response includes onboarding next steps
Success response now tells users to run `hamlet daemon` then `hamlet` after initialization.

---

## Findings Requiring Action

### F7 (Significant): MCP server silently fails when uv absent and mcp not pre-installed (gap SG1)
start.sh python3 fallback has no check for mcp package availability. Silent failure — plugin appears installed but hamlet_init tool is missing. Fix: add diagnostic check before python3 fallback.

---

## Open Questions

### Q3: Should we require uv, or support pip install mcp as a documented alternative?
The uv path is clean but uv is not universally installed. The fallback exists for a reason. A diagnostic message on failure satisfies P11 better than removing the fallback.

---

## Carried Forward
Q1, Q2 from Cycle 1 decision log remain open.
