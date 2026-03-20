# Module: Viewport

## Scope

This module owns the coordinate system and viewport management. It is responsible for:

- Maintaining world coordinate system
- Tracking viewport position and size
- Translating between world and screen coordinates
- Managing scroll state and auto-follow behavior
- Determining which entities are visible in the current view
- Handling user scroll input

This module is NOT responsible for:

- Storing entity positions (World State module)
- Rendering (TUI module)
- Game logic (Simulation module)

## Provides

- `ViewportManager` class — Viewport state and operations
  - `get_viewport() -> ViewportState`
  - `set_center(position: Position) -> None`
  - `scroll(delta_x: int, delta_y: int) -> None`
  - `resize(width: int, height: int) -> None`
  - `world_to_screen(world_pos: Position) -> Position`
  - `screen_to_world(screen_pos: Position) -> Position`
  - `get_visible_bounds() -> BoundingBox`
  - `is_visible(world_pos: Position) -> bool`
  - `auto_follow(agent_id: str) -> None`
  - `get_agents_in_view() -> List[str]`
  - `get_structures_in_view() -> List[str]`

- `ViewportState` dataclass — Current viewport state
  - `center: Position` — World coordinates at viewport center
  - `size: Size` — Viewport dimensions in cells
  - `follow_mode: "center" | "free"` — Auto-follow or manual scroll
  - `follow_target: str | None` — Agent ID to follow (if follow_mode is "center")

- `Position` dataclass — Coordinate position
  - `x: int`
  - `y: int`

- `BoundingBox` dataclass — Axis-aligned bounding box
  - `min_x: int`
  - `min_y: int`
  - `max_x: int`
  - `max_y: int`

## Requires

- `WorldState` (from World State module) — Query entity positions
  - `get_agent(agent_id) -> Agent`
  - `get_village(village_id) -> Village`
  - `get_all_villages() -> List[Village]`
- `asyncio` — For async position queries

## Boundary Rules

1. **No state mutation.** Viewport only reads positions; it never modifies World State.

2. **Screen-space coordinates.** All rendering coordinates are computed by this module. TUI never converts directly.

3. **Deterministic translation.** Same world position + same viewport state = same screen position.

4. **No entity knowledge.** Viewport knows positions, not entity types. TUI determines rendering based on entity type.

5. **Integer coordinates.** All coordinates are integer cell positions. No sub-cell positioning.

## Internal Design Notes

### Coordinate System

```
World Coordinates (Global)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Origin (0, 0) at first village center                      │
│  X increases east (right)                                   │
│  Y increases south (down)                                   │
│  Unlimited extent (sparse storage)                          │
│                                                             │
│                    ┌─────────┐                             │
│                    │ Village │                             │
│                    │   A     │                             │
│                    │ (10,20) │                             │
│                    └─────────┘                             │
│                                                             │
│          ┌───────────────────┐                              │
│          │    Village B      │                              │
│          │    (-50, 30)      │                              │
│          └───────────────────┘                              │
│                                                             │
│                    ┌─────────┐                              │
│                    │ Village │                              │
│                    │   C     │                              │
│                    │ (100,60)│                              │
│                    └─────────┘                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Screen Coordinates (Viewport-Local)
┌─────────────────────────────────────────────────────────────┐
│  (0,0) ──────────────────────────────────────────────────► │
│    │                                                        │
│    │   Viewport shows world coordinates                    │
│    │   relative to center position                          │
│    │                                                        │
│    │   screen_x = world_x - center_x + (width/2)           │
│    │   screen_y = world_y - center_y + (height/2)           │
│    │                                                        │
│    ▼                                                        │
└─────────────────────────────────────────────────────────────┘
```

### Coordinate Translation

```python
def world_to_screen(world_pos: Position, viewport: ViewportState) -> Position:
    """Convert world coordinates to screen coordinates."""
    screen_x = world_pos.x - viewport.center.x + viewport.size.width // 2
    screen_y = world_pos.y - viewport.center.y + viewport.size.height // 2
    return Position(screen_x, screen_y)

def screen_to_world(screen_pos: Position, viewport: ViewportState) -> Position:
    """Convert screen coordinates to world coordinates."""
    world_x = screen_pos.x + viewport.center.x - viewport.size.width // 2
    world_y = screen_pos.y + viewport.center.y - viewport.size.height // 2
    return Position(world_x, world_y)

def is_visible(world_pos: Position, viewport: ViewportState) -> bool:
    """Check if a world position is within the viewport."""
    screen_pos = world_to_screen(world_pos, viewport)
    return (0 <= screen_pos.x < viewport.size.width and
            0 <= screen_pos.y < viewport.size.height)

def get_visible_bounds(viewport: ViewportState) -> BoundingBox:
    """Get the world-space bounding box of the visible area."""
    top_left = screen_to_world(Position(0, 0), viewport)
    bottom_right = screen_to_world(
        Position(viewport.size.width - 1, viewport.size.height - 1), 
        viewport
    )
    return BoundingBox(
        min_x=top_left.x,
        min_y=top_left.y,
        max_x=bottom_right.x,
        max_y=bottom_right.y
    )
```

### Scroll Behavior

```
┌─────────────────────────────────────────────────────────────┐
│                     SCROLL MODES                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FREE MODE:                                                 │
│    - User controls scroll with arrow keys                   │
│    - Viewport stays where user left it                      │
│    - Agents may move out of view                            │
│                                                             │
│  FOLLOW MODE:                                               │
│    - Viewport automatically centers on an agent             │
│    - User scroll temporarily switches to FREE mode          │
│    - 'f' key returns to FOLLOW mode                         │
│    - If followed agent leaves (completes), reverts to FREE  │
│                                                             │
│  AUTO-FOLLOW (default):                                     │
│    - If no explicit follow target, center on village       │
│    - When new agents appear, optionally auto-follow         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Auto-Follow Logic

```python
async def update_auto_follow(self, world_state: WorldStateManager) -> None:
    """
    Update viewport center based on auto-follow rules.
    
    Rules:
    1. If follow_mode is "center" and follow_target exists, center on that agent
    2. If follow_mode is "center" and no target, center on primary village
    3. If follow_mode is "free", do not update center
    """
    if self._state.follow_mode == "free":
        return
    
    if self._state.follow_target:
        agent = await world_state.get_agent(self._state.follow_target)
        if agent:
            self._state.center = agent.position
            return
        # Agent no longer exists, revert to village center
        self._state.follow_target = None
    
    # Center on primary village
    villages = await world_state.get_all_villages()
    if villages:
        primary = villages[0]  # First village is primary
        self._state.center = primary.center
```

### Visibility Optimization

For large worlds, we don't want to check every entity:

```python
class SpatialIndex:
    """Spatial index for fast visibility queries."""
    
    def __init__(self, cell_size: int = 50):
        self._cell_size = cell_size
        self._grid: Dict[Tuple[int, int], Set[str]] = {}  # cell -> entity IDs
    
    def update(self, entity_id: str, position: Position) -> None:
        """Update entity position in index."""
        # Remove from old cell
        # Add to new cell
        cell = self._get_cell(position)
        if cell not in self._grid:
            self._grid[cell] = set()
        self._grid[cell].add(entity_id)
    
    def query(self, bounds: BoundingBox) -> List[str]:
        """Get all entity IDs in bounding box."""
        result = []
        min_cell = self._get_cell(Position(bounds.min_x, bounds.min_y))
        max_cell = self._get_cell(Position(bounds.max_x, bounds.max_y))
        
        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                if (cx, cy) in self._grid:
                    result.extend(self._grid[(cx, cy)])
        
        return result
    
    def _get_cell(self, pos: Position) -> Tuple[int, int]:
        return (pos.x // self._cell_size, pos.y // self._cell_size)
```

### Implementation Approach

```python
class ViewportManager:
    def __init__(self, world_state: WorldStateManager):
        self._world_state = world_state
        self._state = ViewportState(
            center=Position(0, 0),
            size=Size(80, 24),  # Default terminal size
            follow_mode="center",
            follow_target=None
        )
        self._spatial_index = SpatialIndex()
    
    async def initialize(self) -> None:
        """Set initial viewport center to primary village."""
        villages = await self._world_state.get_all_villages()
        if villages:
            self._state.center = villages[0].center
    
    def world_to_screen(self, world_pos: Position) -> Position:
        """Convert world coordinates to screen coordinates."""
        return world_to_screen(world_pos, self._state)
    
    def screen_to_world(self, screen_pos: Position) -> Position:
        """Convert screen coordinates to world coordinates."""
        return screen_to_world(screen_pos, self._state)
    
    def is_visible(self, world_pos: Position) -> bool:
        """Check if a world position is visible in the current viewport."""
        return is_visible(world_pos, self._state)
    
    def get_visible_bounds(self) -> BoundingBox:
        """Get the world-space bounds of the visible area."""
        return get_visible_bounds(self._state)
    
    async def get_agents_in_view(self) -> List[str]:
        """Get all agent IDs currently visible in the viewport."""
        bounds = self.get_visible_bounds()
        return self._spatial_index.query(bounds)
    
    async def get_structures_in_view(self) -> List[str]:
        """Get all structure IDs currently visible in the viewport."""
        bounds = self.get_visible_bounds()
        # Query world state for structures in bounds
        # (This could also use spatial index)
        return await self._world_state.query_structures_in_bounds(bounds)
    
    def scroll(self, delta_x: int, delta_y: int) -> None:
        """Scroll the viewport by the given delta."""
        # Switch to free mode when user scrolls
        self._state.follow_mode = "free"
        self._state.follow_target = None
        
        new_x = self._state.center.x + delta_x
        new_y = self._state.center.y + delta_y
        self._state.center = Position(new_x, new_y)
    
    def set_center(self, position: Position) -> None:
        """Set viewport center to specific position."""
        self._state.center = position
        self._state.follow_mode = "free"
        self._state.follow_target = None
    
    def auto_follow(self, agent_id: str) -> None:
        """Enable auto-follow for a specific agent."""
        self._state.follow_mode = "center"
        self._state.follow_target = agent_id
    
    def resize(self, width: int, height: int) -> None:
        """Handle terminal resize."""
        self._state.size = Size(width, height)
    
    async def update(self) -> None:
        """Update viewport state (call each frame if in follow mode)."""
        await self.update_auto_follow(self._world_state)
```

### Edge Cases

1. **Agent moves outside viewport in follow mode:**
   - Viewport automatically scrolls to keep agent centered

2. **World is smaller than viewport:**
   - World is centered; edges show void (empty space)

3. **Multiple villages far apart:**
   - User must scroll or use village selection to navigate

4. **Terminal resize:**
   - Viewport size updates; center remains the same

5. **Agent followed no longer exists:**
   - Revert to village center or free mode
