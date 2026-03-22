# Execution Strategy — refine-15: Terrain Legend and Configurable Generation

## Mode
Batched parallel — three phases with dependencies between phases.

## Parallelism
- Phase 1: Max 3 concurrent agents (WI-249, WI-250, WI-251 have no interdependencies)
- Phase 2: Max 1 agent (WI-252, WI-253 are sequential)
- Phase 3: Max 2 agents (WI-255, WI-256, WI-257 depend on WI-254)

## Worktree configuration
- Isolation: worktree recommended for Phase 1 (3 parallel agents modifying different files)
- WI-249: `src/hamlet/tui/legend.py`
- WI-250: `src/hamlet/world_state/terrain.py`
- WI-251: `src/hamlet/config/settings.py`, `src/hamlet/app_factory.py`

## Review cadence
- Incremental review after each work item
- Capstone review after each phase

## Work item groups

### Phase 1 (parallel — no dependencies)
| ID | Title | Complexity | Key files |
|----|-------|------------|-----------|
| WI-249 | Terrain Legend Enhancement | low | tui/legend.py |
| WI-250 | TerrainConfig Parameter System | medium | world_state/terrain.py |
| WI-251 | Config Persistence for Terrain Parameters | medium | config/settings.py, app_factory.py |

### Phase 2 (sequential — map viewer)
| ID | Title | Complexity | Key files |
|----|-------|------------|-----------|
| WI-252 | Map Viewer Mode with Parameter Adjustment | high | cli/__init__.py, tui/app.py, tui/map_viewer.py (new), tui/parameter_panel.py (new) |
| WI-253 | Zoom Functionality for Map Viewer | medium | tui/map_viewer.py, viewport/coordinates.py |

### Phase 3 (parallel after WI-254)
| ID | Title | Complexity | Key files |
|----|-------|------------|-----------|
| WI-254 | Biome Region Generation | high | world_state/terrain.py |
| WI-255 | Realistic Water Features | high | world_state/terrain.py |
| WI-256 | Forest Clustering Near Features | medium | world_state/terrain.py |
| WI-257 | Terrain Smoothing and Transition Rules | medium | world_state/terrain.py |

## Dependency graph

```
Phase 1:
  WI-249 ──────────────────────────────────┐
                                            │
  WI-250 ─────┬─────────────────────────────┼──> WI-252 ──> WI-253
              │                             │
              │                             │
              └─────────────────────────────┼──> WI-254 ──┬──> WI-255 ──> WI-256
                                            │             │
  WI-251 ───────────────────────────────────┘             └──> WI-257

Phase 2 (after Phase 1):
  WI-252 ──> WI-253

Phase 3 (after WI-254):
  WI-254 ──┬──> WI-255 ──> WI-256
           └──> WI-257
```

## Agent configuration
- Model: sonnet (all items)
- WI-252 and WI-254 are high complexity — consider opus for these items
- WI-255 (water features) and WI-257 (smoothing) can run in parallel after WI-254
- WI-256 (forest clustering) should wait for WI-255 (needs water features)

## Testing notes
- WI-249: Visual verification in TUI
- WI-250: Unit tests for parameter usage in terrain generation
- WI-251: Integration test for config load/save
- WI-252: Manual testing of map viewer mode
- WI-253: Manual testing of zoom levels
- WI-254-WI-257: Unit tests for terrain algorithms; visual verification for realistic appearance