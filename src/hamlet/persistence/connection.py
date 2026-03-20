"""Database connection management for Hamlet persistence layer."""

from __future__ import annotations

import asyncio

import aiosqlite

__all__ = ["DatabaseConnection"]

_NOT_OPEN = "DatabaseConnection must be used as an async context manager"


class DatabaseConnection:
    """Wraps an aiosqlite.Connection with context manager support and WAL mode."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._cursor: aiosqlite.Cursor | None = None
        self._in_transaction: bool = False
        self._transaction_lock: asyncio.Lock = asyncio.Lock()

    async def __aenter__(self) -> "DatabaseConnection":
        # Open connection with isolation_level=None (autocommit off, manual transactions)
        self._conn = await aiosqlite.connect(self._db_path, isolation_level=None)
        # Enable WAL mode
        await self._conn.execute("PRAGMA journal_mode=WAL")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._cursor:
            try:
                await self._cursor.close()
            except Exception:
                pass
            self._cursor = None
        if self._conn:
            try:
                await self._conn.close()
            except Exception:
                pass
            self._conn = None
        return None  # Don't suppress exceptions

    async def execute(self, sql: str, params: tuple = ()) -> None:
        """Execute a SQL statement."""
        if self._conn is None:
            raise RuntimeError(_NOT_OPEN)
        if self._cursor:
            await self._cursor.close()
            self._cursor = None
        self._cursor = await self._conn.execute(sql, params)

    async def executemany(self, sql: str, params_list: list) -> None:
        """Execute a SQL statement with multiple parameter sets.

        Note: fetchone() and fetchall() must not be called after executemany().
        """
        if self._conn is None:
            raise RuntimeError(_NOT_OPEN)
        await self._conn.executemany(sql, params_list)

    async def fetchone(self) -> tuple | None:
        """Fetch one row from the last executed query."""
        if self._cursor is None:
            raise RuntimeError("No active cursor — call execute() first")
        return await self._cursor.fetchone()

    async def fetchall(self) -> list[tuple]:
        """Fetch all rows from the last executed query."""
        if self._cursor is None:
            raise RuntimeError("No active cursor — call execute() first")
        return await self._cursor.fetchall()

    async def begin_transaction(self) -> None:
        """Begin an explicit transaction.

        Serializes concurrent callers: if another coroutine is currently in a
        transaction, this method waits for it to commit or rollback before
        starting a new one.
        """
        if self._conn is None:
            raise RuntimeError(_NOT_OPEN)
        await self._transaction_lock.acquire()
        try:
            await self._conn.execute("BEGIN")
            self._in_transaction = True
        except Exception:
            self._transaction_lock.release()
            raise

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._conn is None:
            raise RuntimeError(_NOT_OPEN)
        await self._conn.commit()
        self._in_transaction = False
        if self._transaction_lock.locked():
            self._transaction_lock.release()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        if self._conn is None:
            raise RuntimeError(_NOT_OPEN)
        await self._conn.execute("ROLLBACK")
        self._in_transaction = False
        if self._transaction_lock.locked():
            self._transaction_lock.release()
