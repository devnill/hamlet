# Cycle 012 Code Quality Review — Terrain Generation Refinement

**Reviewer**: Claude
**Date**: 2026-03-22
**Work Items**: WI-249 through WI-257

## Verdict: Fail

Multiple significant findings and one unmet acceptance criterion related to incomplete parameter exposure in the map viewer.

---

## Critical Findings

None.

---

## Significant Findings

### S1: Inverted Water Bias Formula in Wet Regions (WI-254)

- **File**: `/Users/dan/code/hamlet/src/hamlet/world_state/terrain.py:663`
- **Issue**: The water bias calculation for wet regions uses `bias_strength * (-biome_char) * 0.5`. While this is an improvement over the original inverted formula, the comment still states "wet regions: more water and forest" but the formula implementation doesn't align with the stated intent. For `biome_char = -1` (wettest), the water bias is `0.3 * 1.0 * 0.5 = 0.15`, but for `biome_char = -0.33` (boundary), the water bias is `0.3 * 0.33 * 0.5 = 0.05`. This means wet regions get higher water bias, which is correct. However, the constant `0.3` in line 651 (`bias_strength = self._config.region_blending * 0.3`) combined with the `* 0.5` in line 663 produces a maximum bias of 0.15, not 0.3 as suggested by the comment "Max +/-0.3 adjustment".
- **Impact**: The water bias in wet regions works correctly but the documented maximum is inaccurate. Users configuring `region_blending=1.0` expect a maximum bias of +/-0.3 but actually get +/-0.15.
- **Suggested fix**: Either update the comment on line 651 to reflect the actual maximum bias, or adjust the multiplier in the formula to achieve the documented 0.3 maximum.

### S2: Missing Parameters in Map Viewer Parameter Panel

- **File**: `/Users/dan/code/hamlet/src/hamlet/tui/parameter_panel.py:21-37`
- **Issue**: The `TERRAIN_PARAMS` list does not include the following TerrainConfig parameters that were added in WI-254, WI-255, and WI-256:
  - `region_scale` (WI-254)
  - `region_blending` (WI-254)
  - `river_count` (WI-255)
  - `pond_count` (WI-255)
  - `min_pond_size` (WI-255)
  - `max_pond_size` (WI-255)
  - `water_percentage_target` (WI-255)
  - `forest_water_adjacency_bonus` (WI-256)
  - `forest_region_bias_strength` (WI-256)
  - `forest_percentage_target` (WI-256)
- **Impact**: Users cannot adjust these parameters through the map viewer interface, despite them being configurable in TerrainConfig and persisted in settings.
- **Suggested fix**: Add these parameters to `TERRAIN_PARAMS` with appropriate min/max/step values:
  ```python
  TERRAIN_PARAMS = [
      # ... existing params ...
      ("region_scale", "Region Scale", 50.0, 200.0, 10.0, "Biome region size (cells)"),
      ("region_blending", "Region Blend", 0.0, 1.0, 0.1, "Biome transition sharpness"),
      ("river_count", "Rivers", 0, 10, 1, "Number of rivers (0=auto)"),
      ("pond_count", "Ponds", 0, 20, 1, "Number of ponds (0=auto)"),
      # etc.
  ]
  ```

### S3: TerrainConfig Parameters Not in Default Settings

- **File**: `/Users/dan/code/hamlet/src/hamlet/config/settings.py:13-34`
- **Issue**: The default settings JSON in the docstring is outdated and does not include the new TerrainConfig parameters from WI-254, WI-255, and WI-256. While the `terrain: dict[str, Any]` field will accept any parameters, the documented default configuration does not reflect the current parameter set.
- **Impact**: Users who look at the documented default config will see an incomplete list of parameters. New installations will use TerrainConfig defaults (which are correct), but the documentation is out of sync.
- **Suggested fix**: Update the docstring example to include all TerrainConfig parameters, or add a note that additional parameters are available.

### S4: Inconsistent Bounds Calculation

- **File**: `/Users/dan/code/hamlet/src/hamlet/tui/map_viewer.py:66-87`
- **Issue**: `MapViewer.get_visible_bounds()` reimplements the logic from `viewport/coordinates.py:get_visible_bounds()` instead of using the shared utility function. This creates two places to maintain the same bounds calculation logic.
- **Impact**: If bounds calculation needs to change, developers must update both locations. The current implementations appear equivalent but duplication invites divergence.
- **Suggested fix**: Refactor `MapViewer.get_visible_bounds()` to import and call the utility function from coordinates.py:
  ```python
  from hamlet.viewport.coordinates import get_visible_bounds, BoundingBox
  # ...
  def get_visible_bounds(self) -> "BoundingBox":
      from hamlet.viewport.coordinates import Size
      viewport_size = Size(self._viewport_width, self._viewport_height)
      center = Position(self.center_x, self.center_y)
      return get_visible_bounds(center, viewport_size, self.zoom)
  ```

---

## Minor Findings

### M1: Outdated Water Frequency and Mountain Frequency in Settings

- **File**: `/Users/dan/code/hamlet/src/hamlet/config/settings.py:16-17`
- **Issue**: The settings docstring includes `water_frequency` and `mountain_frequency` parameters, but these are not used in the current TerrainConfig. The TerrainConfig uses threshold-based classification (`water_threshold`, `mountain_threshold`) instead.
- **Suggested fix**: Update the docstring example to reflect current parameters, or remove these legacy fields.

### M2: Callable Type Hint Already Fixed

- **File**: `/Users/dan/code/hamlet/src/hamlet/tui/parameter_panel.py:6`
- **Issue**: The WI-252 review noted that `callable` was used instead of `Callable`. This has been fixed - the file now imports `Callable` from `typing` on line 6.
- **Suggested fix**: None needed; this was addressed.

### M3: Parameter Panel Excludes `seed` from Adjustment

- **File**: `/Users/dan/code/hamlet/src/hamlet/tui/parameter_panel.py:21-37`
- **Issue**: The `seed` parameter is not in `TERRAIN_PARAMS`, which is intentional since it has dedicated UI (display in header, randomization via 'R' key). However, this means `seed` cannot be manually edited through the panel.
- **Suggested fix**: Document this design decision or add a comment explaining why seed is handled separately.

### M4: Dead Code in scroll Method Removed

- **File**: `/Users/dan/code/hamlet/src/hamlet/tui/map_viewer.py:89-92`
- **Issue**: The WI-253 review identified dead variables and misleading comments in `scroll`. The current implementation is clean - the method now simply updates `center_x` and `center_y` without any unused variables.
- **Suggested fix**: None needed; this was addressed.

### M5: generate_water_features Modifies Generator State

- **File**: `/Users/dan/code/hamlet/src/hamlet/world_state/terrain.py:2015-2017`
- **Issue**: The helper function `generate_water_features` creates a `TerrainGenerator`, then overwrites `generator._seed` and `generator._random`. This is an unusual pattern that modifies internal state after construction.
- **Impact**: Works correctly but violates encapsulation. If TerrainGenerator ever validates seed in `__init__`, this would break.
- **Suggested fix**: Pass the seed to the TerrainGenerator constructor:
  ```python
  generator = TerrainGenerator(config)
  if config.seed is None:
      generator._seed = seed
      generator._random = random.Random(seed)
  ```

---

## Unmet Acceptance Criteria

### WI-252 AC3: Parameter panel displays all config values

- **Criterion**: "Parameter panel displays all configurable terrain parameters with current values"
- **Status**: NOT MET
- **Reason**: Ten TerrainConfig parameters (`region_scale`, `region_blending`, `river_count`, `pond_count`, `min_pond_size`, `max_pond_size`, `water_percentage_target`, `forest_water_adjacency_bonus`, `forest_region_bias_strength`, `forest_percentage_target`) are missing from the parameter panel. Users cannot view or adjust these values in the map viewer.

---

## Cross-Cutting Observations

### Parameter Persistence Pattern

The pattern for persisting terrain configuration is consistent:
1. `Settings.terrain` stores a dict representation of TerrainConfig
2. `app_factory.py` reconstructs TerrainConfig from the dict
3. `parameter_panel.py` allows editing
4. `map_app.py` persists via `Settings.save()`

This pattern works well but requires that all new parameters be added to both TerrainConfig (done) and TERRAIN_PARAMS (incomplete).

### Code Quality Across Work Items

The code for WI-249 through WI-257 is generally well-structured with:
- Clear docstrings explaining algorithm intent
- Consistent use of type hints
- Appropriate error handling
- Deterministic generation from seeds

### Test Coverage

Test coverage appears adequate based on the incremental reviews. The tests cover:
- TerrainType enum properties
- TerrainConfig parameter validation
- TerrainGenerator determinism
- Smoothing rules
- Lake detection and expansion
- River and pond generation
- Region bias calculation
- Zoom functionality
- Map viewer integration

---

## Files Reviewed

- `/Users/dan/code/hamlet/src/hamlet/world_state/terrain.py` (2052 lines)
- `/Users/dan/code/hamlet/src/hamlet/config/settings.py` (124 lines)
- `/Users/dan/code/hamlet/src/hamlet/app_factory.py` (175 lines)
- `/Users/dan/code/hamlet/src/hamlet/tui/map_viewer.py` (179 lines)
- `/Users/dan/code/hamlet/src/hamlet/tui/parameter_panel.py` (202 lines)
- `/Users/dan/code/hamlet/src/hamlet/tui/map_app.py` (341 lines)
- `/Users/dan/code/hamlet/src/hamlet/tui/legend.py` (61 lines)
- `/Users/dan/code/hamlet/src/hamlet/cli/__init__.py` (219 lines)
- `/Users/dan/code/hamlet/src/hamlet/viewport/coordinates.py` (133 lines)
- `/Users/dan/code/hamlet/tests/test_terrain.py` (partial)

---

## Summary

Cycle 012 implements sophisticated terrain generation with biome regions, water features, and forest clustering. The core algorithms are correct, but the map viewer integration is incomplete: 10 new parameters cannot be adjusted through the UI. Additionally, the water bias formula documentation is inaccurate, and there's code duplication in bounds calculation. These issues prevent the cycle from passing review.
