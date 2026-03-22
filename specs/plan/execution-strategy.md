# Execution Strategy — refine-14: World Terrain Generation

## Mode
Batched parallel — three phases. Foundation types can run in parallel; integration depends on foundation; rendering depends on integration.

## Parallelism
- Max concurrent agents: 4 (phase 1)
- Max concurrent agents: 2 (phase 2)
- Max concurrent agents: 1 (phase 3)

## Worktree configuration
- Isolation: worktree recommended for phase 1 (4 parallel agents modifying different files)

## Review cadence
- Incremental review after each work item completes
- Capstone review after WI-239 (RemoteWorldState terrain methods, last integration item)

## Work item groups

### Phase 1 (parallel — no dependencies)
| ID | Title | Complexity | Key files |
|----|-------|------------|-----------|
| WI-232 | TerrainType enum and TerrainConfig dataclass | low | world_state/terrain.py (NEW) |
| WI-233 | TerrainGenerator — deterministic terrain from seed | medium | world_state/terrain.py |
| WI-234 | TerrainGrid — in-memory terrain storage with caching | low | world_state/terrain.py |
| WI-236 | Terrain symbols and colors for TUI | low | tui/symbols.py |

### Phase 2 (after WI-232, WI-233, WI-234, WI-236 complete)
| ID | Title | Complexity | Key files |
|----|-------|------------|-----------|
| WI-235 | WorldStateManager terrain integration and village placement | high | world_state/manager.py, protocols.py |
| WI-237 | WorldView terrain layer rendering | medium | tui/world_view.py, tui/app.py |
| WI-238 | Persistence integration for terrain seed | low | world_state/manager.py |

### Phase 3 (after WI-238 completes)
| ID | Title | Complexity | Key files |
|----|-------|------------|-----------|
| WI-239 | RemoteWorldState terrain methods | medium | tui/remote_world_state.py, mcp_server/server.py |

## Dependency graph

```
WI-232 ──────────────────────────────────────────┐
                                                  │
WI-233 ─┬─────────────────────────────────────────┼──> WI-235 ──> WI-237
        │                                        │       │
WI-234 ─┘                                        │       └──> WI-238 ──> WI-239
                                                 │
WI-236 ──────────────────────────────────────────┴──> WI-237
```

## Agent configuration
- Model: sonnet (all items)
- No additional decomposer required — work items are already atomic