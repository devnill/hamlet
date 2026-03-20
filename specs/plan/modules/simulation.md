# Module: Simulation

## Scope

This module owns the game loop and world progression. It is responsible for:

- Running the simulation tick loop (independent of event arrival)
- Advancing construction progress based on accumulated work units
- Evolving structures (wood -> stone -> brick)
- Building roads between nearby villages
- Managing agent animation states (spin, idle, pulse)
- Detecting zombie/timeout state for inactive agents
- Triggering village expansion and new settlement founding

This module is NOT responsible for:

- Processing events (Event Processing module)
- Storing state (World State module)
- Rendering (TUI module)

## Provides

- `SimulationEngine` class — Main simulation loop
  - `async start()` — Begin simulation tick loop
  - `async stop()` — Graceful shutdown
  - `set_tick_rate(rate: float)` — Adjust simulation speed

- `SimulationState` dataclass — Current simulation state
  - `tick_count: int`
  - `last_tick_at: datetime`
  - `running: bool`

- `SimulationConfig` dataclass — Configuration
  - `tick_rate: float` — Ticks per second (default: 30)
  - `work_unit_scale: float` — Work units per ms (default: 0.01)
  - `zombie_threshold: timedelta` — Idle time before zombie (default: 5 min)
  - `expansion_threshold: int` — Agents before expansion (default: 20)

## Requires

- `WorldState` (from World State module) — Query and update entities
  - `get_all_villages() -> List[Village]`
  - `get_agents_by_village(village_id) -> List[Agent]`
  - `get_structures_by_village(village_id) -> List[Structure]`
  - `update_agent(agent_id, fields)`
  - `update_structure(structure_id, fields)`
  - `create_road(village_id, start, end)`
  - `expand_village(village_id)`
- `asyncio` — Timer-based execution

## Boundary Rules

1. **No event dependency.** Simulation runs independently of event arrival. If no events occur, simulation continues (agents become idle, structures pause).

2. **No rendering.** Simulation updates state only. TUI reads state and renders.

3. **Time-based progression.** Work units are converted to progress based on simulation time, not event timestamps.

4. **Idempotent ticks.** Each tick produces deterministic results given the same state. No random state mutations.

5. **Non-blocking.** Each tick must complete within a bounded time (target: < 10ms for 100 agents).

## Internal Design Notes

### Simulation Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    SIMULATION TICK                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  For each village:                                          │
│    ┌─────────────────────────────────────────────────┐     │
│    │  AGENT STATE UPDATE                             │     │
│    │  - Check last_seen against zombie_threshold    │     │
│    │  - Update state: active -> idle -> zombie      │     │
│    │  - Update animation frame for active agents    │     │
│    └─────────────────────────────────────────────────┘     │
│                                                             │
│    ┌─────────────────────────────────────────────────┐     │
│    │  STRUCTURE PROGRESSION                          │     │
│    │  - Check work_units against thresholds         │     │
│    │  - Advance stage if threshold met              │     │
│    │  - Evolve material (wood -> stone -> brick)    │     │
│    │  - Reset work_units for next stage             │     │
│    └─────────────────────────────────────────────────┘     │
│                                                             │
│    ┌─────────────────────────────────────────────────┐     │
│    │  VILLAGE EXPANSION CHECK                       │     │
│    │  - Count agents in village                     │     │
│    │  - If count > expansion_threshold:             │     │
│    │    - Find expansion site (nearby empty area)   │     │
│    │    - Create road to expansion site             │     │
│    │    - Create new village (future settlement)    │     │
│    └─────────────────────────────────────────────────┘     │
│                                                             │
│  Global:                                                    │
│    ┌─────────────────────────────────────────────────┐     │
│    │  WORLD METADATA UPDATE                          │     │
│    │  - Update tick_count                            │     │
│    │  - Update last_tick_at                          │     │
│    └─────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Animation State Machine

```
┌─────────────────────────────────────────────────────────────┐
│                  AGENT ANIMATION STATES                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐    activity detected    ┌─────────┐            │
│  │  IDLE   │────────────────────────►│ ACTIVE  │            │
│  │ (static)│                          │ (spin)  │            │
│  └─────────┘◄────────────────────────└─────────┘            │
│       ▲         no activity for         │                    │
│       │         short duration          │                    │
│       │                                  │                    │
│       │         no activity for         │                    │
│       │         long duration           ▼                    │
│       │                            ┌─────────┐              │
│       └────────────────────────────│ ZOMBIE  │              │
│            (becomes idle again)     │ (pulse) │              │
│                                     └─────────┘              │
│                                                             │
│  Animation frames per tick:                                 │
│  - IDLE: no animation (symbol: @)                           │
│  - ACTIVE: spin cycle at 4Hz (symbols: - \ | /)            │
│  - ZOMBIE: slow pulse at 0.5Hz (color oscillation)         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Animation Rendering Data

```python
@dataclass
class AnimationState:
    animation_type: "idle" | "spin" | "pulse"
    current_frame: int
    frame_count: int  # Number of frames in animation
    
def get_animation_symbol(agent: Agent, state: AnimationState) -> str:
    """Get the current display symbol for an agent."""
    if agent.state == "idle" or state.animation_type == "idle":
        return "@"  # Static
    
    if state.animation_type == "spin":
        # Spin animation: - \ | /
        symbols = ["-", "\\", "|", "/"]
        return symbols[state.current_frame % 4]
    
    return "@"  # Fallback

def get_animation_color(agent: Agent, state: AnimationState) -> str:
    """Get the current display color for an agent."""
    base_color = TYPE_COLORS.get(agent.inferred_type, "white")
    
    if agent.state == "zombie":
        # Pulse between base color and green
        if state.animation_type == "pulse":
            # Oscillate at 0.5Hz
            phase = (time.time() * 0.5) % 1.0
            if phase < 0.5:
                return blend_color(base_color, "green", 0.3)
        return blend_color(base_color, "green", 0.5)
    
    return base_color
```

### Structure Evolution

```python
# Structure progression rules
STRUCTURE_RULES = {
    StructureType.HOUSE: {
        "stages": ["foundation", "frame", "complete"],
        "thresholds": [100, 500, 1000],
        "materials": ["wood", "wood", "stone"],
        "symbols": ["░", "▒", "▓"],  # Progress symbols
    },
    StructureType.WORKSHOP: {
        "stages": ["foundation", "frame", "complete"],
        "thresholds": [150, 750, 1500],
        "materials": ["wood", "stone", "stone"],
        "symbols": ["░", "▒", "▓"],
    },
    StructureType.LIBRARY: {
        "stages": ["foundation", "frame", "complete"],
        "thresholds": [200, 1000, 2000],
        "materials": ["wood", "stone", "brick"],
        "symbols": ["░", "▒", "▓"],
    },
    # ... other structure types
}

def evolve_structure(structure: Structure) -> None:
    """Check and apply structure evolution."""
    rules = STRUCTURE_RULES[structure.type]
    
    # Check if current stage is complete
    current_threshold = rules["thresholds"][structure.stage]
    if structure.work_units >= current_threshold:
        structure.stage += 1
        structure.work_units = 0  # Reset for next stage
        
        # Update material
        if structure.stage < len(rules["materials"]):
            structure.material = rules["materials"][structure.stage]
```

### Village Expansion

```python
def check_village_expansion(village: Village, agents: List[Agent]) -> Optional[Position]:
    """
    Check if village should expand and return expansion site.
    
    Rules:
    1. If agent count > expansion_threshold, find expansion site
    2. Expansion site should be 20-50 cells from village center
    3. Site should be clear of other villages
    4. Return position for new village center
    """
    if len(agents) < EXPANSION_THRESHOLD:
        return None
    
    # Find clear site
    for distance in range(20, 50):
        for angle in range(0, 360, 15):  # Check every 15 degrees
            rad = math.radians(angle)
            x = village.center.x + int(distance * math.cos(rad))
            y = village.center.y + int(distance * math.sin(rad))
            pos = Position(x, y)
            
            # Check if clear (no nearby villages)
            if is_clear_site(pos, existing_villages):
                return pos
    
    return None

async def create_road_between(village: Village, start: Position, end: Position) -> None:
    """
    Create a road structure between two points.
    
    Uses simple line drawing algorithm (Bresenham's).
    """
    points = bresenham_line(start, end)
    
    for point in points:
        # Create road segment
        await self._world_state.create_structure(
            village_id=village.id,
            structure_type=StructureType.ROAD,
            position=point,
            stage=3,  # Roads start complete
            material="stone"
        )
```

### Implementation Approach

```python
class SimulationEngine:
    def __init__(self, world_state: WorldStateManager, config: SimulationConfig):
        self._world_state = world_state
        self._config = config
        self._state = SimulationState(
            tick_count=0,
            last_tick_at=datetime.utcnow(),
            running=False
        )
        self._task: asyncio.Task | None = None
    
    async def start(self):
        """Start the simulation tick loop."""
        self._state.running = True
        self._task = asyncio.create_task(self._tick_loop())
    
    async def stop(self):
        """Stop the simulation."""
        self._state.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _tick_loop(self):
        """Main simulation loop."""
        while self._state.running:
            try:
                await self._tick()
                self._state.tick_count += 1
                self._state.last_tick_at = datetime.utcnow()
                
                # Sleep until next tick
                await asyncio.sleep(1.0 / self._config.tick_rate)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Simulation tick error: {e}")
                # Continue running despite errors
    
    async def _tick(self):
        """Execute one simulation tick."""
        villages = await self._world_state.get_all_villages()
        
        for village in villages:
            agents = await self._world_state.get_agents_by_village(village.id)
            structures = await self._world_state.get_structures_by_village(village.id)
            
            # Update agent states
            await self._update_agents(agents)
            
            # Update structure progress
            await self._update_structures(structures)
            
            # Check for expansion
            expansion_site = check_village_expansion(village, agents)
            if expansion_site:
                await self._create_expansion(village, expansion_site)
    
    async def _update_agents(self, agents: List[Agent]):
        """Update agent states and animations."""
        now = datetime.utcnow()
        
        for agent in agents:
            # Check for zombie transition
            time_since_seen = now - agent.last_seen
            
            if time_since_seen > self._config.zombie_threshold:
                new_state = "zombie"
            elif time_since_seen > timedelta(minutes=1):
                new_state = "idle"
            else:
                new_state = "active"
            
            if agent.state != new_state:
                await self._world_state.update_agent(agent.id, {"state": new_state})
    
    async def _update_structures(self, structures: List[Structure]):
        """Check for structure evolution."""
        for structure in structures:
            if structure.stage >= 3:  # Already complete
                continue
            
            # Check for stage advancement
            rules = STRUCTURE_RULES.get(structure.type)
            if not rules:
                continue
            
            threshold = rules["thresholds"][structure.stage]
            if structure.work_units >= threshold:
                new_stage = structure.stage + 1
                new_material = rules["materials"][min(new_stage, len(rules["materials"]) - 1)]
                
                await self._world_state.update_structure(structure.id, {
                    "stage": new_stage,
                    "material": new_material,
                    "work_units": 0
                })
```

### Concurrency

The simulation runs as a separate asyncio task alongside the TUI and MCP server:

```python
# In main.py
async def main():
    world_state = WorldStateManager(persistence)
    simulation = SimulationEngine(world_state, config)
    tui = TUIApp(world_state)
    mcp_server = MCPServer(event_queue)
    event_processor = EventProcessor(event_queue, world_state, agent_inference, persistence)
    
    # Start all components
    await simulation.start()
    await mcp_server.start()
    await event_processor.start()
    
    # Run TUI (blocks until exit)
    await tui.run_async()
    
    # Cleanup
    await simulation.stop()
    await mcp_server.stop()
    await event_processor.stop()
```

All state updates go through `WorldStateManager` which handles locking internally.
