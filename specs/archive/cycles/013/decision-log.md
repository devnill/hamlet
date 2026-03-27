# Decision Log — Cycle 013

Cycle 013 was a refinement cycle addressing 6 findings from cycle 012's terrain generation review. All 6 work items passed incremental review; one required rework.

---

## D1: `water_threshold` validated against `[-1, 1]`, not `[0, 1]`

**Work item:** WI-263
**Date:** 2026-03-22
**Decision:** `water_threshold` is validated against `[-1, 1]` in `TerrainConfig.__post_init__`, separate from `mountain_threshold`, `forest_threshold`, and `meadow_threshold` which are validated against `[0, 1]`.

**Context:** The original spec note (notes/263.md) grouped all four thresholds together and suggested validating them uniformly against `[0, 1]`. During incremental review, this was identified as incorrect: `water_threshold` is an elevation noise threshold and its default value is `-0.25`. Applying a `[0, 1]` range check would have triggered a spurious warning on every default `TerrainConfig` instantiation.

**Outcome:** The implementation splits threshold validation into two groups. `water_threshold` gets its own check against `[-1, 1]` at `terrain.py:128–129`. The other three thresholds remain in a loop at `terrain.py:130–133` against `[0, 1]`. This is more correct than the spec note and the incremental review confirmed the rework.

**Cross-reference:** This decision resolved the spurious-warning issue flagged as a significant finding (WI-263 S1 in the review manifest). Spec adherence review independently confirmed the implementation is a positive deviation from the spec note.

---

## D2: Settings docstring uses reference note (Option 2)

**Work item:** WI-260
**Date:** 2026-03-22
**Decision:** The `Settings` class docstring was updated with a note pointing to `TerrainConfig` in `src/hamlet/world_state/terrain.py` for the full parameter list, rather than enumerating all parameters inline.

**Context:** The cycle 012 gap identified the Settings docstring as outdated — it did not reflect the `terrain_config` field or the many TerrainConfig parameters added in cycle 012. Two options were considered: enumerate all parameters in the docstring (Option 1) or add a single reference note to TerrainConfig (Option 2).

**Outcome:** Option 2 was chosen. This avoids duplication between the docstring and the TerrainConfig dataclass definition, and reduces maintenance burden when parameters are added or changed. GP-11 (Low-Friction Setup) is satisfied by pointing users to the authoritative source.

---

## D3: No UI mechanism to reset nullable parameters to None (deferred)

**Work item:** WI-259
**Date:** 2026-03-22
**Decision:** No change made. The inability to reset `river_count`, `pond_count`, `water_percentage_target`, and `forest_percentage_target` to `None` (auto-calculate) via the parameter panel is a known usability gap and is explicitly deferred.

**Context:** These TerrainConfig fields use `int | None` where `None` means "auto-calculate". The parameter panel sets `0` as the minimum value. When a user decrements to `0`, the panel stores integer `0`, not `None`; there is no panel gesture that produces `None`. The `_adjust_param` method converts `None` to midpoint on first interaction, making auto behavior unreachable once a value has been set. The incremental reviewer flagged this as WI-259 S2 (significant finding) and explicitly deferred it.

**Outcome:** Deferred to a future cycle. The gap does not constitute a regression — the behavior is unchanged from before WI-259. A future work item should add an explicit "reset to auto" action or a distinct UI affordance for nullable fields.

**Cross-reference:** This gap is independently noted in spec adherence review (WI-259 minor finding) and gap analysis (WI-259 S2 deferred). The `_adjust_param` midpoint-on-None behavior is a direct consequence of this gap.

---

## Open Questions

### OQ-1: `meadow_threshold` may need `[-1, 1]` validation range

**Source:** Code quality review S1
**Raised:** 2026-03-22

The code quality reviewer identified that `meadow_threshold` is a moisture threshold with noise range `[-1, 1]`, but the current `__post_init__` validation loop at `terrain.py:130–133` checks it against `[0, 1]`. The parameter panel correctly reflects the `[-1, 1]` range (`min_val=-1.0`). A user who decreases `meadow_threshold` below `0.0` via the panel (which the UI explicitly permits) will trigger a spurious warning on every `TerrainConfig` construction. The warning text "outside normal range [0, 1]" would be factually incorrect for a moisture threshold.

The suggested fix is to move `meadow_threshold` into the `[-1, 1]` group alongside `water_threshold`. This was not addressed in cycle 013 and is a candidate for cycle 014.

**Cross-reference:** Parallels D1 — the same range-type confusion that caused the `water_threshold` rework during WI-263. The `water_threshold` fix did not catch `meadow_threshold`.

### OQ-2: `TerrainConfig.__post_init__` validation is untested

**Source:** Gap analysis (missing tests)
**Raised:** 2026-03-22

No tests exist for the validation logic added by WI-263. Untested behaviors: each range check fires a warning for out-of-range values; in-range values produce no warnings; out-of-range values are accepted without raising an exception; `None` optional fields skip validation. `tests/test_terrain.py` has no `caplog` usage or validation-related patterns. A test class using `pytest`'s `caplog` fixture should be added.

### OQ-3: `MapApp` legend toggle is untested

**Source:** Gap analysis (missing tests)
**Raised:** 2026-03-22

The `action_toggle_legend` method, `/` keybinding, and `LegendOverlay` visibility behavior added by WI-262 have no tests. `tests/test_map_viewer.py` covers `MapViewer` widget logic but not `MapApp` app-level behavior.

### OQ-4: `map_app.py` accesses `MapViewer._terrain_grid` directly

**Source:** Code quality review M1
**Raised:** 2026-03-22

`map_app.py:195` sets `map_viewer._terrain_grid` directly, bypassing encapsulation. `MapViewer` has no public setter. This pattern predates cycle 013 and was not introduced by any cycle 013 work item. A `MapViewer.set_terrain_grid(grid)` method would make the interface explicit and allow `MapViewer` internals to evolve independently. Low priority — no behavioral issue — but worth addressing before the `MapViewer` interface grows further.

### OQ-5: `action_toggle_help` in `MapApp` is a no-op stub

**Source:** Spec adherence review M2
**Raised:** 2026-03-22

`action_toggle_help` is bound to `?` in `MapApp` but its body is `pass`. Not introduced by cycle 013 — the `?` binding was added by WI-262 without implementing help overlay behavior. The help overlay is unimplemented across the codebase. This is a placeholder for a future feature.
