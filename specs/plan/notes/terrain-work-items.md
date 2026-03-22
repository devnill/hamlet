# Work Items — Terrain (refine-14)

Work items WI-232 through WI-239 implement terrain generation for the hamlet idle game.

## Dependency Graph

```
WI-232 (TerrainType enum) ─────────────────────────────────────────┐
                                                                    │
WI-233 (TerrainGenerator) ──┬───────────────────────────────────────┼──> WI-235 (WorldStateManager integration)
                            │                                       │
WI-234 (TerrainGrid) ───────┘                                       │
                                                                    │
WI-236 (Terrain symbols) ──────────────────────────────────────────┼──> WI-237 (WorldView terrain layer)
                                                                    │
WI-235 (WorldStateManager integration) ───────────────────────────┼──> WI-237 (WorldView terrain layer)
                                                                    │
WI-235 (WorldStateManager integration) ───────────────────────────┴──> WI-238 (Persistence integration)

WI-239 (RemoteWorldState terrain) ──────────────────────────────────────> WI-238 (Persistence integration)
```

## Execution Strategy

**Phase 1 (Parallel)**: WI-232, WI-233, WI-234, WI-236 can run in parallel — they have no dependencies on each other.

**Phase 2 (Sequential)**: WI-235 depends on WI-232, WI-233, WI-234. WI-237 depends on WI-235, WI-236. WI-238 depends on WI-235.

**Phase 3 (Sequential)**: WI-239 depends on WI-238.

## Notes

- The `noise` library is a new dependency for Perlin noise generation. Alternative: use seeded `random` with deterministic hashing.
- No database migration needed — terrain seed stored in existing `world_metadata` table.
- Village placement uses spiral search from (0,0) to find first passable terrain.
- Structure placement validates terrain (no water/mountains).