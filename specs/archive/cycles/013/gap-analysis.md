## Summary

The implementation is largely complete. One functional gap in `_install`'s idempotency guard and missing launchctl failure-path tests for `start`, `stop`, and `restart` leave edge cases unhandled and untested.

## Gaps

### G1: `_install` idempotency guard is too narrow
- **Severity**: Significant
- **Area**: `service.py` — `_install`
- **Gap**: The guard `if PLIST_PATH.exists() and _service_is_running()` only prevents re-install when both the plist exists AND the service is running. When the service has been stopped but not uninstalled (`PLIST_PATH.exists()` is True, `_service_is_running()` is False), the guard does not fire and `_install` proceeds to overwrite the plist and call `launchctl bootstrap` on an already-registered label, producing a confusing error.
- **Impact**: Users who run `hamlet service stop` followed by `hamlet service install` get a misleading "launchctl load failed" error instead of being directed to `hamlet service start`.

### G2: No launchctl failure-path tests for `start`, `stop`, and `restart`
- **Severity**: Minor
- **Area**: `tests/test_cli_service.py`
- **Gap**: `TestInstallCommand` includes a test for launchctl failure (bootstrap returns non-zero), but `TestStartCommand`, `TestStopCommand`, and `TestRestartCommand` have no test for the launchctl failure branch. The implementations at `service.py:141-143`, `157-160`, `175-178`, and `181-183` all handle launchctl errors with `return 1` — these branches are not tested.
- **Impact**: Regression risk if the error-handling branches in these commands are accidentally broken.

### G3: No user-facing documentation for `hamlet service`
- **Severity**: Minor
- **Area**: Documentation
- **Gap**: README.md and any quickstart documentation do not mention `hamlet service install`, `hamlet service start`, or the upgrade flow (`pip install --upgrade hamlet && hamlet service restart`). Users discovering the tool from the README have no guidance on background service installation.
- **Impact**: Reduces discoverability of the service management feature. Addressed post-convergence.
