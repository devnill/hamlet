# Gap Analysis — Cycle 013

## Verdict: Pass

All 6 cycle 012 findings were addressed. The implementation is functionally correct, with two deferred minor usability gaps and one missing test class for the new validation logic.

## Addressed Findings

| Finding | WI | Status | Notes |
|---|---|---|---|
| S1: Water bias formula documentation inaccurate | WI-258 | Resolved | Comment at terrain.py:692 now reads "Max ±0.15 adjustment (bias_strength * biome_char * 0.5)", accurately describing the formula |
| S2: Ten TerrainConfig parameters missing from parameter panel | WI-259 | Resolved | All 10 parameters added to TERRAIN_PARAMS (region_scale, region_blending, river_count, pond_count, min_pond_size, max_pond_size, water_percentage_target, forest_water_adjacency_bonus, forest_region_bias_strength, forest_percentage_target) |
| S3: Settings docstring outdated | WI-260 | Resolved | Docstring now lists all parameters and defers to TerrainConfig for the full reference |
| S4: Bounds calculation duplicated | WI-261 | Resolved | map_viewer.py imports and delegates to `get_visible_bounds` from `viewport/coordinates.py` |
| G1: Legend not accessible in map viewer | WI-262 | Resolved | MapApp has `/` keybinding, `action_toggle_legend`, and yields `LegendOverlay` in compose |
| G2: Terrain parameter validation missing | WI-263 | Resolved | `TerrainConfig.__post_init__` validates region_scale, octaves, all thresholds, water/forest percentage targets |

## Gaps Found

### Critical

None.

### Significant

None.

### Minor

**WI-259 S2 (deferred): Auto fields cannot be reset to None from the parameter panel.**

Fields with `None` defaults (`river_count`, `pond_count`, `water_percentage_target`, `forest_percentage_target`) use `None` to mean "auto-calculate". Once a user adjusts them to a numeric value, there is no way to return them to `None`/auto via the panel — the `_adjust_param` method converts `None` to midpoint and never re-sets `None`. This was explicitly deferred by the incremental reviewer (WI-259 S2). Users who save a non-None value will lose auto-calculate behavior.

**WI-263: Threshold validation treats `water_threshold` the same as others.**

The validation loop at terrain.py:130–133 checks `mountain_threshold`, `forest_threshold`, and `meadow_threshold` for range `[0, 1]`. This is correct. `water_threshold` has its own check at terrain.py:128–129 against `[-1, 1]` — also correct. No gap here on logic, but the notes spec (263.md) originally proposed treating `water_threshold` uniformly with the others (checking `[0, 1]`), which would have been wrong. The implementation correctly uses `[-1, 1]` for `water_threshold`. This is a documentation inconsistency in the notes, not a code gap.

## Missing Tests

**Validation logic in `TerrainConfig.__post_init__` (WI-263) has no tests.**

No test class or test functions exist for the new `__post_init__` validation. Searching `tests/test_terrain.py` for `caplog`, `__post_init__`, `warning`, or validation-related patterns returns no matches. The following behaviors are untested:

- `region_scale < 10` logs a warning
- `region_scale > 500` logs a warning
- `octaves > 10` logs a warning
- `water_threshold` outside `[-1, 1]` logs a warning
- `mountain_threshold`, `forest_threshold`, `meadow_threshold` outside `[0, 1]` log warnings
- `water_percentage_target` outside `[0, 50]` logs a warning
- `forest_percentage_target` outside `[0, 50]` logs a warning
- In-range values do not log warnings
- Out-of-range values are still accepted (no exception raised)

**Legend toggle in `MapApp` (WI-262) has no tests.**

`tests/test_map_viewer.py` has no tests for `action_toggle_legend`, `LegendOverlay` visibility, or the `/` keybinding in `MapApp`. The existing test file covers `MapViewer` widget logic but not `MapApp` app-level behavior.

## Missing Infrastructure

None.
