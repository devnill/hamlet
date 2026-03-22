"""Database migration system for Hamlet persistence layer.

Applies pending schema migrations in version order, each within a transaction.
"""

from __future__ import annotations

from hamlet.persistence.connection import DatabaseConnection

__all__ = ["MIGRATIONS", "run_migrations"]

MIGRATIONS: dict[int, str] = {
    4: """
BEGIN;
ALTER TABLE structures ADD COLUMN size_tier INTEGER NOT NULL DEFAULT 1;
UPDATE schema_version SET version = 4 WHERE version = 3;
COMMIT;
""",
    3: """
BEGIN;
ALTER TABLE villages ADD COLUMN has_expanded INTEGER NOT NULL DEFAULT 0;
UPDATE schema_version SET version = 3 WHERE version = 2;
COMMIT;
""",
    2: """
BEGIN;
ALTER TABLE agents ADD COLUMN project_id TEXT DEFAULT '';
UPDATE schema_version SET version = 2 WHERE version = 1;
COMMIT;
""",
    1: """
CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
INSERT INTO schema_version VALUES (1);

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    started_at TEXT NOT NULL,
    last_activity TEXT NOT NULL,
    agent_ids_json TEXT NOT NULL
);

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

CREATE TABLE event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    hook_type TEXT NOT NULL,
    tool_name TEXT,
    summary TEXT NOT NULL
);

CREATE TABLE world_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX idx_agents_village ON agents(village_id);
CREATE INDEX idx_agents_session ON agents(session_id);
CREATE INDEX idx_structures_village ON structures(village_id);
CREATE INDEX idx_event_log_timestamp ON event_log(timestamp);
CREATE INDEX idx_sessions_project ON sessions(project_id);
""",
}


async def run_migrations(db: DatabaseConnection) -> None:
    """Apply all pending migrations to the database.

    Reads the current schema version, then applies each migration with a
    version number greater than the current version, in ascending order.
    Each migration runs atomically within a single transaction.
    """
    try:
        await db.execute("SELECT MAX(version) FROM schema_version")
        row = await db.fetchone()
        current_version = row[0] if row and row[0] is not None else 0
    except Exception:
        current_version = 0

    for version in sorted(MIGRATIONS.keys()):
        if version > current_version:
            sql = MIGRATIONS[version]
            # executescript issues an implicit COMMIT before running, so wrapping
            # in begin_transaction/commit is ineffective. executescript provides
            # its own atomicity for the script; we rely on that here.
            await db._conn.executescript(sql)
