## Verdict: Fail

One script fails to satisfy its acceptance criterion, and `sys.exit(0)` in a `finally` block suppresses exceptions silently across all five scripts in a way that will mask coding errors during development.

## Critical Findings

None.

## Significant Findings

### S1: `stop_failure.py` does not unpack the error dict — sends raw value, not `{type, reason}`

- **File**: `/Users/dan/code/hamlet/hooks/stop_failure.py:28`
- **Issue**: The acceptance criterion states the script must send an `error` field structured as a dict with `type` and `reason` sub-fields. The script does `hook_input.get("error", {})` and sends whatever the input provides verbatim. If the upstream Claude Code hook delivers `error` as something other than `{"type": ..., "reason": ...}` (or as a string), the server receives an ill-shaped payload. Nothing in the script enforces or validates the `type`/`reason` structure.
- **Impact**: The MCP server may receive a malformed `error` field. Any server-side code that does `params["error"]["type"]` will raise `KeyError` or `TypeError` on unexpected input shapes.
- **Suggested fix**: Extract and normalise explicitly:
  ```python
  raw_error = hook_input.get("error", {})
  if not isinstance(raw_error, dict):
      raw_error = {}
  "error": {
      "type": raw_error.get("type", ""),
      "reason": raw_error.get("reason", ""),
  }
  ```

## Minor Findings

### M1: `sys.exit(0)` in `finally` silently swallows all exceptions across all five scripts

- **File**: `/Users/dan/code/hamlet/hooks/post_tool_use_failure.py:44`, `/Users/dan/code/hamlet/hooks/user_prompt_submit.py:43`, `/Users/dan/code/hamlet/hooks/pre_compact.py:42`, `/Users/dan/code/hamlet/hooks/post_compact.py:42`, `/Users/dan/code/hamlet/hooks/stop_failure.py:43`
- **Issue**: The `finally` block runs unconditionally, meaning `sys.exit(0)` fires even when the `except` clause is not reached and no exception was logged. This is the correct behaviour for GP-7. However, `sys.exit()` raises `SystemExit`, so if `sys.exit(0)` is ever placed *inside* the `try` block it would be caught by `except Exception` — it is not here, so the structure is safe. The minor issue is that `sys.exit(0)` in `finally` means any `SystemExit` raised by Python internals (e.g., from `json.load` finding EOF on a closed stdin) also exits 0 rather than propagating the real exit code. During local testing this makes failures invisible at the shell level.
- **Suggested fix**: This is an accepted trade-off under GP-7, but consider using `os._exit(0)` or simply calling `sys.exit(0)` unconditionally at the end of `main()` after the try/except (not in a `finally`) so the intent is clearer. Alternatively, leave as-is and document that exit 0 is always enforced.

### M2: `hook_input` is read from stdin before `find_server_url()` returns in all five scripts

- **File**: `/Users/dan/code/hamlet/hooks/post_tool_use_failure.py:16-18` (and equivalents in all five scripts)
- **Issue**: `find_server_url()` is called first, then `json.load(sys.stdin)`. If `find_server_url()` raises (it catches its own exceptions internally, so this won't happen in practice), stdin would be unconsumed. The reference pattern `notification.py` uses the same ordering, so this is consistent. The real observation is that the ordering is `find_server_url → json.load(stdin) → find_config`, whereas the reference script uses the same order. No bug, but reading stdin *before* potentially slow disk I/O (`find_config` walks directories) would reduce the window in which Claude Code's write end of the pipe blocks. Low priority given the 1-second HTTP timeout dominates.
- **Suggested fix**: Reorder to `json.load(sys.stdin)` first, then `find_server_url`, then `find_config`. This matches the natural data-dependency order and unblocks stdin immediately.

### M3: `pre_compact.py` and `post_compact.py` read `hook_input` from stdin but never use it

- **File**: `/Users/dan/code/hamlet/hooks/pre_compact.py:17`, `/Users/dan/code/hamlet/hooks/post_compact.py:17`
- **Issue**: Both scripts call `hook_input = json.load(sys.stdin)` but then only use `hook_input.get("session_id", "")`. If the compact hook delivers no `session_id` field (or delivers an empty stdin), the scripts still function but the `json.load` call will raise on malformed JSON, which is caught by the outer `except`. This is fine. The minor issue is that the variable name `hook_input` implies the full input is used; it would be clearer to note that only `session_id` is extracted from it.
- **Suggested fix**: No code change required; this is a documentation/readability observation. A comment like `# Only session_id is used for base-fields-only events` would suffice.

## Unmet Acceptance Criteria

- [ ] AC5: hooks/stop_failure.py sends error dict with `type` and `reason` fields — The script sends `hook_input.get("error", {})` verbatim without unpacking or validating the `type`/`reason` sub-fields. The structure of the outgoing `error` value is entirely dependent on whatever the upstream hook delivers, with no enforcement of the required shape.
