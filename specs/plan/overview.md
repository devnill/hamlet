# Change Plan — refine-14: World Terrain Generation

## What is changing and why

User feedback after using hamlet revealed a desire for richer visual and gameplay elements. The first foundational change is world terrain generation: a deterministic, seed-based terrain map with water, mountains, forests, meadows, and plains.

### Why terrain first?

Terrain is foundational:
- Affects where villages can be placed (can't build on water/mountains)
- Enables future features: geography-specific structures, resource gathering, agent movement
- Provides visual richness: the world is no longer a blank grid
- Breaking change to data model: terrain seed must be persisted before other features depend on it

### Feature: Deterministic World Terrain

A global terrain map generated from a seed:
- **Terrain types**: WATER, MOUNTAIN, FOREST, MEADOW, PLAIN
- **Visual representation**: ASCII tiles (`~` for water, `^` for mountains, `♣` for forests, `"` for meadows, `.` for plains)
- **Gameplay effect**: Structures cannot be built on WATER or MOUNTAIN terrain
- **Deterministic**: Same seed produces same terrain — shareable world seeds
- **Village placement**: Automatic search for passable terrain near world origin

### Deferred to future cycles

- Agent movement system (agents moving while working)
- Geography-specific structures (mines in mountains, lumber mills in forests)
- Project menu and village jumping UI
- Roads as agent-built features
- Building speed increases

These features require terrain as a foundation and will be addressed in subsequent refinement cycles.

## Scope

**Changing:**
- `src/hamlet/world_state/terrain.py` — NEW: TerrainType, TerrainConfig, TerrainGenerator, TerrainGrid
- `src/hamlet/world_state/manager.py` — terrain field, terrain-aware village placement, structure validation
- `src/hamlet/world_state/__init__.py` — export terrain classes
- `src/hamlet/tui/world_view.py` — terrain layer rendering
- `src/hamlet/tui/symbols.py` — terrain symbols and colors
- `src/hamlet/tui/app.py` — pass terrain_grid to WorldView
- `src/hamlet/tui/remote_world_state.py` — terrain query methods
- `src/hamlet/protocols.py` — get_terrain_at, is_passable methods
- `src/hamlet/mcp_server/server.py` — terrain HTTP endpoint
- Tests for all new modules

**Not changing:** Hook scripts, inference engine, expansion manager, animation, persistence schema (uses existing world_metadata table), existing village/structure/agent logic beyond terrain validation.

## Work items

- WI-232: TerrainType enum and TerrainConfig dataclass
- WI-233: TerrainGenerator — deterministic terrain from seed
- WI-234: TerrainGrid — in-memory terrain storage with caching
- WI-235: WorldStateManager terrain integration and village placement
- WI-236: Terrain symbols and colors for TUI
- WI-237: WorldView terrain layer rendering
- WI-238: Persistence integration for terrain seed
- WI-239: RemoteWorldState terrain methods

## Dependencies

```
WI-232 ─────────────────────────────────────────┐
                                                │
WI-233 ─┬───────────────────────────────────────┼──> WI-235 ──> WI-237
        │                                       │
WI-234 ─┘                                       │
                                                │
WI-236 ─────────────────────────────────────────┴──> WI-237

WI-235 ────────────────────────────────────────────> WI-238 ──> WI-239
```

Phase 1 (parallel): WI-232, WI-233, WI-234, WI-236
Phase 2 (sequential): WI-235 → WI-237, WI-238
Phase 3 (sequential): WI-239