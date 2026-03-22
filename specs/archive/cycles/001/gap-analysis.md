# Gap Analysis — Cycle 001

**Review Date**: 2026-03-21
**Reviewer**: Claude Opus 4.6
**Scope**: Full project — missing requirements, integration gaps, implicit expectations

---

## Verdict: No Critical Gaps

The implementation addresses all requirements from the interview and module specifications. Terrain generation (WI-232 through WI-239) has been fully integrated with all acceptance criteria satisfied.

---

## Integration Gaps

### G1: State endpoint does not include terrain data

- **Location**: `src/hamlet/mcp_server/server.py:88-98`
- **Expected**: The `/hamlet/state` endpoint returns world state including terrain_grid data
- **Actual**: The state endpoint returns agents, structures, and villages but does not include terrain information. RemoteWorldState must make separate requests to `/terrain/{x}/{y}` for terrain data.
- **Impact**: Minor — the separate terrain endpoint exists and works correctly. This is a performance optimization concern, not a correctness issue.
- **Suggestion**: Consider adding terrain_grid serialization to the state endpoint response for efficiency, allowing viewers to fetch world state and terrain in a single request.

### G2: Terrain not serialized in checkpoint persistence

- **Location**: `src/hamlet/world_state/manager.py`
- **Expected**: The checkpoint mechanism should persist terrain_grid or terrain_seed
- **Actual**: The checkpoint system persists agents, structures, and villages, but terrain is regenerated from terrain_seed in world_metadata on each load.
- **Impact**: None — this is by design. terrain_seed is persisted, and terrain is deterministically regenerated.
- **Note**: Not a gap — correct implementation of the persistence strategy.

---

## Implicit Requirements — All Addressed

### IR1: Terrain determinism
- **Requirement**: Same seed should produce identical terrain across restarts
- **Status**: ✅ Addressed — TerrainGenerator uses seeded random and terrain_seed is persisted in world_metadata table

### IR2: Village placement must avoid impassable terrain
- **Requirement**: Villages should not be placed on water or mountains
- **Status**: ✅ Addressed — `_find_village_position` implements spiral search for passable terrain

### IR3: Structure creation must validate terrain
- **Requirement**: Players should not be able to build structures on water/mountains
- **Status**: ✅ Addressed — `create_structure` raises ValueError on impassable terrain

### IR4: RemoteWorldState must support terrain queries
- **Requirement**: Viewer mode needs terrain access
- **Status**: ✅ Addressed — `RemoteWorldState.get_terrain_at()` and `is_passable()` implemented, plus HTTP endpoint

### IR5: TUI must render terrain as background layer
- **Requirement**: World view should show terrain beneath agents and structures
- **Status**: ✅ Addressed — WorldView.render() renders terrain layer with correct priority (agent > structure > terrain)

---

## Missing Features From Interview

### M1: Multi-cell structure rendering on terrain
- **Interview Reference**: "Structures should have visual progression (foundation → wood → stone) and roads should connect villages"
- **Status**: ✅ Implemented — multi-cell structures and rendering priority work correctly
- **Note**: Roads between villages mentioned but implementation is deferred (not a gap for this cycle)

### M2: Terrain-based gameplay effects
- **Interview Reference**: No explicit terrain effects on gameplay were requested
- **Status**: N/A — Terrain is visual/atmospheric for now
- **Note**: Future enhancement could include movement costs through different terrain types

---

## Test Coverage Gaps

### T1: No integration test for terrain persistence across daemon restart
- **Location**: `tests/test_world_state_manager.py`
- **Issue**: Tests verify terrain_seed persistence, but there's no integration test that starts a daemon, places structures, restarts, and verifies terrain is identical
- **Impact**: Low — unit tests cover determinism, but end-to-end verification would increase confidence
- **Suggestion**: Add an e2e test in `test_e2e_persistence_roundtrip.py` that verifies terrain regeneration produces identical maps

### T2: Noise library path untested
- **Location**: `tests/test_terrain.py`
- **Issue**: The `_generate_with_noise` method is never executed in tests because the noise library is not installed in the test environment
- **Impact**: Medium — Production behavior with noise library installed is untested
- **Suggestion**: Add a test that mocks `HAS_NOISE=True` and verifies the noise path produces valid terrain types

---

## Documentation Gaps

### D1: No docstring for terrain module in main architecture
- **Location**: `specs/plan/architecture.md`
- **Issue**: Terrain module exists in `specs/plan/modules/terrain.md` but is not shown in the main architecture component map
- **Impact**: Low — documentation only
- **Suggestion**: Add a small "Terrain" box in the World State module showing TerrainGrid integration

---

## Summary

The terrain generation implementation is complete and well-integrated. All acceptance criteria from WI-232 through WI-239 are satisfied. The identified gaps are:

1. **G1**: Minor performance optimization — terrain not included in state endpoint
2. **T1, T2**: Test coverage opportunities — integration test for restart, noise library path
3. **D1**: Documentation — terrain not shown in architecture diagram

No critical or significant gaps that would block convergence.
