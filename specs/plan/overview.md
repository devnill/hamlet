# Change Plan — refine-15: Terrain Legend and Configurable Generation

## What is changing and why

The current terrain generation produces visually busy, scattered terrain cells rather than coherent biome regions. Additionally, the TUI legend does not display terrain type information. This refinement addresses both issues:

1. **Legend enhancement** — Add terrain types to the legend overlay
2. **Terrain generation refinement** — Create realistic, configurable biome regions

### Triggering Context

User feedback after terrain generation implementation:
- "The terrain is much too busy, I'd like something a little more realistic where biomes smoothly shift into each other"
- "We should have a variety of different types — rivers, ponds, large lakes"
- "Mountain ranges: ridge lines are great, we can also have scattered peaks occasionally"
- "Forests should cluster around water/features, modeling terrain generation after nature"
- "We should have editable parameters which can be altered to see how terrain generation is affected in real time"

### Scope Boundary

**Changing:**
- `src/hamlet/tui/legend.py` — Add terrain type section
- `src/hamlet/world_state/terrain.py` — Biome region generation, water features, forest clustering, smoothing rules
- `src/hamlet/config/settings.py` — Terrain config persistence
- `src/hamlet/app_factory.py` — Config loading integration
- `src/hamlet/cli/__init__.py` — Map viewer mode flag
- `src/hamlet/tui/app.py` — Map viewer mode entry
- `src/hamlet/tui/map_viewer.py` — New file for map viewer
- `src/hamlet/tui/parameter_panel.py` — New file for parameter adjustment UI
- `src/hamlet/viewport/coordinates.py` — Zoom support

**Not changing:**
- TerrainType enum (WATER, MOUNTAIN, FOREST, MEADOW, PLAIN unchanged)
- TerrainGrid interface (same methods)
- Agent behavior or rendering
- Persistence schema
- Guiding principles or constraints
- Oceans/islands feature (deferred for future)

## Work Items

### Phase 1: Foundation (WI-249, WI-250, WI-251)

**WI-249**: Terrain Legend Enhancement — Add terrain types to legend overlay
**WI-250**: TerrainConfig Parameter System — Expose all generation parameters
**WI-251**: Config Persistence — Save/load terrain parameters from config

### Phase 2: Map Viewer (WI-252, WI-253)

**WI-252**: Map Viewer Mode — New mode with parameter adjustment UI
**WI-253**: Zoom Functionality — Discrete zoom levels for viewing larger areas

### Phase 3: Terrain Generation (WI-254, WI-255, WI-256, WI-257)

**WI-254**: Biome Region Generation — Macro-scale regions for coherent terrain
**WI-255**: Realistic Water Features — Rivers, ponds, lakes
**WI-256**: Forest Clustering — Forests near water/features
**WI-257**: Terrain Smoothing — CA rules for all terrain types

## Dependency Graph

```
Phase 1 (foundation):
  WI-249 ──────────────────────────────────┐
                                            │
  WI-250 ─────┬─────────────────────────────┼─> WI-252 ──> WI-253
              │                             │
              │                             │
              └─────────────────────────────┼─> WI-254 ──┬─> WI-255 ──> WI-256
                                            │            │
              WI-251 ───────────────────────┘            └─> WI-257
```

## Execution Strategy

**Mode**: Batched parallel
- Phase 1: WI-249, WI-250, WI-251 can run in parallel
- Phase 2: WI-252 depends on Phase 1; WI-253 depends on WI-252
- Phase 3: WI-254 depends on WI-250; WI-255, WI-256, WI-257 depend on WI-254

**Parallelism**: Max 3 agents in Phase 1, 1 agent in Phase 2, 2 agents in Phase 3

**Review cadence**: Incremental review after each work item

## Expected Impact

- **Visual**: Larger, coherent biome regions; realistic water features; forests clustered near water
- **UX**: Legend shows terrain types; map viewer allows parameter tuning; zoom shows larger areas
- **Configurability**: All terrain parameters adjustable in real-time and persistable
- **Performance**: Target <500ms generation for 200x200 world
- **Determinism**: Same seed + same parameters = same terrain