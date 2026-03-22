# Architecture: Terrain Module

## Component Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WorldStateManager                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   WorldState  │  │ PositionGrid │  │  TerrainGrid │  │    Persistence  │  │
│  │  (container)  │  │  (entities)  │  │   (terrain)  │  │    Facade       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────────┘  │
│         │                  │                  │                 │           │
│         └──────────────────┴──────────────────┴─────────────────┘           │
│                              asyncio.Lock                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                              │
                    ▼                              ▼
        ┌─────────────────────┐          ┌─────────────────────┐
        │   ExpansionManager  │          │      WorldView       │
        │   (village spawn)   │          │   (TUI rendering)    │
        │                     │          │                       │
        │  - check_village_   │          │  - terrain layer      │
        │    expansion()      │          │  - structure layer    │
        │  - find_valid_      │          │  - agent layer       │
        │    position()       │          │                       │
        └─────────────────────┘          └─────────────────────┘
                    │
                    ▼
        ┌─────────────────────┐
        │   TerrainGenerator  │
        │                     │
        │  - generate_chunk() │
        │  - is_passable()    │
        │  - get_terrain()    │
        └─────────────────────┘
```

## Data Flow

1. **World Initialization**: On first startup, `WorldStateManager.load_from_persistence()` loads terrain seed from `world_metadata`. If no seed exists, generates one and persists it.

2. **Terrain Generation**: `TerrainGenerator` produces terrain chunks on-demand using the deterministic seed. Terrain is generated for regions where villages/agents exist.

3. **Village Placement**: When a new project creates a village, `WorldStateManager._find_village_position()` queries `TerrainGrid` to find a passable cell (not water/mountains) with suitable distance from existing villages.

4. **Structure Placement**: `WorldStateManager.create_structure()` validates terrain at position (cannot build on water/mountains).

5. **Rendering**: `WorldView.render()` queries `TerrainGrid` for terrain in visible bounds, renders terrain background, then structures and agents on top.

## Module Specifications

See `plan/modules/terrain.md` for the full terrain module specification.

## Execution Order

### Parallel Groups
- `TerrainGrid` and `TerrainGenerator` can be developed in parallel (independent modules)
- `terrain_types.py` and `terrain_config.py` can be developed in parallel (simple enums/dataclasses)

### Sequential Dependencies
1. `terrain_types.py` → `TerrainGrid` (TerrainType enum used by TerrainGrid)
2. `TerrainGrid` → `WorldStateManager` integration (TerrainGrid added as field)
3. `TerrainGenerator` → `WorldStateManager` integration (generator called during initialization)
4. `WorldStateManager` integration → `WorldView` rendering (terrain layer in TUI)
5. `TerrainGrid` → `ExpansionManager` (village placement queries terrain)
6. All above → Persistence migration (new terrain columns/tables)

### Critical Path
1. `terrain_types.py` (TerrainType enum)
2. `TerrainGenerator` (deterministic terrain generation)
3. `TerrainGrid` (in-memory terrain storage)
4. `WorldStateManager` integration (add terrain field, village placement)
5. `WorldView` integration (render terrain tiles)
6. Persistence migration (store seed in world_metadata)

## Design Tensions

### 1. Terrain Storage Strategy

| Option | Tradeoff |
|--------|----------|
| Generate on-demand, cache in memory | Low storage, but regeneration on restart |
| Persist all terrain chunks | Fast load, but database bloat |
| Hybrid: generate deterministically, persist modifications | Balanced, requires tracking modifications |

**Resolution**: Hybrid approach. Store seed in `world_metadata`, generate terrain deterministically. Terrain modifications (if any) would be tracked separately. For MVP, terrain is read-only — no modifications to track.

### 2. Grid Coordinate System

| Option | Tradeoff |
|--------|----------|
| Global coordinates (same as PositionGrid) | Simple, consistent with existing code |
| Chunk-based coordinates (Minecraft-style) | Efficient for large worlds, more complex |

**Resolution**: Global coordinates. The current world is bounded by viewport and village positions (typically -50 to +50). Global coordinates are simpler and sufficient for the expected scale.

### 3. Terrain vs Entity Layer Interaction

| Option | Tradeoff |
|--------|----------|
| TerrainGrid checks on every occupy() call | Enforces constraints at PositionGrid level |
| Terrain checked only at placement time | Simpler, but allows inconsistent state |

**Resolution**: Check at placement time. `WorldStateManager._find_spawn_position()` and `create_structure()` will validate terrain. PositionGrid remains unaware of terrain. This maintains separation of concerns and avoids coupling.

### 4. Village Placement Algorithm

| Option | Tradeoff |
|--------|----------|
| Random valid cell within radius | Simple, but may cluster villages |
| Weighted selection near resources | Strategic, but requires resource concept |
| Spiral search from origin | Predictable placement, may conflict with terrain |
| Flood fill from center | Finds nearest valid, but more complex |

**Resolution**: Spiral search from world origin (0,0), skipping occupied positions and impassable terrain. First valid position wins. This is consistent with existing `_find_spawn_position()` pattern and deterministic with the seed.

## 100% Coverage Check

1. **Scope Coverage**: 
   - TerrainType enum covers all terrain types (water, mountains, forests, meadows, plains)
   - TerrainGenerator handles generation with configurable parameters
   - TerrainGrid stores and retrieves terrain data
   - WorldStateManager integration handles village placement and structure validation
   - WorldView integration renders terrain as background layer
   - Persistence handles seed storage

2. **No Overlaps**:
   - TerrainGrid is separate from PositionGrid (terrain vs entities)
   - TerrainGenerator is stateless (generation algorithm only)
   - WorldStateManager owns terrain lifecycle

3. **Complete Scope**:
   - Generation: TerrainGenerator with seed
   - Storage: TerrainGrid in memory, seed in world_metadata
   - Placement: Village placement via terrain validation
   - Rendering: WorldView terrain layer
   - Constraints: Structure placement validates terrain

4. **Interface Contracts**:
   - WorldStateManager.get_terrain_at(x, y) → TerrainType
   - WorldStateManager.is_passable(x, y) → bool
   - TerrainGenerator.generate_chunk(origin, size) → list[tuple[Position, TerrainType]]
   - TerrainGrid.get_terrain(position) → TerrainType | None
   - TerrainGrid.is_passable(position) → bool
