"""Tests for WriteQueue batching (work item 081).

Run with: pytest tests/test_persistence_queue.py -v
"""
from __future__ import annotations

import asyncio
import pytest

from hamlet.persistence.queue import WriteQueue
from hamlet.persistence.types import WriteOperation


class TestWriteQueue:
    """Test suite for WriteQueue batching."""

    @pytest.mark.asyncio
    async def test_put_drops_when_full(self) -> None:
        """Test put drops operation silently when queue is full (GP-7)."""
        queue = WriteQueue(max_size=2)

        # Create test operations
        op1 = WriteOperation(entity_type="project", entity_id="1", operation="insert", data={})
        op2 = WriteOperation(entity_type="project", entity_id="2", operation="insert", data={})
        op3 = WriteOperation(entity_type="project", entity_id="3", operation="insert", data={})

        # Fill the queue
        await queue.put(op1)
        await queue.put(op2)

        # Third put should drop silently
        await queue.put(op3)  # No exception

        # Verify only first two are in queue
        assert queue.qsize() == 2

        # Verify which items are in queue by draining
        batch = await queue.get_batch(max_items=10)
        assert len(batch) == 2
        ids = {op.entity_id for op in batch}
        assert ids == {"1", "2"}

    @pytest.mark.asyncio
    async def test_get_batch_returns_list(self) -> None:
        """Test get_batch returns a list of WriteOperations."""
        queue = WriteQueue(max_size=10)

        # Add some operations
        for i in range(5):
            op = WriteOperation(
                entity_type="project",
                entity_id=f"proj-{i}",
                operation="insert",
                data={"name": f"Project {i}"}
            )
            await queue.put(op)

        # Get batch
        batch = await queue.get_batch(max_items=3)

        # Verify batch is a list with correct items
        assert isinstance(batch, list)
        assert len(batch) == 3
        assert all(isinstance(op, WriteOperation) for op in batch)

        # Verify correct items were returned
        ids = [op.entity_id for op in batch]
        assert ids == ["proj-0", "proj-1", "proj-2"]

        # Verify remaining items in queue
        assert queue.qsize() == 2

    @pytest.mark.asyncio
    async def test_join_waits_for_task_done(self) -> None:
        """Test join waits until all items are processed via task_done."""
        queue = WriteQueue(max_size=10)

        # Add some operations
        for i in range(3):
            op = WriteOperation(
                entity_type="project",
                entity_id=f"proj-{i}",
                operation="insert",
                data={}
            )
            await queue.put(op)

        # Get batch
        batch = await queue.get_batch(max_items=5)
        assert len(batch) == 3

        # Mark tasks as done
        for _ in batch:
            queue.task_done()

        # Join should complete immediately since all tasks are done
        await queue.join()

        # Queue should be empty
        assert queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_get_batch_empty_queue_timeout(self) -> None:
        """Test get_batch returns empty list when queue is empty."""
        queue = WriteQueue(max_size=10)

        # Get batch from empty queue - should timeout quickly
        batch = await queue.get_batch(max_items=5)

        # Should return empty list after timeout
        assert batch == []

    @pytest.mark.asyncio
    async def test_get_batch_respects_max_items(self) -> None:
        """Test get_batch respects max_items parameter."""
        queue = WriteQueue(max_size=10)

        # Add 10 operations
        for i in range(10):
            op = WriteOperation(
                entity_type="project",
                entity_id=f"proj-{i}",
                operation="insert",
                data={}
            )
            await queue.put(op)

        # Get batch with max_items=3
        batch = await queue.get_batch(max_items=3)
        assert len(batch) == 3

        # Get another batch with max_items=4
        batch2 = await queue.get_batch(max_items=4)
        assert len(batch2) == 4

        # Queue should have 3 remaining
        assert queue.qsize() == 3

    @pytest.mark.asyncio
    async def test_get_batch_partial_fill(self) -> None:
        """Test get_batch returns available items even if less than max."""
        queue = WriteQueue(max_size=10)

        # Add 2 operations
        for i in range(2):
            op = WriteOperation(
                entity_type="project",
                entity_id=f"proj-{i}",
                operation="insert",
                data={}
            )
            await queue.put(op)

        # Get batch with max_items=5 - should return 2
        batch = await queue.get_batch(max_items=5)
        assert len(batch) == 2

    @pytest.mark.asyncio
    async def test_put_nowait(self) -> None:
        """Test put_nowait adds operation synchronously."""
        queue = WriteQueue(max_size=10)

        op = WriteOperation(
            entity_type="project",
            entity_id="proj-1",
            operation="insert",
            data={}
        )

        queue.put_nowait(op)
        assert queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_put_nowait_raises_when_full(self) -> None:
        """Test put_nowait raises QueueFull when queue is full."""
        queue = WriteQueue(max_size=1)

        op1 = WriteOperation(entity_type="project", entity_id="1", operation="insert", data={})
        op2 = WriteOperation(entity_type="project", entity_id="2", operation="insert", data={})

        queue.put_nowait(op1)

        # Second put should raise
        with pytest.raises(asyncio.QueueFull):
            queue.put_nowait(op2)

    @pytest.mark.asyncio
    async def test_multiple_put_get_cycles(self) -> None:
        """Test multiple put/get cycles work correctly."""
        queue = WriteQueue(max_size=10)

        # First cycle
        for i in range(3):
            await queue.put(WriteOperation(entity_type="project", entity_id=f"1-{i}", operation="insert", data={}))

        batch1 = await queue.get_batch(max_items=3)
        for _ in batch1:
            queue.task_done()

        # Second cycle
        for i in range(2):
            await queue.put(WriteOperation(entity_type="project", entity_id=f"2-{i}", operation="insert", data={}))

        batch2 = await queue.get_batch(max_items=2)
        for _ in batch2:
            queue.task_done()

        assert len(batch1) == 3
        assert len(batch2) == 2

    @pytest.mark.asyncio
    async def test_qsize_accuracy(self) -> None:
        """Test qsize returns accurate count."""
        queue = WriteQueue(max_size=10)

        assert queue.qsize() == 0

        for i in range(5):
            await queue.put(WriteOperation(entity_type="project", entity_id=str(i), operation="insert", data={}))
            assert queue.qsize() == i + 1

    @pytest.mark.asyncio
    async def test_join_waits_for_all_tasks(self) -> None:
        """Test join blocks until all tasks are marked done."""
        queue = WriteQueue(max_size=10)

        # Add operations
        for i in range(5):
            await queue.put(WriteOperation(entity_type="project", entity_id=str(i), operation="insert", data={}))

        # Get all items
        batch = await queue.get_batch(max_items=10)
        assert len(batch) == 5

        # Mark only some as done
        for _ in range(2):
            queue.task_done()

        # Join should wait - use asyncio.wait_for to avoid hanging
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.join(), timeout=0.1)

        # Mark remaining as done
        for _ in range(3):
            queue.task_done()

        # Now join should complete
        await asyncio.wait_for(queue.join(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_empty_batch_no_task_done_needed(self) -> None:
        """Test that empty batch doesn't require task_done."""
        queue = WriteQueue(max_size=10)

        # Get from empty queue
        batch = await queue.get_batch(max_items=5)
        assert batch == []

        # Join should complete immediately since nothing was retrieved
        await queue.join()
