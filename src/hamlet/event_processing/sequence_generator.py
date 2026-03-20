"""Monotonic sequence generator for unique event ordering within a process."""

from __future__ import annotations

import asyncio


class SequenceGenerator:
    """Coroutine-safe monotonic sequence generator (safe within a single event loop)."""

    def __init__(self):
        self._counter = 0
        self._lock = asyncio.Lock()

    async def next(self) -> int:
        async with self._lock:
            self._counter += 1
            return self._counter
