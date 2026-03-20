# WI-145 Status: Add test coverage for new code

## Status: COMPLETE

## Summary

Created three new test files covering `RemoteWorldState`, the `init` CLI command, and the `daemon` CLI subcommand registration.

## Files Created

- `/Users/dan/code/hamlet/tests/test_remote_world_state.py` — 8 tests
- `/Users/dan/code/hamlet/tests/test_cli_init.py` — 6 tests
- `/Users/dan/code/hamlet/tests/test_cli_daemon.py` — 4 tests

## Test Results

All 18 tests pass:

```
18 passed in 0.05s
```

## Implementation Notes

### fetch_events returns a list, not a dict
The spec's mock used `{"events": [...]}` for `fetch_events`, but `RemoteStateProvider.fetch_events()` already unwraps the dict and returns a `list[dict]` directly. `RemoteWorldState.refresh()` iterates over the return value directly. The mocks were corrected to return lists.

### get_event_log is oldest-first by insertion order
`get_event_log(limit=N)` returns `self._event_log[:limit]`, which preserves the order that `fetch_events` returned. Tests verify this behavior.

### Stale data retention on exception
Both state fetch and events fetch exceptions are caught independently. Tests confirm that previously-cached data is retained when either fails.

### pytest-asyncio configuration
`asyncio_mode = "auto"` is set in `pyproject.toml`, so `@pytest.mark.asyncio` decorators are included for clarity but are not strictly required.

### create_parser is exported from hamlet.cli
The `daemon` subcommand is registered with `dest="command"` set to `"daemon"` and a `func` attribute pointing to `_daemon_command`. Both are verified in tests.
