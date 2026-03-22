## Verdict: Fail

One significant logic error in `_install` allows a re-install over a stale plist to silently overwrite the file and bootstrap a duplicate service.

## Critical Findings

None.

## Significant Findings

### S1: `_install` guard uses AND instead of OR — stale plist is silently overwritten
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/service.py:75`
- **Issue**: The early-return guard is `if PLIST_PATH.exists() and _service_is_running()`. When a plist exists but the service is *not* loaded (e.g. it was stopped with `hamlet service stop` but not uninstalled, or launchd was restarted after a crash), the condition is `False` and the function proceeds to overwrite the plist and call `bootstrap` again. Because launchd still has the label registered from the previous stop, the second `bootstrap` may produce an error or silently create a duplicate entry depending on the macOS version. The intent of the guard — prevent a double-install — is not satisfied for the stopped-but-installed state. The guard should be `if PLIST_PATH.exists()` (or `if PLIST_PATH.exists() or _service_is_running()`) and the message should direct the user to `hamlet service start` when the plist is present but not running.
- **Impact**: Running `hamlet service install` after `hamlet service stop` overwrites the plist (harmless) and then attempts `launchctl bootstrap` on an already-registered label. On macOS 13+ this returns a non-zero exit code with "service already loaded", causing `_install` to print "launchctl load failed" and return 1 — confusing the user. On older macOS it may silently succeed, creating a duplicate entry.
- **Suggested fix**:
  ```python
  if PLIST_PATH.exists():
      if _service_is_running():
          print("Service is already installed and running. Run `hamlet service uninstall` first.")
      else:
          print("Service is already installed but not running. Run `hamlet service start` to start it.")
      return 0
  ```

## Minor Findings

### M1: Unnecessary f-string literals on plain strings
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/service.py:105`
- **Issue**: Lines 105, 106, 107, 108 use `f"..."` string literals but lines 105 contains no interpolation. This is a style inconsistency (the codebase otherwise uses bare strings when there is nothing to interpolate) and will generate a `SyntaxWarning` in Python 3.12+ (non-empty f-string without placeholders).
- **Suggested fix**: Change `print(f"hamlet service installed and started.")` to `print("hamlet service installed and started.")`.

### M2: `_check_port_conflict` treats any HTTP 200 response as hamlet — no body validation
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/daemon.py:32`
- **Issue**: The hamlet identification check reads `resp.status == 200` but does not inspect the response body. Any service on the port that returns HTTP 200 on `/hamlet/health` (coincidental path match, reverse proxy, etc.) is classified as "hamlet", suppressing the correct "another process" message and giving the user misleading guidance about `hamlet service stop`.
- **Suggested fix**: Also check that the response body contains `{"status": "ok"}`, e.g.:
  ```python
  import json
  data = json.loads(resp.read())
  if resp.status == 200 and data.get("status") == "ok":
      return "hamlet"
  ```

### M3: No test covers `_install` on a plist-exists-but-not-running scenario
- **File**: `tests/test_cli_service.py`
- **Issue**: `TestInstallCommand` has no test for the case where `PLIST_PATH.exists()` is `True` but `_service_is_running()` is `False`. This is exactly the scenario exposed by S1 — the guard falls through and a misleading launchctl error is shown to the user. Adding a regression test would both document the intended behavior and catch the existing bug.
- **Suggested fix**: Add a test that patches `PLIST_PATH` to exist and `_service_is_running` to return `False`, then asserts `_install` returns 0 with a message directing the user to `hamlet service start`.

### M4: `service_command` returns 1 for missing subcommand instead of printing help
- **File**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/service.py:212`
- **Issue**: When `hamlet service` is run without a subcommand, `service_subcommand` is `None`, causing `service_command` to print a bare usage string and return 1. The argparse subparsers added in `__init__.py` are not configured with `required=True`, so argparse itself does not print the subparser help. The user gets a terse, non-standard error rather than the full subparser help text.
- **Suggested fix**: Either set `required=True` on `service_subparsers` in `__init__.py`, or call `service_parser.print_help()` inside `service_command` before returning 1.
