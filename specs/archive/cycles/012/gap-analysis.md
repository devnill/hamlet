## Summary

The core service management implementation is functionally complete. All six `hamlet service` subcommands are present, port conflict detection works correctly, plist template is correct, and CLI is properly registered. Two documentation gaps exist (README.md and QUICKSTART.md do not mention `hamlet service`) and two robustness/test gaps exist (install is not idempotent; missing test for re-install scenario). The XML injection finding from code-quality overlaps with the idempotency gap.

## Gaps Found

### G1: `hamlet service` is undocumented in README.md

- **What's missing**: The README.md Usage section lists five commands but does not mention `hamlet service` or any of its six subcommands. The upgrade flow (`pip install --upgrade hamlet && hamlet service restart`) is not described anywhere.
- **Where it should be**: `/Users/dan/code/hamlet/README.md` — in the Usage section.
- **Impact**: Users who want to run the daemon persistently in the background have no documentation pointing them to `hamlet service`. The upgrade flow — one of the stated requirements for this refinement — is invisible.
- **Suggested fix**: Add `hamlet service install/start/stop/restart/status/uninstall` to the Usage list with a short "macOS background service" note and the upgrade flow command.

### G2: `hamlet service` is undocumented in QUICKSTART.md

- **What's missing**: QUICKSTART.md step 3 presents only `hamlet daemon` (foreground) as the way to run the daemon. No mention of `hamlet service install` as an alternative.
- **Where it should be**: `/Users/dan/code/hamlet/QUICKSTART.md` — after step 3.
- **Impact**: A user following QUICKSTART.md to set up a persistent background service has no path to discover `hamlet service`.
- **Suggested fix**: Add a note after step 3 explaining that `hamlet service install` sets up the daemon as a persistent macOS background service that starts at login, with `hamlet service restart` as the upgrade command.

### G3: `hamlet service install` is not idempotent — re-install fails with opaque launchctl error

- **What's missing**: `_install` does not check whether the service is already loaded before calling `launchctl bootstrap`. Re-running install produces a confusing non-zero exit with a raw launchctl error.
- **Where it should be**: `/Users/dan/code/hamlet/src/hamlet/cli/commands/service.py` — at the top of `_install`.
- **Impact**: Running `hamlet service install` after an upgrade produces a confusing error.
- **Suggested fix**: Check `_service_is_running()` at the top of `_install`. If loaded, print "Service is already installed and running. Run `hamlet service uninstall` first." and exit 0 (or provide reinstall semantics).

### G4: Test for `hamlet service install` when service is already installed is missing

- **What's missing**: `TestInstallCommand` has no test for the already-installed scenario.
- **Where it should be**: `/Users/dan/code/hamlet/tests/test_cli_service.py`
- **Suggested fix**: Add a test mocking `_service_is_running` returning `True` and asserting graceful exit with informational message.

## No Gaps Found In

- All six subcommands present and fully implemented.
- CLI registration in `cli/__init__.py` with all six sub-subcommands.
- macOS platform guard on every subcommand.
- Plist template with `KeepAlive=true`, `RunAtLoad=true`, correct log paths.
- Executable discovery with venv fallback and clear error.
- Port conflict detection distinguishing hamlet vs. other process.
- Conflict error messages suggesting service remedies.
- Daemon exits non-zero on both conflict types without starting.
- Non-macOS platform tests cover all 6 subcommands.
- `uninstall` graceful when not installed; `start` when already running; `stop` when not running.
