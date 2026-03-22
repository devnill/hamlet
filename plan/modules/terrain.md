# Module: Terrain

## Scope

The terrain module provides the global terrain map for the hamlet idle game. It is responsible for:
- Defining terrain types (water, mountains, forests, meadows, plains)
- Generating terrain deterministically from a seed
- Storing terrain in memory for fast lookups
- Providing terrain information for village placement, structure building, and rendering

The terrain module is NOT responsible for:
- Entity positions (handled by PositionGrid)
- Village/structure/agent data (handled by WorldState)
- Rendering logic beyond providing terrain data (handled by WorldView)
- Persistence beyond storing the seed (handled by PersistenceFacade)

## Provides

- `TerrainType` (enum) — All valid terrain types with passability and display properties
- `TerrainConfig` (dataclass) — Configuration for terrain generation parameters
- `TerrainGenerator` (class) — Deterministic terrain generation from seed
- `TerrainGrid` (class) — In-memory terrain storage and lookup

### TerrainType

```python
class TerrainType(Enum):
    """Terrain types with inherent properties."""
    WATER = "water"
    MOUNTAIN = "mountain"
    FOREST = "forest"
    MEADOW = "meadow"
    PLAIN = "plain"

    @property
    def passable(self) -> bool:
        """True if agents/structures can occupy this terrain."""
        return self in (TerrainType.FOREST, TerrainType.MEADOW, TerrainType.PLAIN)
    
    @property
    def symbol(self) -> str:
        """ASCII symbol for TUI rendering."""
        ...
    
    @property
    def color(self) -> str:
        """Rich color name for TUI rendering."""
        ...
```

### TerrainConfig

```python
@dataclass
class TerrainConfig:
    """Configuration for terrain generation."""
    seed: int | None = None  # None = generate random seed
    world_size: int = 200  # world is [-100, 100] x [-100, 100]
    water_frequency: float = 0.02  # noise frequency for water
    mountain_frequency: float = 0.015  # noise frequency for mountains
    forest_threshold: float = 0.4  # noise value threshold for forest
    meadow_threshold: float = 0.6  # noise value threshold for meadow
    water_threshold: float = -0.3  # noise values below this are water
    mountain_threshold: float = 0.7  # noise values above this are mountains
```

### TerrainGenerator

```python
class TerrainGenerator:
    """Generates terrain deterministically from a seed."""
    
    def __init__(self, config: TerrainConfig | None = None) -> None:
        """Initialize with config. If config.seed is None, generates random seed."""
        self._config = config or TerrainConfig()
        self._seed = self._config.seed or random.randint(0, 2**31 - 1)
        # Noise generator initialized with seed
    
    @property
    def seed(self) -> int:
        """The seed used for terrain generation."""
        return self._seed
    
    def generate_terrain(self, position: Position) -> TerrainType:
        """Generate terrain type for a single position.
        
        Uses multi-octave Perlin noise with the configured frequencies and thresholds.
        Deterministic: same seed + position always returns same terrain type.
        """
        ...
    
    def generate_chunk(
        self, 
        bounds: Bounds
    ) -> Iterator[tuple[Position, TerrainType]]:
        """Generate terrain for all positions within bounds.
        
        Yields (position, terrain_type) tuples for each cell in the bounding box.
        Efficient for bulk terrain queries.
        """
        ...
    
    def is_passable(self, position: Position) -> bool:
        """Check if position is passable (not water or mountain)."""
        return self.generate_terrain(position).passable
```

### TerrainGrid

```python
class TerrainGrid:
    """In-memory terrain storage with on-demand generation."""
    
    def __init__(self, generator: TerrainGenerator) -> None:
        """Initialize with a terrain generator for on-demand generation."""
        self._generator = generator
        self._cache: dict[Position, TerrainType] = {}
    
    def get_terrain(self, position: Position) -> TerrainType:
        """Return terrain type at position.
        
        Returns cached terrain if available, otherwise generates and caches.
        """
        if position not in self._cache:
            self._cache[position] = self._generator.generate_terrain(position)
        return self._cache[position]
    
    def get_terrain_in_bounds(self, bounds: Bounds) -> dict[Position, TerrainType]:
        """Return terrain for all positions within bounds.
        
        Uses chunk generation for efficiency, caches results.
        """
        ...
    
    def is_passable(self, position: Position) -> bool:
        """Check if position is passable."""
        return self.get_terrain(position).passable
    
    def clear_cache(self) -> None:
        """Clear all cached terrain. Used when seed changes."""
        self._cache.clear()
    
    @property
    def seed(self) -> int:
        """Return the generator's seed."""
        return self._generator.seed
```

## Requires

- `Position` (from: `world_state.types`) — Coordinate type for terrain lookups
- `Bounds` (from: `world_state.types`) — Bounding box for bulk terrain queries
- No persistence dependency — seed storage handled by WorldStateManager

## Boundary Rules

- Terrain is **read-only** after generation. No terrain modification API.
- Terrain generation is **deterministic** given a seed. Same seed + position = same terrain.
- TerrainGrid **caches** terrain but does not persist it. Cache is rebuilt on restart.
- The seed is **persisted** in `world_metadata` table with key `terrain_seed`.
- Terrain checks for structure placement are done at `WorldStateManager.create_structure()` level, not inside PositionGrid.
- Village placement searches for passable terrain via `TerrainGrid.is_passable()`.

## Internal Design Notes

### Terrain Generation Algorithm

The terrain generator uses Perlin noise (via the `noise` library, which is a common Python dependency). The algorithm:

1. **Multi-octave noise**: Combine multiple noise frequencies for natural variation
   - Base noise at `water_frequency` determines water placement
   - Base noise at `mountain_frequency` determines mountain placement
   - Both use the same seed for determinism

2. **Threshold classification**:
   ```
   if noise_value < water_threshold:
       terrain = WATER
   elif noise_value > mountain_threshold:
       terrain = MOUNTAIN
   elif noise_value < forest_threshold:
       terrain = FOREST
   elif noise_value < meadow_threshold:
       terrain = MEADOW
   else:
       terrain = PLAIN
   ```

3. **Optional smoothing**: Apply cellular automata passes to smooth terrain edges (not in MVP).

### Village Placement Algorithm

The existing village placement at (0, 0) is replaced with terrain-aware placement:

```python
def _find_village_position(
    self, 
    terrain_grid: TerrainGrid,
    existing_villages: list[Village],
    occupied_positions: set[Position]
) -> Position:
    """Find a valid position for a new village.
    
    Uses spiral search from world origin (0, 0), checking:
    1. Terrain is passable (not water/mountain)
    2. Position is not occupied by existing entities
    3. Position is at least MIN_VILLAGE_DISTANCE from other village centers
    
    Returns the first valid position found.
    Raises RuntimeError if no valid position exists within search radius.
    """
    MIN_VILLAGE_DISTANCE = 15
    MAX_SEARCH_RADIUS = 50
    
    for radius in range(0, MAX_SEARCH_RADIUS + 1):
        for dx, dy in spiral_order(radius):  # Chebyshev distance ordering
            candidate = Position(dx, dy)
            if not terrain_grid.is_passable(candidate):
                continue
            if candidate in occupied_positions:
                continue
            if any(distance(candidate, v.center) < MIN_VILLAGE_DISTANCE for v in existing_villages):
                continue
            return candidate
    
    raise RuntimeError("No valid village position found")
```

### TUI Rendering Integration

The `WorldView.render()` method is updated to render terrain as a background layer:

```python
def render(self) -> Text:
    bounds = self._viewport.get_visible_bounds()
    terrain_map = self._terrain_grid.get_terrain_in_bounds(bounds)
    
    text = Text()
    for y in range(bounds.min_y, bounds.max_y + 1):
        for x in range(bounds.min_x, bounds.max_x + 1):
            pos = Position(x, y)
            terrain = terrain_map.get(pos, TerrainType.PLAIN)
            
            # Layer ordering: terrain -> structures -> agents
            if pos in agent_by_pos:
                agent = agent_by_pos[pos]
                text.append(get_agent_symbol(agent), style=get_agent_color(agent))
            elif pos in struct_by_pos:
                symbol, color = struct_by_pos[pos]
                text.append(symbol, style=color)
            else:
                # Terrain background
                text.append(terrain.symbol, style=terrain.color)
        text.append("\n")
    return text
```

### Persistence Integration

The seed is stored in `world_metadata`:

```python
# In WorldStateManager.load_from_persistence():
terrain_seed = self._state.world_metadata.get("terrain_seed")
if terrain_seed is None:
    # Generate new seed for fresh world
    terrain_seed = random.randint(0, 2**31 - 1)
    self._state.world_metadata["terrain_seed"] = str(terrain_seed)
    await self._persistence.queue_write(
        "world_metadata", "terrain_seed", {"key": "terrain_seed", "value": str(terrain_seed)}
    )
self._terrain_grid = TerrainGrid(TerrainGenerator(TerrainConfig(seed=int(terrain_seed))))
```

No migration is needed because `world_metadata` already exists as a key-value store. The terrain seed is just another key.

### Terrain Display Symbols

| TerrainType | Symbol | Color |
|-------------|--------|-------|
| WATER | `~` | blue |
| MOUNTAIN | `^` | grey85 |
| FOREST | `♣` | green |
| MEADOW | `"` | chartreuse |
| PLAIN | `.` | white (dim) |

### Structure Terrain Affinity

Structures have terrain affinity that affects gameplay (future work, not MVP):

| StructureType | Preferred Terrain | Forbidden Terrain |
|---------------|-------------------|-------------------|
| HOUSE | PLAIN, MEADOW | WATER, MOUNTAIN |
| WORKSHOP | PLAIN | WATER, MOUNTAIN |
| LIBRARY | PLAIN, MEADOW | WATER, MOUNTAIN |
| FORGE | MOUNTAIN (near ore) | WATER |
| TOWER | MOUNTAIN, PLAIN | WATER |
| ROAD | PLAIN, MEADOW, FOREST | WATER, MOUNTAIN |
| WELL | PLAIN, MEADOW | WATER, MOUNTAIN |

For MVP, all structures are simply blocked on WATER and MOUNTAIN terrain.

## API Changes

### WorldStateManager

New methods:

```python
async def get_terrain_at(self, x: int, y: int) -> TerrainType:
    """Return terrain type at position (x, y)."""
    return self._terrain_grid.get_terrain(Position(x, y))

async def is_passable(self, x: int, y: int) -> bool:
    """Check if position is passable for agents and structures."""
    return self._terrain_grid.is_passable(Position(x, y))
```

Modified methods:

```python
# get_or_create_project() — changed to use terrain-aware village placement
# _seed_initial_structures() — validates terrain before creating structures
# create_structure() — validates terrain before placing structure
# _find_spawn_position() — validates terrain for agent spawn positions
```

### WorldView

Modified:

```python
def __init__(self, world_state: Any, viewport: Any, terrain_grid: TerrainGrid) -> None:
    self._terrain_grid = terrain_grid
    ...

def render(self) -> Text:
    # Terrain rendered as background layer
    ...
```

### WorldStateProtocol (protocols.py)

New methods:

```python
async def get_terrain_at(self, x: int, y: int) -> "TerrainType": ...
async def is_passable(self, x: int, y: int) -> bool: ...
```

## File Structure

```
src/hamlet/
├── world_state/
│   ├── __init__.py       # exports TerrainType, TerrainGrid, etc.
│   ├── terrain.py        # NEW: TerrainGenerator, TerrainGrid, TerrainConfig
│   ├── types.py          # TerrainType moved here (or kept in terrain.py)
│   ├── grid.py           # PositionGrid (unchanged)
│   ├── state.py          # WorldState (unchanged)
│   └── manager.py        # WorldStateManager (modified)
├── tui/
│   └── world_view.py     # WorldView (modified for terrain rendering)
└── ...
```

## Testing Strategy

1. **Unit tests for TerrainGenerator**:
   - Deterministic generation (same seed + position = same terrain)
   - All terrain types can be generated
   - Passability matches terrain type

2. **Unit tests for TerrainGrid**:
   - Cache hit/miss behavior
   - Bounds queries return correct positions
   - is_passable delegates to generator

3. **Integration tests for WorldStateManager**:
   - Village placement avoids water/mountains
   - Structure creation fails on water/mountains
   - Agent spawn avoids water/mountains
   - Terrain persists via seed in world_metadata

4. **TUI tests for WorldView**:
   - Terrain renders with correct symbols/colors
   - Agents/structures render on top of terrain
