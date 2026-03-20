# Decision Log — Cycle 008

## Context

Cycle 008 is the capstone review of refine-7 (v0.4.0): full Claude Code hook coverage (11 new scripts), adaptive viewport resize, plugin install hygiene, event schema extension, daemon event handling, and version bump. Eight work items (WI-179 through WI-186) were executed over one day (2026-03-20).

---

## Decision: os.chdir pattern is required before any find_server_url() or find_config() call

**Established in**: WI-179 rework (incremental review)
**Confirmed as gap by**: Code-quality capstone review (S1)
**Files affected**: All 11 new hook scripts (6 WI-179, 5 WI-180)

The WI-179 incremental review identified that `find_server_url()` was called before `os.chdir(cwd)`, causing traversal from Claude Code's launch directory rather than the project directory. The fix — read stdin first, then chdir, then call utilities — was applied to the WI-179 scripts during rework.

The WI-180 scripts were completed before this rework was finalized. The capstone review (code-quality S1) correctly identified that the five WI-180 scripts were missing `os.chdir` entirely. This was fixed before the capstone verdict.

**Durable rule**: All hook scripts must follow: `json.load(stdin)` → `os.chdir(cwd)` → `find_server_url()` → `find_config()`. `import os` is required. See architecture P-6 (config traversal) and P-9 (server URL resolution).

---

## Decision: HOOK_SCRIPTS dict in install.py must cover all registered hook types

**Identified by**: Code-quality capstone review (M4 — elevated to significant impact)
**Fixed in**: Cycle 008 review
**File**: `src/hamlet/cli/commands/install.py:20–25`

The `HOOK_SCRIPTS` dict was created when only 4 hook types existed. WI-185 added `is_plugin_active()` without updating the list. The capstone review found that non-plugin users running `hamlet install` would receive only 4 of 15 hooks. Fixed by adding all 11 new hook types to the dict, matching the entries in `hooks.json`.

**Durable rule**: Any addition of a new hook script must be accompanied by an update to `HOOK_SCRIPTS` in `install.py`. The dict and `hooks.json` must remain in sync.

---

## Decision: PreToolUse and PreCompact are blocking hooks — no async:true

**Established in**: WI-181
**Source**: Claude Code hook documentation

Blocking hooks (PreToolUse, PreCompact) must not have `"async": true` in `hooks.json`. These hooks can interrupt Claude Code's processing. Setting async on them produces a load error. All other hook types are fire-and-forget and should use `"async": true` to avoid blocking the Claude Code process.

---

## Decision: TeammateIdle daemon handler is log-only (no agent name lookup)

**Established in**: WI-183 rework
**Reason**: The `Agent` dataclass has no `name` field. `getattr(agent, "name", None)` always returns None. The spec described finding an agent by teammate_name, but there is no stored mapping from teammate name to Agent entity.

**Resolution**: TeammateIdle handler logs a summary string only. No state mutation. If agent-name resolution becomes necessary in a future cycle, an Agent.name field or a name→agent_id index would need to be added.

---

## Decision: stop_failure.py sends nested error object — accepted as P-8 asymmetry

**Identified by**: Code-quality capstone review (M1)
**Status**: Deferred — not fixed this cycle

`stop_failure.py` sends `"error": {"type": ..., "reason": ...}` as a nested object. P-8 specifies flat params. However, the validation schema explicitly permits `"error": {"type": ["object", "null"]}` and `InternalEvent` stores it as `dict[str, Any] | None`. The pipeline accepts it.

This is the only hook that sends a nested non-tool value. The decision to keep it nested was implicit (the schema was written to match the Claude Code hook payload structure). A future cycle could flatten to `error_type` + `error_reason` for strict P-8 compliance.

---

## Open Questions

### OQ-1: Test coverage for new hook types and event pipeline branches

**Source**: Code-quality S2, Gap-analysis G2
**Status**: Open

None of the 11 new `HookType` values are covered by tests. None of the 11 new `handle_event()` branches are exercised. The `on_resize` handler and `is_plugin_active()` function are also untested. This is the most significant gap remaining after cycle 008.

**Impact if unresolved**: Regressions in session and agent lifecycle tracking, structure work accumulation, viewport resize, and plugin detection will not be caught automatically.

### OQ-2: notification_type field silently discarded (pre-existing)

**Source**: Gap-analysis G4, Suggestion from code-quality
**Status**: Open (pre-existing, deferred since cycle 005)

`notification.py` sends `notification_type` in params; the schema declares it; but `InternalEvent` has no `notification_type` field and `event_processor.py` does not extract it. The value is silently dropped. If visual differentiation of notification types (progress vs. info vs. warning) is desired, this field must be added to `InternalEvent` and extracted.

### OQ-3: is_plugin_active substring match may produce false positives

**Source**: Gap-analysis G3, Suggestion from code-quality
**Status**: Open

The `"hamlet" in key.lower()` match heuristic could match other plugins. A stricter match (exact key or installPath check) would be more robust but is a minor edge case.

---

## Cross-References

- S1 (code-quality) = G1 (gap-analysis): Both identify the os.chdir omission in WI-180 hooks. S1 provides the root cause (P-6 traversal from wrong directory); G1 tracks it as a missing implementation requirement. Fixed before capstone verdict.
- M4 (code-quality) = G1 (gap-analysis): HOOK_SCRIPTS incomplete. Both identify non-plugin users getting degraded experience. Fixed before capstone verdict.
- S2 (code-quality) = OQ-1 (this log): Test coverage gap for all new functionality. No fix applied this cycle.
- M1 (code-quality) = M1 (spec-adherence): stop_failure.py nested error object. Both reviewers noted the borderline P-8 issue. Deferred.
- M2 (code-quality) = M2 (spec-adherence): Infallible try/except in manager.py. Both reviewers noted the pattern. Deferred.
