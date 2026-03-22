# Refinement Interview — 2026-03-22

**Context**: User feedback on terrain visualization — current Perlin noise implementation produces scattered, disconnected cells. Need realistic geographic features: lakes, forest groves, mountain ranges.

## Q: What's your priority for realism vs. simplicity?

The research proposes three implementation phases:
1. **Phase 1 (fBm + domain warping)** — Quick win, produces coherent terrain with ~50 lines of code change
2. **Phase 2 (cellular automata smoothing)** — Additional polish, larger connected regions
3. **Phase 3 (specialized features)** — Mountain ridge chains, lakes, rivers — more complex

**A**: All three phases would be good, but they need to be modular so we can test and examine the outputs individually.

## Q: Any specific feature priorities?

The research identified:
- Larger bodies of water (lakes)
- Forest groves (clustering)
- Mountain ranges (connected ridges)

**A**: No specific priority, all of the above.

## Q: Performance budget?

Current terrain generation is ~50ms for a 200x200 world. Phase 1 adds ~150ms. Phase 2 adds another ~50ms. Is ~250ms startup time acceptable?

**A**: Time is not a huge factor, unless it feels broken.

## Q: Guiding principles still apply?

All current guiding principles were confirmed as still applicable.

## Architecture Changes

No changes to module boundaries. Changes are contained within:
- `src/hamlet/world_state/terrain.py` — significant modification
- `tests/test_terrain.py` — new tests for generation algorithms

## Scope Boundary

**Changing:**
- TerrainGenerator implementation (fBm, domain warping, CA smoothing)
- TerrainConfig parameters (new thresholds, octaves, etc.)
- Tests for new algorithms

**Not changing:**
- TerrainType enum (unchanged)
- TerrainGrid interface (unchanged)
- WorldStateManager integration
- TUI rendering
- Persistence schema
- Any other modules