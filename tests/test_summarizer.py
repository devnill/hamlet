"""Tests for ActivitySummarizer (work item 111).

Run with: pytest tests/test_summarizer.py -v
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hamlet.inference.summarizer import ActivitySummarizer


class TestActivitySummarizer:
    """Test suite for ActivitySummarizer."""

    @pytest.fixture
    def summarizer(self) -> ActivitySummarizer:
        """Return a summarizer with a mocked Anthropic client."""
        with patch("hamlet.inference.summarizer.anthropic.AsyncAnthropic"):
            return ActivitySummarizer(model="claude-haiku-4-5-20251001")

    @pytest.mark.asyncio
    async def test_summarize_returns_api_response_text(self, summarizer: ActivitySummarizer) -> None:
        """summarize() returns stripped text from the API response."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="  editing config file  ")]
        summarizer._client.messages.create = AsyncMock(return_value=mock_response)

        result = await summarizer.summarize("Edit", {"path": "config.py"})

        assert result == "editing config file"
        summarizer._client.messages.create.assert_awaited_once()
        call_kwargs = summarizer._client.messages.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 20
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"

    @pytest.mark.asyncio
    async def test_summarize_returns_fallback_on_api_error(self, summarizer: ActivitySummarizer) -> None:
        """summarize() returns fallback string when API raises any exception (GP-7)."""
        summarizer._client.messages.create = AsyncMock(side_effect=RuntimeError("network error"))

        result = await summarizer.summarize("Bash", {"command": "ls"})

        assert result == "running command"  # static fallback for Bash

    @pytest.mark.asyncio
    async def test_summarize_returns_fallback_on_timeout(self, summarizer: ActivitySummarizer) -> None:
        """summarize() returns fallback when API call exceeds 5-second timeout."""
        async def slow_create(**kwargs):
            await asyncio.sleep(10)  # exceeds 5s timeout

        summarizer._client.messages.create = slow_create

        result = await summarizer.summarize("Read", {"path": "foo.py"})

        assert result == "reading file"  # static fallback for Read

    def test_fallback_known_tool(self, summarizer: ActivitySummarizer) -> None:
        """_fallback returns the static phrase for a known tool name."""
        assert summarizer._fallback("Write") == "writing file"
        assert summarizer._fallback("Grep") == "searching code"
        assert summarizer._fallback("Glob") == "finding files"

    def test_fallback_unknown_tool(self, summarizer: ActivitySummarizer) -> None:
        """_fallback returns tool_name.lower()+'ing...' for unknown tools."""
        assert summarizer._fallback("Task") == "tasking..."
        assert summarizer._fallback("WebFetch") == "webfetching..."
