## Cycle 013 Decision Log

### D1: `_check_platform()` void guard retained

**Decision**: Keep `_check_platform()` as a `sys.exit(1)` void guard rather than converting to `return 1`.

**Rationale**: The function is called at the top of every public command with no return value check at call sites. Converting to `return 1` would require updating every call site to `if not _check_platform(): return 1`, making the code more verbose without functional benefit. The void guard pattern is clear and intentional; tests for the non-macOS path use `pytest.raises(SystemExit)` which documents expected behavior.

### D2: launchctl `bootstrap`/`bootout` over deprecated `load`/`unload`

**Decision**: Use `launchctl bootstrap gui/{uid} {plist}` and `launchctl bootout gui/{uid}/{label}` rather than the spec-note's `load`/`unload`.

**Rationale**: `launchctl load` and `launchctl unload` are deprecated and non-functional on macOS 13+. This correction was approved in cycle 012. The spec notes in 204.md were written before this was discovered and are superseded by the approved implementation.

### D3: "other" port-conflict message includes service remedy commands

**Decision**: The "other" conflict message in `daemon.py` includes `hamlet service status` and `hamlet service stop` remedy lines, beyond what WI-205 specified.

**Rationale**: This addition was approved as fix S1 during WI-205's incremental review in cycle 012. The additional guidance helps users who may have the service running and are unaware it is the source of the conflict.

### D4: `_launchctl` concatenates stderr+stdout

**Decision**: Return `(result.stderr + result.stdout).strip()` rather than `result.stderr or result.stdout`.

**Rationale**: Concatenation ensures no output is lost when both streams have content. The spec-note's `or` form would silently drop stdout when stderr is non-empty.
