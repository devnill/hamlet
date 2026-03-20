## Verdict: Pass (after rework)

HTTP endpoint largely correct but has a resource leak, an uncaught exception path that aborts start() after MCP task is live, and no tests.

## Critical Findings

None.

## Significant Findings

### S1: `runner.setup()` outside OSError guard — exception aborts start() after MCP task is running
- **File**: `src/hamlet/mcp_server/server.py:88-91`
- **Issue**: `await runner.setup()` executes outside the `try/except OSError` block. A non-OSError exception propagates out of `start()` with `_run_task` already created and `_running=True`. Caller receives unhandled exception with live MCP task but no way to invoke `stop()`.
- **Impact**: Violates GP-7 and AC8. Can leave server in uncleanable half-started state.
- **Suggested fix**: Wrap entire HTTP setup block in `try/except Exception`.

### S2: Resource leak when `site.start()` raises OSError
- **File**: `src/hamlet/mcp_server/server.py:88-98`
- **Issue**: `self._http_runner = runner` is inside the `try` block (only reached on success). If `site.start()` raises `OSError`, `_http_runner` is never assigned, so `stop()` skips cleanup and the AppRunner's internal resources are leaked.
- **Impact**: File descriptors and asyncio tasks from `runner.setup()` never released after port-conflict failure.
- **Suggested fix**: Assign `self._http_runner = runner` immediately after `runner.setup()`, before the `try`.

### S3: No tests for HTTP endpoint behaviour
- **File**: `tests/test_mcp_server.py`
- **Issue**: Zero tests cover any HTTP path. Existing tests also don't mock aiohttp, so they will attempt to bind port 8080 during test runs.
- **Impact**: All HTTP acceptance criteria unverified by test suite.
- **Suggested fix**: Add tests using aiohttp test utilities or mocking TCPSite.

## Minor Findings

### M1: Double WARN log on schema-validation failure
- **File**: `src/hamlet/mcp_server/server.py:80`
- **Issue**: `validate_event()` already logs at WARNING internally. The HTTP handler logs a second WARNING for the same event.
- **Suggested fix**: Remove redundant log at server.py line 80.

### M2: 405 response missing `Allow` header (RFC 7231 §6.5.5)
- **File**: `src/hamlet/mcp_server/server.py:72`
- **Suggested fix**: Add `headers={"Allow": "POST"}` to the 405 response.

## Unmet Acceptance Criteria

- [ ] AC9 — stop() shuts down HTTP server — Partially met; S2 means cleanup skipped after failed port binding.
- [ ] AC10 — Port in use: logged, continues — Partially met; S2 leaves runner resources leaked.
