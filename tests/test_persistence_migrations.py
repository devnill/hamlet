"""Tests for database migrations (work item 080).

Run with: pytest tests/test_persistence_migrations.py -v
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from hamlet.persistence.connection import DatabaseConnection
from hamlet.persistence.migrations import MIGRATIONS, run_migrations


class TestMigrations:
    """Test suite for database migrations."""

    async def test_run_migrations_creates_all_tables(self) -> None:
        """run_migrations() creates all expected tables and indexes."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db = DatabaseConnection(db_path)
            async with db:
                # Run migrations
                await run_migrations(db)

                # Verify schema_version table exists
                await db.execute("SELECT MAX(version) FROM schema_version")
                row = await db.fetchone()
                assert row is not None
                assert row[0] == 3  # Should be at version 3 after all migrations

                # Verify all tables were created
                await db.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                tables = [row[0] for row in await db.fetchall()]
                expected_tables = [
                    "agents",
                    "event_log",
                    "projects",
                    "schema_version",
                    "sessions",
                    "structures",
                    "villages",
                    "world_metadata",
                ]
                for table in expected_tables:
                    assert table in tables, f"Table {table} not found"

                # Verify indexes were created
                await db.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name LIKE 'idx_%'
                    ORDER BY name
                """)
                indexes = [row[0] for row in await db.fetchall()]
                expected_indexes = [
                    "idx_agents_session",
                    "idx_agents_village",
                    "idx_event_log_timestamp",
                    "idx_sessions_project",
                    "idx_structures_village",
                ]
                for idx in expected_indexes:
                    assert idx in indexes, f"Index {idx} not found"
        finally:
            Path(db_path).unlink(missing_ok=True)

    async def test_run_migrations_idempotent(self) -> None:
        """run_migrations() is idempotent - running twice has no ill effects."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db = DatabaseConnection(db_path)
            async with db:
                # Run migrations first time
                await run_migrations(db)

                # Verify version
                await db.execute("SELECT MAX(version) FROM schema_version")
                row = await db.fetchone()
                assert row is not None
                assert row[0] == 3

                # Run migrations again (should be idempotent)
                await run_migrations(db)

                # Verify version still correct
                await db.execute("SELECT MAX(version) FROM schema_version")
                row = await db.fetchone()
                assert row is not None
                assert row[0] == 3

                # Verify tables still exist and work
                await db.execute("SELECT COUNT(*) FROM projects")
                row = await db.fetchone()
                assert row is not None
                assert row[0] == 0  # Empty but functional

                # Insert test data to verify tables work
                await db.execute("""
                    INSERT INTO projects (id, name, config_json, created_at, updated_at)
                    VALUES ('test-1', 'Test', '{}', '2024-01-01', '2024-01-01')
                """)

                await db.execute("SELECT name FROM projects WHERE id = 'test-1'")
                row = await db.fetchone()
                assert row is not None
                assert row[0] == "Test"
        finally:
            Path(db_path).unlink(missing_ok=True)

    async def test_migrations_dict_not_empty(self) -> None:
        """MIGRATIONS dict contains at least version 1 and 2."""
        assert 1 in MIGRATIONS
        assert len(MIGRATIONS[1]) > 0
        assert "CREATE TABLE" in MIGRATIONS[1]
        assert 2 in MIGRATIONS
        assert "project_id" in MIGRATIONS[2]

    async def test_migration_2_adds_project_id_column(self) -> None:
        """Migration 2 adds project_id TEXT column to agents table."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db = DatabaseConnection(db_path)
            async with db:
                await run_migrations(db)

                # Verify schema version is 3
                await db.execute("SELECT MAX(version) FROM schema_version")
                row = await db.fetchone()
                assert row is not None
                assert row[0] == 3

                # Verify project_id column exists on agents table
                await db.execute("PRAGMA table_info(agents)")
                columns = {row[1] for row in await db.fetchall()}
                assert "project_id" in columns
        finally:
            Path(db_path).unlink(missing_ok=True)
