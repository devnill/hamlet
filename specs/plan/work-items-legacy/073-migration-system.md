# 073: Migration System

## Objective
Implement database schema creation and migration system for version upgrades.

## Acceptance Criteria
- [ ] File `src/hamlet/persistence/migrations.py` exists
- [ ] `MIGRATIONS` dict maps version number to SQL script
- [ ] Migration 1 creates full schema: schema_version, projects, sessions, villages, agents, structures, event_log, world_metadata tables
- [ ] `async run_migrations(db: DatabaseConnection)` applies pending migrations
- [ ] Reads current version from `schema_version` table
- [ ] Applies migrations in version order
- [ ] Creates indexes: `idx_agents_village`, `idx_agents_session`, `idx_structures_village`, `idx_event_log_timestamp`, `idx_sessions_project`
- [ ] Each migration is atomic (single transaction)

## File Scope
- `src/hamlet/persistence/migrations.py` (create)

## Dependencies
- Depends on: 071, 072
- Blocks: none

## Implementation Notes
Migrations are numbered starting at 1. Version 1 creates all tables and indexes. Future migrations add columns or tables. Each migration runs in a transaction. The schema_version table stores the highest applied migration number.

## Complexity
Medium