# Decision Log — Cycle 012

## Decisions Made

### D-1: Use launchctl bootstrap/bootout (modern API) over deprecated load/unload
- **Context**: Initial implementation used deprecated `launchctl load`/`unload` which fail silently or produce I/O errors on macOS 13+.
- **Decision**: Use `launchctl bootstrap gui/{uid} {plist}` and `launchctl bootout gui/{uid}/{label}` throughout.
- **Rationale**: The modern API is the only form that reliably works on currently supported macOS versions.

### D-2: bootout uses single service-target argument form
- **Context**: Two-argument form `bootout gui/uid label` passes the label as a path, returning exit code 5.
- **Decision**: Use single service-target form `bootout gui/uid/label`.
- **Rationale**: Confirmed on-system behavior; the single-target form is the correct documented usage.

## Open Questions

### Q-1: Should `hamlet service install` uninstall-then-reinstall, or refuse if already running?
- **Context**: S1/G3 — re-running `hamlet service install` when the service is loaded fails with an opaque launchctl error. Two UX options exist.
- **Options**: (a) Detect loaded state, print "already running, use hamlet service restart", exit 0. (b) Implement reinstall semantics: unload, overwrite plist, reload.
- **Status**: Open — to be resolved in cycle 2 rework.

## Findings to Address in Next Cycle

From code-quality.md:
- S1: `_install` not idempotent — add guard for already-loaded service
- S2: XML injection in plist — wrap path values with `xml.sax.saxutils.escape()` or switch to `plistlib.dumps()`
- M1: Settings mock target — change to `hamlet.cli.commands.daemon.Settings`
- M2: sys.exit() vs return — replace `sys.exit()` in service.py with `return` and let caller handle exit
- M3: Add test for re-install scenario
- M4: Conflict messages to stderr — add `file=sys.stderr` to print() in daemon.py

From gap-analysis.md:
- G1: Document `hamlet service` in README.md
- G2: Document `hamlet service` in QUICKSTART.md
