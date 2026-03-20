# Module: Persistence

## Scope

This module owns SQLite storage and persistence. It is responsible for:

- Defining and managing the SQLite database schema
- Loading world state from disk on startup
- Writing world state changes to disk (write-behind)
- Managing the write queue for async persistence
- Database migrations for schema changes
- Checkpointing for crash recovery

This module is NOT responsible for:

- In-memory state (World State module)
- Event processing (Event Processing module)
- Configuration management (separate config module)

## Provides

- `Persistence` class — Main persistence interface
  - `async load_state() -> WorldStateData` — Load all state from disk
  - `async save_project(project: Project) -> None`
  - `async save_session(session: Session) -> None`
  - `async save_agent(agent: Agent) -> None`
  - `async save_structure(structure: Structure) -> None`
  - `async save_village(village: Village) -> None`
  - `async append_event_log(entry: EventLogEntry) -> None`
  - `async checkpoint() -> None` — Flush all pending writes
  - `async close() -> None` — Close database connection

- `PersistenceConfig` dataclass — Configuration
  - `db_path: str` — Path to SQLite file (default: `~/.hamlet/world.db`)
  - `write_queue_size: int` — Max pending writes (default: 1000)
  - `checkpoint_interval: float` — Seconds between checkpoints (default: 5.0)

- `WorldStateData` dataclass — Loaded state
  - `projects: List[Project]`
  - `sessions: List[Session]`
  - `villages: List[Village]`
  - `agents: List[Agent]`
  - `structures: List[Structure]`
  - `metadata: Dict[str, str]`

## Requires

- `aiosqlite` (Python package) — Async SQLite wrapper
- `pathlib.Path` (standard library) — Path handling
- `asyncio` — Async operations

## Boundary Rules

1. **Write-behind.** State changes queue writes; they do not block on I/O. The write queue is processed asynchronously.

2. **No caching.** Persistence does not cache; World State is the in-memory cache. Persistence only reads on startup and writes on changes.

3. **Atomic transactions.** All writes are atomic. Partial updates do not corrupt state.

4. **Schema versioning.** Database includes schema version. Migrations are applied on startup if needed.

5. **Crash recovery.** On startup, incomplete transactions are rolled back. Write queue state is lost (acceptable per guiding principle 7).

## Internal Design Notes

### Database Schema

```sql
-- Schema version
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY
);
INSERT INTO schema_version VALUES (1);

-- Projects: Each Claude Code project/codebase
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Sessions: Claude Code sessions
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    started_at TEXT NOT NULL,
    last_activity TEXT NOT NULL,
    agent_ids_json TEXT NOT NULL
);

-- Villages: One per project
CREATE TABLE villages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE REFERENCES projects(id),
    name TEXT NOT NULL,
    center_x INTEGER NOT NULL,
    center_y INTEGER NOT NULL,
    bounds_min_x INTEGER NOT NULL,
    bounds_min_y INTEGER NOT NULL,
    bounds_max_x INTEGER NOT NULL,
    bounds_max_y INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Agents: All agents ever seen
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    village_id TEXT NOT NULL REFERENCES villages(id),
    parent_id TEXT REFERENCES agents(id),
    inferred_type TEXT NOT NULL,
    color TEXT NOT NULL,
    position_x INTEGER NOT NULL,
    position_y INTEGER NOT NULL,
    last_seen TEXT NOT NULL,
    state TEXT NOT NULL,
    current_activity TEXT,
    total_work_units INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Structures: Built structures in villages
CREATE TABLE structures (
    id TEXT PRIMARY KEY,
    village_id TEXT NOT NULL REFERENCES villages(id),
    type TEXT NOT NULL,
    position_x INTEGER NOT NULL,
    position_y INTEGER NOT NULL,
    stage INTEGER NOT NULL,
    material TEXT NOT NULL,
    work_units INTEGER NOT NULL DEFAULT 0,
    work_required INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Event Log: Recent events for display (capped size)
CREATE TABLE event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    hook_type TEXT NOT NULL,
    tool_name TEXT,
    summary TEXT NOT NULL
);

-- World Metadata: Global state
CREATE TABLE world_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Indexes for common queries
CREATE INDEX idx_agents_village ON agents(village_id);
CREATE INDEX idx_agents_session ON agents(session_id);
CREATE INDEX idx_structures_village ON structures(village_id);
CREATE INDEX idx_event_log_timestamp ON event_log(timestamp);
CREATE INDEX idx_sessions_project ON sessions(project_id);
```

### Write Queue Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WRITE QUEUE                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  State Change                                                │
│      │                                                       │
│      ▼                                                       │
│  ┌─────────────┐                                             │
│  │ Put in      │  Non-blocking                              │
│  │ write queue │  O(1) append                               │
│  └─────────────┘                                             │
│      │                                                       │
│      ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              asyncio.Queue (bounded)                 │   │
│  │                                                      │   │
│  │  (entity_type, entity_id, operation, data)          │   │
│  │  (entity_type, entity_id, operation, data)          │   │
│  │  ...                                                 │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        │                                    │
│                        ▼                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Background Write Task                   │   │
│  │                                                      │   │
│  │  Loop:                                               │   │
│  │    1. Get batch from queue (up to 100 items)        │   │
│  │    2. Group by entity type                          │   │
│  │    3. Execute batch write in transaction           │   │
│  │    4. Commit                                        │   │
│  │    5. Sleep briefly (avoid busy loop)              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Write Queue Implementation

```python
from dataclasses import dataclass
from typing import Literal
import asyncio
import aiosqlite

@dataclass
class WriteOperation:
    entity_type: Literal["project", "session", "agent", "structure", "village", "event_log"]
    entity_id: str
    operation: Literal["insert", "update", "delete"]
    data: dict

class Persistence:
    def __init__(self, config: PersistenceConfig):
        self._config = config
        self._db: aiosqlite.Connection | None = None
        self._write_queue: asyncio.Queue[WriteOperation] | None = None
        self._write_task: asyncio.Task | None = None
    
    async def start(self) -> None:
        """Initialize database and start write task."""
        # Open database
        self._db = await aiosqlite.connect(self._config.db_path)
        
        # Run migrations
        await self._run_migrations()
        
        # Create write queue
        self._write_queue = asyncio.Queue(maxsize=self._config.write_queue_size)
        
        # Start background write task
        self._write_task = asyncio.create_task(self._write_loop())
    
    async def stop(self) -> None:
        """Stop write task and close database."""
        # Signal write task to stop
        if self._write_task:
            self._write_task.cancel()
            try:
                await self._write_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining writes
        await self.checkpoint()
        
        # Close database
        if self._db:
            await self._db.close()
    
    async def queue_write(self, entity_type: str, entity: dict) -> None:
        """Queue a write operation (non-blocking)."""
        operation = WriteOperation(
            entity_type=entity_type,
            entity_id=entity.get("id", ""),
            operation="update",
            data=entity
        )
        
        try:
            self._write_queue.put_nowait(operation)
        except asyncio.QueueFull:
            # Queue is full, drop the write (acceptable per guiding principle 7)
            logger.warning(f"Write queue full, dropping {entity_type} {entity.get('id')}")
    
    async def _write_loop(self) -> None:
        """Background task that processes write queue."""
        while True:
            try:
                # Batch multiple writes
                batch = []
                
                # Get first item (blocking)
                item = await self._write_queue.get()
                batch.append(item)
                
                # Try to get more items (non-blocking)
                while len(batch) < 100:
                    try:
                        item = self._write_queue.get_nowait()
                        batch.append(item)
                    except asyncio.QueueEmpty:
                        break
                
                # Write batch
                await self._write_batch(batch)
                
                # Small delay to prevent busy loop
                await asyncio.sleep(0.01)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Write loop error: {e}")
    
    async def _write_batch(self, batch: List[WriteOperation]) -> None:
        """Write a batch of operations in a transaction."""
        async with self._db.cursor() as cursor:
            await cursor.execute("BEGIN TRANSACTION")
            
            try:
                for op in batch:
                    await self._execute_write(cursor, op)
                
                await cursor.execute("COMMIT")
            except Exception as e:
                await cursor.execute("ROLLBACK")
                logger.error(f"Batch write failed: {e}")
    
    async def _execute_write(self, cursor: aiosqlite.Cursor, op: WriteOperation) -> None:
        """Execute a single write operation."""
        if op.entity_type == "agent":
            await cursor.execute("""
                INSERT OR REPLACE INTO agents 
                (id, session_id, village_id, parent_id, inferred_type, color,
                 position_x, position_y, last_seen, state, current_activity,
                 total_work_units, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                op.data["id"],
                op.data["session_id"],
                op.data["village_id"],
                op.data.get("parent_id"),
                op.data["inferred_type"],
                op.data["color"],
                op.data["position"]["x"],
                op.data["position"]["y"],
                op.data["last_seen"],
                op.data["state"],
                op.data.get("current_activity"),
                op.data["total_work_units"],
                op.data["created_at"],
                op.data["updated_at"]
            ))
        # ... other entity types similar
    
    async def checkpoint(self) -> None:
        """Flush all pending writes."""
        # Process all items in queue
        while not self._write_queue.empty():
            await asyncio.sleep(0.01)  # Let write loop process
        
        # SQLite checkpoint
        await self._db.execute("PRAGMA wal_checkpoint")
```

### Load Implementation

```python
async def load_state(self) -> WorldStateData:
    """Load all state from database."""
    if not self._db:
        raise RuntimeError("Database not initialized")
    
    async with self._db.cursor() as cursor:
        # Load projects
        await cursor.execute("SELECT * FROM projects")
        projects = [self._row_to_project(row) for row in await cursor.fetchall()]
        
        # Load sessions
        await cursor.execute("SELECT * FROM sessions")
        sessions = [self._row_to_session(row) for row in await cursor.fetchall()]
        
        # Load villages
        await cursor.execute("SELECT * FROM villages")
        villages = [self._row_to_village(row) for row in await cursor.fetchall()]
        
        # Load agents
        await cursor.execute("SELECT * FROM agents")
        agents = [self._row_to_agent(row) for row in await cursor.fetchall()]
        
        # Load structures
        await cursor.execute("SELECT * FROM structures")
        structures = [self._row_to_structure(row) for row in await cursor.fetchall()]
        
        # Load metadata
        await cursor.execute("SELECT key, value FROM world_metadata")
        metadata = {row[0]: row[1] for row in await cursor.fetchall()}
    
    return WorldStateData(
        projects=projects,
        sessions=sessions,
        villages=villages,
        agents=agents,
        structures=structures,
        metadata=metadata
    )
```

### Migration System

```python
MIGRATIONS = {
    1: """
        CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
        INSERT INTO schema_version VALUES (1);
        CREATE TABLE projects (...);
        CREATE TABLE sessions (...);
        -- ... full schema
    """,
    # Future migrations:
    # 2: "ALTER TABLE agents ADD COLUMN new_field TEXT;",
}

async def _run_migrations(self) -> None:
    """Run database migrations."""
    # Get current version
    async with self._db.cursor() as cursor:
        await cursor.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        current_version = row[0] if row else 0
    
    # Run pending migrations
    for version, sql in MIGRATIONS.items():
        if version > current_version:
            await self._db.executescript(sql)
            await self._db.execute(
                "INSERT OR REPLACE INTO schema_version VALUES (?)",
                (version,)
            )
            await self._db.commit()
```

### Event Log Management

The event log can grow unbounded. We cap it at a reasonable size:

```python
MAX_EVENT_LOG_ENTRIES = 10000

async def append_event_log(self, entry: EventLogEntry) -> None:
    """Append an event to the log, pruning old entries if needed."""
    async with self._db.cursor() as cursor:
        # Insert new entry
        await cursor.execute("""
            INSERT INTO event_log 
            (timestamp, session_id, project_id, hook_type, tool_name, summary)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.timestamp.isoformat(),
            entry.session_id,
            entry.project_id,
            entry.hook_type,
            entry.tool_name,
            entry.summary
        ))
        
        # Prune old entries
        await cursor.execute("""
            DELETE FROM event_log 
            WHERE id < (
                SELECT id FROM event_log 
                ORDER BY id DESC 
                LIMIT 1 OFFSET ?
            )
        """, (MAX_EVENT_LOG_ENTRIES - 1,))
        
        await cursor.execute("COMMIT")
```

### File Location

```python
def get_default_db_path() -> Path:
    """Get default database path."""
    home = Path.home()
    hamlet_dir = home / ".hamlet"
    hamlet_dir.mkdir(exist_ok=True)
    return hamlet_dir / "world.db"
```
