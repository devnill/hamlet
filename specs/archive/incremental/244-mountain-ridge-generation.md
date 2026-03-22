# WI-244 Review: Mountain Ridge Generation

## Verdict: Fail

Acceptance criterion #6 is not satisfied: ridge generation methods exist but are not integrated into the main terrain generation pipeline.

## Critical Findings

### C1: Ridge generation not integrated into main pipeline
- **File**: `src/hamlet/world_state/terrain.py:880-898`
- **Issue**: The `TerrainGrid.get_terrain_in_bounds()` method generates terrain using `generate_chunk()`, applies smoothing, and returns results. It never calls `generate_ridge_chain()`, `generate_ridges_from_heightmap()`, or `generate_terrain_with_ridges()`. The ridge generation methods exist and are tested in isolation but are completely unused in production code.
- **Impact**: Generated terrain will not contain mountain ridges. The feature implementation is incomplete.
- **Suggested fix**: Integrate ridge generation into `get_terrain_in_bounds()`:
  ```python
  def get_terrain_in_bounds(self, bounds: "Bounds") -> dict["Position", TerrainType]:
      # Generate raw terrain with heightmap
      raw_terrain: dict[Position, TerrainType] = {}
      heightmap: dict[Position, float] = {}
      for pos, terrain in self._generator.generate_chunk(bounds):
          raw_terrain[pos] = terrain
          # Store elevation for ridge seeding

      # Generate ridges from high-elevation points
      ridges = self._generator.generate_ridges_from_heightmap(heightmap)

      # Override ridge positions with MOUNTAIN
      for ridge in ridges:
          for pos in ridge:
              if pos in raw_terrain:
                  raw_terrain[pos] = TerrainType.MOUNTAIN

      # Apply smoothing
      smoothed = smooth_terrain(raw_terrain, passes=self._smoothing_passes)
      ...
  ```

## Significant Findings

### S1: Missing heightmap tracking in generate_chunk
- **File**: `src/hamlet/world_state/terrain.py:263-274`
- **Issue**: `generate_chunk()` yields `(Position, TerrainType)` tuples but does not expose elevation values needed for ridge seeding. The `_generate_ridge_seeds()` method requires a heightmap with float elevation values to find peaks.
- **Impact**: Even if ridge generation is integrated, there is no way to obtain the heightmap needed for ridge seeding from the current API.
- **Suggested fix**: Either modify `generate_chunk()` to also yield elevation values, or create a separate method that generates the heightmap. The `_warped_fbm()` method produces the elevation values but they are not exposed.

### S2: No integration test for ridge generation
- **File**: `tests/test_terrain.py:1075-1299`
- **Issue**: The `TestRidgeGeneration` class tests the ridge generation methods in isolation but there is no test verifying that `TerrainGrid.get_terrain_in_bounds()` produces mountain terrain at ridge positions. All 15 tests pass for unit tests but there is no integration test.
- **Impact**: The missing integration was not caught by tests.
- **Suggested fix**: Add an integration test that verifies ridges appear as MOUNTAIN terrain in the output of `TerrainGrid.get_terrain_in_bounds()`:
  ```python
  def test_terrain_grid_includes_ridge_mountains(self) -> None:
      """TerrainGrid produces MOUNTAIN at ridge positions."""
      # Create config with known peaks
      # Verify that positions between peaks become MOUNTAIN
  ```

## Minor Findings

### M1: Potential integer overflow in hash seed
- **File**: `src/hamlet/world_state/terrain.py:334`
- **Issue**: `self._random.seed(self._seed + hash((p1, p2, i)))` - The hash of a tuple may produce large negative integers. Adding to seed could theoretically cause issues, though Python handles arbitrary integers.
- **Suggested fix**: Use `self._random.seed(self._seed + abs(hash((p1, p2, i))) % (2**31))` for consistent behavior across Python versions.

### M2: Displacement limit may not guarantee connectivity
- **File**: `src/hamlet/world_state/terrain.py:336-337`
- **Issue**: The code limits displacement to `min(roughness, 0.3) * length` but the test on line 1103 allows Chebyshev distance up to 2 between consecutive points, not 1. This suggests gaps may occur despite the `_fill_ridge_gaps()` method.
- **Suggested fix**: The test comment says "adjacent or diagonal neighbors" but the assertion allows `dx <= 2 and dy <= 2`. Either tighten the test assertion or update the comment.

## Unmet Acceptance Criteria

- [x] `generate_ridge_chain(start, end, roughness)` method exists — PASS: Method exists at line 280
- [x] Ridge uses midpoint displacement algorithm — PASS: Implementation uses midpoint displacement with perpendicular offset
- [x] Ridge cells are marked as MOUNTAIN terrain — PASS: `generate_terrain_with_ridges()` returns MOUNTAIN for ridge positions
- [x] Ridge chain connects to existing mountain cells from noise generation — PARTIAL: `_generate_ridge_seeds()` finds peaks above 80% of mountain_threshold, but integration is missing
- [x] Same seed produces same ridge placement (deterministic) — PASS: Tests verify determinism
- [ ] Ridge generation is integrated into main pipeline after fBm classification — FAIL: Methods exist but are never called from `TerrainGrid.get_terrain_in_bounds()`

## Test Summary

15 tests in TestRidgeGeneration class, all passing:
- `test_generate_ridge_chain_returns_start_and_end`
- `test_generate_ridge_chain_connects_points`
- `test_generate_ridge_chain_deterministic`
- `test_generate_ridge_chain_different_seeds`
- `test_generate_ridge_chain_roughness_affects_shape`
- `test_generate_ridge_chain_same_start_end`
- `test_generate_ridge_chain_short_distance`
- `test_generate_ridge_seeds_empty_heightmap`
- `test_generate_ridge_seeds_finds_peaks`
- `test_generate_ridge_seeds_deterministic`
- `test_generate_ridge_seeds_respects_num_ridges`
- `test_generate_ridges_from_heightmap`
- `test_generate_terrain_with_ridges_marks_mountain`
- `test_generate_terrain_with_ridges_preserves_other_terrain`
- `test_generate_terrain_with_ridges_none_ridges`

Missing: Integration test verifying ridge mountains appear in `TerrainGrid.get_terrain_in_bounds()` output.
