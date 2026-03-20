# Module: World State

## Scope

This module owns the core data model and in-memory state management. It is responsible for:

- Maintaining all world entities: projects, villages, agents, structures
- Managing session-to-project-to-village relationships
- Providing CRUD operations for all entities
- Enforcing entity constraints (position uniqueness, village bounds)
- Coordinating with Persistence module for durability

This module is NOT responsible for:

- Game loop and progression (Simulation module)
- Coordinate translation (Viewport module)
- Rendering (TUI module)
- Inferring agent state (Agent Inference module)

## Provides

- `WorldState` class — Central state container
  - `projects: Dict[str, Project]`
  - `sessions: Dict[str, Session]`
  - `agents: Dict[str, Agent]`
  - `villages: Dict[str, Village]`
  - `structures: Dict[str, Structure]`
  - `event_log: List[EventLogEntry]`

- `WorldStateManager` class — State manipulation interface
  - `async get_or_create_project(project_id, name) -> Project`
  - `async get_or_create_village(project_id) -> Village`
  - `async get_or_create_agent(session_id, parent_id) -> Agent`
  - `async update_agent(agent_id, fields) -> None`
  - `async create_structure(village_id, structure_type, position) -> Structure`
  - `async update_structure(structure_id, fields) -> None`
  - `async add_work_units(agent_id, structure_type, units) -> None`
  - `async get_event_log(limit) -> List[EventLogEntry]`

- Data types:
  - `Project(id, name, config, village_id)`
  - `Session(id, project_id, started_at, last_activity, agent_ids)`
  - `Village(id, project_id, name, center, bounds)`
  - `Agent(id, session_id, village_id, parent_id, inferred_type, color, position, last_seen, state, activity, work_units)`
  - `Structure(id, village_id, type, position, stage, material, work_units, work_required)`
  - `Position(x: int, y: int)`

## Requires

- `Persistence` (from Persistence module) — SQLite storage
  - `async load_state() -> WorldStateData`
  - `async save_project(project)`
  - `async save_agent(agent)`
  - `async save_structure(structure)`
  - `async save_event_log_entry(entry)`
- `asyncio.Lock` — Thread-safe state access

## Boundary Rules

1. **Single source of truth.** World State is the authoritative in-memory store. All reads go through this module.

2. **Write-behind persistence.** State changes queue writes to Persistence; they do not wait for I/O.

3. **Position uniqueness.** No two entities can occupy the same position. Position assignment must check for conflicts.

4. **Village-scoped agents.** Agents belong to exactly one village. Position is relative to village center.

5. **Thread-safe access.** All public methods must be async and acquire the state lock.

## Internal Design Notes

### Data Model

```
┌─────────────────────────────────────────────────────────────┐
│                      WORLD STATE                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Projects (Map<project_id, Project>)                        │
│    └── Village (1:1)                                        │
│         └── Agents (N:1)                                    │
│         └── Structures (N:1)                                │
│                                                             │
│  Sessions (Map<session_id, Session>)                        │
│    └── Project (N:1)                                        │
│    └── Agents (N:1)                                        │
│                                                             │
│  Villages (Map<village_id, Village>)                        │
│    └── Project (1:1)                                        │
│    └── Agents (1:N)                                         │
│    └── Structures (1:N)                                    │
│                                                             │
│  World Grid (Sparse)                                        │
│    └── Map<Position, Entity>                                │
│        - Agent positions                                    │
│        - Structure positions                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Entity Relationships

```
Project (1) ────────── (1) Village
    │                         │
    │                         │
    │                    ┌────┴────┐
    │                    │         │
    │                 (N) │       │ (N)
    │                    │         │
    │               Structures   Agents
    │                              │
    │                              │
    └──────── (N) ────────────────┘
         (via session)

Session (N) ─────────── (1) Project
    │
    │
 (N) │
    │
 Agents
```

### Position Assignment

Agents must be placed in valid positions within their village:

```python
def find_spawn_position(village: Village, parent: Agent | None, 
                        occupied: Set[Position]) -> Position:
    """
    Find a valid spawn position near parent.
    
    Rules:
    1. If parent exists, spawn within 3 cells of parent
    2. If no parent, spawn near village center
    3. Position must not be occupied
    4. Prefer positions closer to parent/center
    """
    center = parent.position if parent else village.center
    
    # Spiral search from center
    for radius in range(1, MAX_SPAWN_RADIUS + 1):
        for dx, dy in spiral_coords(radius):
            pos = Position(center.x + dx, center.y + dy)
            if pos not in occupied:
                if is_within_village(pos, village):
                    return pos
    
    # Fallback: expand village bounds
    return expand_village(village, occupied)
```

### Village Bounds Management

Villages grow as agents expand outward:

```python
def expand_village_bounds(village: Village, new_position: Position) -> None:
    """Expand village bounds to include new position."""
    village.bounds.min_x = min(village.bounds.min_x, new_position.x)
    village.bounds.min_y = min(village.bounds.min_y, new_position.y)
    village.bounds.max_x = max(village.bounds.max_x, new_position.x)
    village.bounds.max_y = max(village.bounds.max_y, new_position.y)
    
    # Queue persistence update
    persistence_queue.put(("village", village))
```

### Work Unit System

Work units accumulate toward structure construction:

```python
# Tool duration maps to work units
WORK_UNIT_SCALE = 0.01  # 1 unit per 100ms of tool duration

# Structure thresholds
STAGE_THRESHOLDS = {
    StructureType.HOUSE: [100, 500, 1000],  # Foundation, frame, complete
    StructureType.WORKSHOP: [150, 750, 1500],
    StructureType.LIBRARY: [200, 1000, 2000],
    StructureType.FORGE: [150, 750, 1500],
    StructureType.TOWER: [300, 1500, 3000],
    StructureType.ROAD: [50],  # Roads are simpler
    StructureType.WELL: [100, 500, 1000],
}

# Material progression
MATERIAL_STAGES = {
    0: "wood",
    1: "wood",
    2: "stone",
    3: "brick",
}
```

### Implementation Approach

```python
class WorldStateManager:
    def __init__(self, persistence: Persistence):
        self._persistence = persistence
        self._state = WorldState()
        self._lock = asyncio.Lock()
        self._grid: Dict[Position, str] = {}  # position -> entity_id
    
    async def get_or_create_agent(self, session_id: str, 
                                   parent_id: str | None) -> Agent:
        async with self._lock:
            # Check if agent already exists for this session
            existing = self._find_agent_by_session(session_id)
            if existing:
                return existing
            
            # Get village for this session's project
            session = self._state.sessions.get(session_id)
            if not session:
                raise ValueError(f"Unknown session: {session_id}")
            
            village = self._state.villages[session.village_id]
            parent = self._state.agents.get(parent_id) if parent_id else None
            
            # Find spawn position
            occupied = set(self._grid.keys())
            position = find_spawn_position(village, parent, occupied)
            
            # Create agent
            agent = Agent(
                id=str(uuid4()),
                session_id=session_id,
                village_id=village.id,
                parent_id=parent_id,
                inferred_type=AgentType.GENERAL,
                color="white",
                position=position,
                last_seen=datetime.utcnow(),
                state="active",
                current_activity=None,
                total_work_units=0
            )
            
            # Update state
            self._state.agents[agent.id] = agent
            self._grid[position] = agent.id
            session.agent_ids.append(agent.id)
            village.agent_ids.append(agent.id)
            
            # Queue persistence
            await self._persistence.queue_write("agent", agent)
            
            return agent
    
    async def add_work_units(self, agent_id: str, structure_type: str, 
                              units: float) -> None:
        async with self._lock:
            agent = self._state.agents.get(agent_id)
            if not agent:
                return
            
            village = self._state.villages[agent.village_id]
            
            # Add to agent's total
            agent.total_work_units += units
            
            # Find or create structure for this type
            structure = self._find_or_create_structure(village, structure_type)
            structure.work_units += units
            
            # Check for stage advancement
            thresholds = STAGE_THRESHOLDS[structure.type]
            current_stage = structure.stage
            next_threshold = thresholds[current_stage] if current_stage < len(thresholds) else float('inf')
            
            if structure.work_units >= next_threshold:
                structure.stage += 1
                structure.material = MATERIAL_STAGES.get(structure.stage, "stone")
                structure.work_units = 0  # Reset for next stage
            
            # Queue persistence
            await self._persistence.queue_write("agent", agent)
            await self._persistence.queue_write("structure", structure)
```

### State Synchronization

```
┌─────────────────┐     Load      ┌─────────────────┐
│   Persistence   │──────────────►│   World State   │
│   (SQLite)      │               │   (In-Memory)   │
└─────────────────┘               └────────┬────────┘
                                           │
                                           │ Write-Behind
                                           │ Queue
                                           ▼
                                   ┌─────────────────┐
                                   │ Persistence    │
                                   │ Write Task     │
                                   └─────────────────┘
```

Load happens once at startup. Writes are queued and processed asynchronously.
