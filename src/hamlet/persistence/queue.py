"""Write-behind queue for buffering database writes."""
from __future__ import annotations

import asyncio

from hamlet.persistence.types import WriteOperation

__all__ = ["WriteQueue"]


class WriteQueue:
    """Bounded async queue that buffers write operations for the persistence layer.

    When the queue is full, new writes are silently dropped (GP-7: graceful
    degradation, acceptable data loss).
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._queue: asyncio.Queue[WriteOperation] = asyncio.Queue(maxsize=max_size)

    async def put(self, operation: WriteOperation) -> None:
        """Add operation to queue. Drops silently if full."""
        try:
            self._queue.put_nowait(operation)
        except asyncio.QueueFull:
            pass  # Drop — acceptable per GP-7

    def put_nowait(self, operation: WriteOperation) -> None:
        """Add operation to queue synchronously. Raises QueueFull if full."""
        self._queue.put_nowait(operation)

    async def get_batch(self, max_items: int = 100) -> list[WriteOperation]:
        """Return up to max_items from the queue (non-blocking after first)."""
        batch: list[WriteOperation] = []
        # Block for the first item to avoid busy-polling
        try:
            batch.append(await asyncio.wait_for(self._queue.get(), timeout=1.0))
        except asyncio.TimeoutError:
            return batch
        # Non-blocking drain of remaining items
        for _ in range(max_items - 1):
            try:
                batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return batch

    def task_done(self) -> None:
        """Mark a task as done. Called by consumer after processing batch."""
        self._queue.task_done()

    async def join(self) -> None:
        """Wait until all items in the queue have been processed."""
        await self._queue.join()

    def qsize(self) -> int:
        """Return the current number of items in the queue."""
        return self._queue.qsize()
