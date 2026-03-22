# Review: WI-245 Lake Detection and Expansion

## Verdict: Fail

Acceptance criterion 8 (integration into generation pipeline) is not implemented, and the worker self-check incorrectly marked it as N/A.

## Critical Findings

### C1: Lake processing not integrated into generation pipeline
- **File**: `src/hamlet/world_state/terrain.py:880-898`
- **Issue**: Acceptance criterion 8 requires "Lake processing is integrated into generation pipeline after CA smoothing." The `TerrainGrid.get_terrain_in_bounds()` method applies `smooth_terrain()` but never calls `detect_lakes()` or `expand_lake()`. The functions are implemented but not used anywhere in the codebase.
- **Impact**: The lake detection and expansion functionality exists but is never executed. Small water bodies will remain small after smoothing, contrary to the work item's intent.
- **Suggested fix**: Add lake processing to `TerrainGrid.get_terrain_in_bounds()`:
  ```python
  def get_terrain_in_bounds(self, bounds: "Bounds") -> dict["Position", TerrainType]:
      # Generate raw terrain
      raw_terrain: dict[Position, TerrainType] = {}
      for pos, terrain in self._generator.generate_chunk(bounds):
          raw_terrain[pos] = terrain

      # Apply smoothing
      smoothed = smooth_terrain(raw_terrain, passes=self._smoothing_passes)

      # Apply lake expansion for small water bodies
      lakes = detect_lakes(smoothed, min_size=5)  # or make min_size configurable
      for lake_positions, _ in lakes:
          if len(lake_positions) < 5:  # target_size
              expanded = expand_lake(smoothed, lake_positions, target_size=5)
              for pos in expanded:
                  smoothed[pos] = TerrainType.WATER

      # Cache and return results
      for pos, terrain in smoothed.items():
          self._cache[pos] = terrain
      return smoothed
  ```

## Significant Findings

### S1: expand_lake signature differs from acceptance criterion
- **File**: `src/hamlet/world_state/terrain.py:785-787`
- **Issue**: Acceptance criterion 4 specifies `expand_lake(lake_positions, target_size)`, but implementation is `expand_lake(grid, lake_positions, target_size)`. The `grid` parameter is necessary to check terrain types during expansion.
- **Impact**: The acceptance criterion was underspecified. The implementation is correct, but documentation/spec mismatch may cause confusion.
- **Suggested fix**: Update acceptance criterion 4 to read: "`expand_lake(grid, lake_positions, target_size)` function exists" to match the actual implementation.

### S2: expand_lake can absorb adjacent water bodies (undefined behavior)
- **File**: `src/hamlet/world_state/terrain.py:820-835`
- **Issue**: The expansion logic only checks for mountains (`if grid[neighbor] == TerrainType.MOUNTAIN: continue`) but does not check for water. If two small lakes are separated by a single land cell, expanding one lake could absorb the other lake's cells if they're reached via BFS.
- **Impact**: This could cause lakes to merge unexpectedly, or one small lake to "consume" another small lake during expansion. The behavior is undefined and untested.
- **Suggested fix**: Either document this as intentional behavior (lake merging) or add a check to prevent expansion into water cells:
  ```python
  # Don't expand into mountains or other water bodies
  if grid[neighbor] in (TerrainType.MOUNTAIN, TerrainType.WATER):
      continue
  ```
  Add a test case: `test_expand_lake_does_not_absorb_adjacent_water_bodies`.

## Minor Findings

### M1: Center calculation may produce position outside lake
- **File**: `src/hamlet/world_state/terrain.py:809-812`
- **Issue**: The center is calculated using integer division of coordinate averages, which may produce a position that's not actually in the lake or even in the grid. For example, a lake at {(0,0), (0,1), (0,2), (0,3)} would have center at (0,1), which works. But the code handles the case gracefully - if center isn't in the grid, its neighbors are still checked.
- **Suggested fix**: Add a test case `test_expand_lake_center_not_in_lake_positions` to verify this edge case works correctly. Consider adding a comment explaining this behavior.

### M2: No test for expand_lake with empty lake_positions
- **File**: `tests/test_terrain.py:1500-1685`
- **Issue**: The `TestLakeExpansion` class has 8 tests but none test the edge case of `lake_positions` being an empty set.
- **Suggested fix**: Add test:
  ```python
  def test_expand_lake_empty_lake_positions(self) -> None:
      """expand_lake handles empty lake_positions."""
      grid = {Position(0, 0): TerrainType.PLAIN}
      expanded = expand_lake(grid, set(), target_size=5)
      assert len(expanded) == 0  # or assert it returns empty set
  ```

## Unmet Acceptance Criteria

- [x] AC1: `detect_lakes(grid, min_size)` function exists — PASS: Lines 709-747
- [x] AC2: Flood-fill algorithm identifies connected water regions — PASS: Uses 4-connected flood-fill in `_flood_fill_water()`
- [x] AC3: Returns list of (position_set, size) for each lake — PASS: Returns `list[tuple[set[Position], int]]`
- [x] AC4: `expand_lake(lake_positions, target_size)` function exists — PASS: Function exists (signature differs slightly; `grid` parameter added)
- [x] AC5: Small water bodies (< min_size) are expanded to target_size — PASS: Function logic correct; integration required for actual use
- [x] AC6: Expansion uses nearest-neighbor growth from lake center — PASS: BFS from calculated center
- [x] AC7: Lake expansion preserves water/mountain adjacency — PASS: Skips mountains at line 828-829
- [ ] AC8: Lake processing is integrated into generation pipeline after CA smoothing — FAIL: Functions implemented but not called in `TerrainGrid.get_terrain_in_bounds()` or anywhere else
