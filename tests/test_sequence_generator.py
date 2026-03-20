"""Tests for SequenceGenerator (work item 082).

Test framework: pytest + pytest-asyncio (see pyproject.toml dev dependencies).
Run with: pytest tests/test_sequence_generator.py -v
"""
from __future__ import annotations

import asyncio

import pytest

from hamlet.event_processing.sequence_generator import SequenceGenerator


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def generator() -> SequenceGenerator:
    """Return a SequenceGenerator instance for testing."""
    return SequenceGenerator()


# -----------------------------------------------------------------------------
# Test Class: TestSequenceGenerator
# -----------------------------------------------------------------------------

class TestSequenceGenerator:
    """Tests for SequenceGenerator class."""

    # -------------------------------------------------------------------------
    # AC-10: test_next_returns_incrementing_integers
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_next_returns_incrementing_integers(
        self,
        generator: SequenceGenerator,
    ) -> None:
        """next returns incrementing integers starting from 1."""
        seq1 = await generator.next()
        seq2 = await generator.next()
        seq3 = await generator.next()

        assert seq1 == 1
        assert seq2 == 2
        assert seq3 == 3

    @pytest.mark.asyncio
    async def test_next_returns_sequential_values(
        self,
        generator: SequenceGenerator,
    ) -> None:
        """Each call to next returns the next integer in sequence."""
        prev = 0
        for _ in range(10):
            curr = await generator.next()
            assert curr == prev + 1
            prev = curr

    @pytest.mark.asyncio
    async def test_next_returns_integers(
        self,
        generator: SequenceGenerator,
    ) -> None:
        """next returns integer values."""
        seq = await generator.next()
        assert isinstance(seq, int)

    # -------------------------------------------------------------------------
    # AC-11: test_next_is_async_safe
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_next_is_async_safe(
        self,
        generator: SequenceGenerator,
    ) -> None:
        """next is safe for concurrent access from multiple coroutines."""
        results: list[int] = []

        async def generate() -> None:
            for _ in range(10):
                seq = await generator.next()
                results.append(seq)
                await asyncio.sleep(0)  # Yield control

        # Run multiple coroutines concurrently
        await asyncio.gather(
            generate(),
            generate(),
            generate(),
        )

        # Verify we got 30 unique values
        assert len(results) == 30
        assert len(set(results)) == 30

        # Verify all values are in the expected range
        assert min(results) == 1
        assert max(results) == 30

    @pytest.mark.asyncio
    async def test_next_no_duplicate_sequences_under_concurrent_load(
        self,
        generator: SequenceGenerator,
    ) -> None:
        """next never returns duplicate sequences even under concurrent load."""
        results: list[int] = []

        async def generate_many(count: int) -> None:
            for _ in range(count):
                seq = await generator.next()
                results.append(seq)

        # Run many concurrent tasks
        tasks = [
            generate_many(50)
            for _ in range(10)
        ]
        await asyncio.gather(*tasks)

        # Verify no duplicates
        assert len(results) == 500
        assert len(set(results)) == 500

    @pytest.mark.asyncio
    async def test_next_is_monotonic_under_concurrent_access(
        self,
        generator: SequenceGenerator,
    ) -> None:
        """Sequences are monotonically increasing even with concurrent access."""
        sequences: list[int] = []
        lock = asyncio.Lock()

        async def generate_and_record() -> None:
            for _ in range(20):
                seq = await generator.next()
                async with lock:
                    sequences.append(seq)

        # Run concurrent tasks
        await asyncio.gather(
            generate_and_record(),
            generate_and_record(),
            generate_and_record(),
        )

        # Sort and verify monotonic increase
        sorted_seqs = sorted(sequences)
        assert sorted_seqs == list(range(1, 61))

    @pytest.mark.asyncio
    async def test_separate_generators_are_independent(
        self,
    ) -> None:
        """Each SequenceGenerator instance maintains its own counter."""
        gen1 = SequenceGenerator()
        gen2 = SequenceGenerator()

        seq1_a = await gen1.next()
        seq2_a = await gen2.next()
        seq1_b = await gen1.next()
        seq2_b = await gen2.next()

        assert seq1_a == 1
        assert seq1_b == 2
        assert seq2_a == 1
        assert seq2_b == 2
