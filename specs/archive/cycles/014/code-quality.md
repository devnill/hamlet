## Verdict: Pass (after rework)

Three significant findings fixed as immediate rework: `_shutdown_requested` reset added, dispatch guard restored with `.get()`, and all error messages updated to reference the correct launchctl subcommand names. 37 tests pass.

---
*Original findings (all resolved as rework before convergence check):*
---

## Critical Findings

None.

## Significant Findings

### S1: Module-level `_shutdown_requested` flag is never reset between runs

- **File**: `src/hamlet/cli/commands/daemon.py:17` and `:95`
- **Issue**: `_shutdown_requested` is a module-level boolean, set to `True` by the signal handler (`_signal_handler`, line 46) and read in the `while not _shutdown_requested` loop (line 95). It is never reset to `False` at the start of `_run_daemon`. If `daemon_command` is invoked more than once in the same Python process — as can happen in tests, programmatic use, or if a future supervisor restarts the daemon inline — the second call enters `_run_daemon`, and the `while not _shutdown_requested` loop exits immediately because the flag is still `True` from the previous run. The daemon appears to start and stop successfully (exit code 0) but does no work.
- **Impact**: In any test or embedding scenario that calls `daemon_command` twice, the second invocation silently exits without running. This also makes the function non-idempotent in a way that is invisible to the caller.
- **Suggested fix**: Reset the flag at the top of `_run_daemon` before entering the wait loop:
  ```python
  global _shutdown_requested
  _shutdown_requested = False
  ```
  Add this as the first line of `_run_daemon` (after the `global` declaration on line 61).

### S2: Bare dict lookup in `service_command` raises `KeyError` on unexpected subcommand

- **File**: `src/hamlet/cli/commands/service.py:215`
- **Issue**: `dispatch[subcommand](args)` performs a bare dict access. If `subcommand` is `None` (the default from `getattr(args, "service_subcommand", None)`) or any unrecognised string, this raises an unhandled `KeyError`. The argparse layer prevents this in normal CLI use because `service_subparsers.required = True` is set, but `service_command` is a public function and can be called directly — including from tests, from the `_service_command` shim, or via future programmatic use. The test suite calls it directly in every test via `_run_service`, which means any test that passes an invalid subcommand crashes with a `KeyError` instead of a clean failure.
- **Impact**: Any caller that passes a `Namespace` with `service_subcommand` absent or unrecognised receives an unhandled exception instead of a meaningful error message and a non-zero exit code.
- **Suggested fix**: Replace the bare lookup with a `.get()` and explicit error handling:
  ```python
  handler = dispatch.get(subcommand)
  if handler is None:
      print(f"Error: unknown service subcommand: {subcommand!r}", file=sys.stderr)
      return 1
  return handler(args)
  ```

### S3: Error messages reference deprecated launchctl subcommand names

- **File**: `src/hamlet/cli/commands/service.py:105`, `:145`, `:162`, `:185`
- **Issue**: After the migration to `bootstrap`/`bootout` (previous cycles), four error message strings still say "launchctl load failed" (lines 105, 145, 185) and "launchctl unload failed" (line 162). These are the deprecated command names that were replaced precisely because they were removed in newer macOS releases.
- **Impact**: When `bootstrap` or `bootout` fails, the error message tells the user the wrong command failed. A user who reads the message and tries to diagnose the issue — or searches for it — will be sent in the wrong direction. The message is actively misleading on macOS 13+.
- **Suggested fix**: Update the strings to match the actual commands:
  - Lines 105, 145, 185: `"Error: launchctl bootstrap failed: {output}"`
  - Line 162: `"Error: launchctl bootout failed: {output}"`

## Minor Findings

### M1: `_check_port_conflict` hardcodes `"localhost"` which may resolve to IPv6

- **File**: `src/hamlet/cli/commands/daemon.py:28`
- **Issue**: The TCP probe connects to `"localhost"` which on many macOS systems resolves to `::1` (IPv6 loopback). If the daemon binds to `127.0.0.1` (IPv4), the probe will fail to connect — reporting the port as free — even though the daemon is running. The health-check URL on line 33 also uses `localhost`, compounding the issue.
- **Suggested fix**: Use `"127.0.0.1"` explicitly for the socket probe, or probe both `"127.0.0.1"` and `"::1"` and treat the port as in-use if either succeeds.

### M2: `_install` idempotency guard returns exit code 0 when plist exists but service is not running

- **File**: `src/hamlet/cli/commands/service.py:79`
- **Issue**: When the plist exists but the service is not running, `_install` prints a message and returns `0`. Exit code 0 conventionally means success. A script that runs `hamlet service install && hamlet service start` would see the `0` from install, proceed to `start`, and start the service — which may be the intended behaviour. However, there is no way for a script to distinguish "newly installed" from "already installed but not running" using exit codes alone. This is a usability and scripting concern.
- **Suggested fix**: Return a non-zero exit code (e.g., `2`) for the "already installed but not running" case to allow callers to distinguish it from a clean install, or document that `0` is intentional for idempotent install semantics.

## Unmet Acceptance Criteria

No work item spec was provided for this review cycle. No acceptance criteria to evaluate.
