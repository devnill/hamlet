"""Tests for DatabaseConnection context manager and transaction lifecycle (work item 080).

Run with: pytest tests/test_persistence_connection.py -v
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hamlet.persistence.connection import DatabaseConnection


class TestDatabaseConnection:
    """Test suite for DatabaseConnection context manager and transactions."""

    @pytest.mark.asyncio
    async def test_context_manager_opens_wal_mode(self) -> None:
        """DatabaseConnection opens with WAL mode enabled."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db = DatabaseConnection(db_path)
            async with db:
                # Verify WAL mode is enabled
                await db.execute("PRAGMA journal_mode")
                row = await db.fetchone()
                assert row is not None
                assert row[0].lower() == "wal"
        finally:
            Path(db_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_transaction_lifecycle(self) -> None:
        """Transaction lifecycle: begin, execute, commit/rollback works correctly."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db = DatabaseConnection(db_path)
            async with db:
                # Create a test table
                await db.execute("""
                    CREATE TABLE test (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL
                    )
                """)

                # Test commit
                await db.begin_transaction()
                await db.execute("INSERT INTO test (name) VALUES (?)", ("committed",))
                await db.commit()

                # Verify committed data exists
                await db.execute("SELECT name FROM test WHERE id = 1")
                row = await db.fetchone()
                assert row is not None
                assert row[0] == "committed"

                # Test rollback
                await db.begin_transaction()
                await db.execute("INSERT INTO test (name) VALUES (?)", ("rolled_back",))
                await db.rollback()

                # Verify rolled-back data does not exist
                await db.execute("SELECT COUNT(*) FROM test WHERE name = ?", ("rolled_back",))
                row = await db.fetchone()
                assert row is not None
                assert row[0] == 0

                # Verify original data still exists
                await db.execute("SELECT COUNT(*) FROM test")
                row = await db.fetchone()
                assert row is not None
                assert row[0] == 1
        finally:
            Path(db_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_execute_raises_when_not_open(self) -> None:
        """execute() raises RuntimeError when connection not open."""
        db = DatabaseConnection(":memory:")

        with pytest.raises(RuntimeError, match="must be used as an async context manager"):
            await db.execute("SELECT 1")

    @pytest.mark.asyncio
    async def test_fetchone_raises_without_execute(self) -> None:
        """fetchone() raises when no query executed."""
        db = DatabaseConnection(":memory:")

        async with db:
            with pytest.raises(RuntimeError, match="No active cursor"):
                await db.fetchone()

    @pytest.mark.asyncio
    async def test_fetchall_raises_without_execute(self) -> None:
        """fetchall() raises when no query executed."""
        db = DatabaseConnection(":memory:")

        async with db:
            with pytest.raises(RuntimeError, match="No active cursor"):
                await db.fetchall()

    @pytest.mark.asyncio
    async def test_executemany_and_fetch(self) -> None:
        """executemany() inserts multiple rows efficiently."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db = DatabaseConnection(db_path)
            async with db:
                # Create table
                await db.execute("""
                    CREATE TABLE batch_test (
                        id INTEGER PRIMARY KEY,
                        value TEXT
                    )
                """)

                # Insert multiple rows
                params = [(f"value_{i}",) for i in range(5)]
                await db.executemany("INSERT INTO batch_test (value) VALUES (?)", params)

                # Count rows
                await db.execute("SELECT COUNT(*) FROM batch_test")
                row = await db.fetchone()
                assert row is not None
                assert row[0] == 5

                # Fetch all values
                await db.execute("SELECT value FROM batch_test ORDER BY id")
                rows = await db.fetchall()
                assert len(rows) == 5
                assert [r[0] for r in rows] == [f"value_{i}" for i in range(5)]
        finally:
            Path(db_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_begin_transaction_raises_when_not_open(self) -> None:
        """begin_transaction() raises RuntimeError when connection not open."""
        db = DatabaseConnection(":memory:")

        with pytest.raises(RuntimeError, match="must be used as an async context manager"):
            await db.begin_transaction()

    @pytest.mark.asyncio
    async def test_commit_raises_when_not_open(self) -> None:
        """commit() raises RuntimeError when connection not open."""
        db = DatabaseConnection(":memory:")

        with pytest.raises(RuntimeError, match="must be used as an async context manager"):
            await db.commit()

    @pytest.mark.asyncio
    async def test_rollback_raises_when_not_open(self) -> None:
        """rollback() raises RuntimeError when connection not open."""
        db = DatabaseConnection(":memory:")

        with pytest.raises(RuntimeError, match="must be used as an async context manager"):
            await db.rollback()
