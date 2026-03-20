# WI-140 Status — Fix exit code propagation in main()

## Status: Complete

## Change Applied

Updated `main()` in `/Users/dan/code/hamlet/src/hamlet/__main__.py` to capture the return value from `asyncio.run(_run_viewer())` and pass it to `sys.exit()`.

### Before
```python
if not args:
    asyncio.run(_run_viewer())
    return
```

### After
```python
if not args:
    exit_code = asyncio.run(_run_viewer())
    sys.exit(exit_code if exit_code is not None else 0)
    return
```

## Acceptance Criteria

- `exit_code = asyncio.run(_run_viewer())` — return value captured: YES
- `sys.exit(exit_code)` called with the captured value: YES
- Process exits non-zero when daemon is unreachable: YES (`_run_viewer()` returns 1 on health-check failure, which is now propagated)
