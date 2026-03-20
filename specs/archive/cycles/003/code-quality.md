# Code Quality Review — Cycle 3 (WI-171: mcp diagnostic in start.sh)

Scope: WI-171 only — `mcp/start.sh` python3 fallback diagnostic check.

---

## Verdict: Pass

The shell logic is correct and POSIX-compatible. Two minor findings noted; no critical or significant defects.

## Critical Findings

None.

## Significant Findings

None.

## Minor Findings

### M1: `python3` absence produces a misleading error message
- **File**: `/Users/dan/code/hamlet/mcp/start.sh:7`
- **Issue**: When `python3` is not on PATH, `python3 -c "import mcp"` exits non-zero, causing the `if !` branch to fire and emit "hamlet: mcp package not found" — which is factually wrong. The actual problem is that `python3` itself is missing.
- **Suggested fix**: Add a `command -v python3` guard before line 7.

### M2: `pip install mcp` advice may install into the wrong Python environment
- **File**: `/Users/dan/code/hamlet/mcp/start.sh:8`
- **Issue**: On many systems `pip` installs into a different environment than `python3`. A user who follows this advice may still get `ModuleNotFoundError`.
- **Suggested fix**: Change to `python3 -m pip install mcp` to guarantee installation into the same interpreter that will run `server.py`.

## Unmet Acceptance Criteria

None.
