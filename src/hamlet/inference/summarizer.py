"""LLM-based activity summarizer for agent tool calls."""
from __future__ import annotations

import asyncio
import logging

import anthropic

logger = logging.getLogger(__name__)

__all__ = ["ActivitySummarizer"]


class ActivitySummarizer:
    """Summarizes tool call activity into short human-readable phrases using an LLM."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        self._model = model
        self._client = anthropic.AsyncAnthropic()  # uses ANTHROPIC_API_KEY env var

    async def summarize(self, tool_name: str, tool_input: dict) -> str:
        """Return a short activity phrase describing the tool call.

        Calls the Anthropic API with a 5-second timeout. On any error
        (network, auth, timeout), returns a fallback string per GP-7.
        """
        try:
            input_repr = str(tool_input)[:500]  # truncate to avoid large payloads
            message = await asyncio.wait_for(
                self._client.messages.create(
                    model=self._model,
                    max_tokens=20,
                    system="Describe what this Claude Code tool call is doing in 6 words or fewer. Use lowercase. Examples: 'reading auth module', 'running tests', 'editing config file'.",
                    messages=[{"role": "user", "content": f"Tool: {tool_name}\nInput: {input_repr}"}],
                ),
                timeout=5.0,
            )
            return message.content[0].text.strip()
        except Exception:
            logger.debug("ActivitySummarizer.summarize failed for tool %s, using fallback", tool_name)
            return self._fallback(tool_name)

    def _fallback(self, tool_name: str) -> str:
        """Return a static fallback activity phrase for a tool name."""
        mapping = {
            "Read": "reading file",
            "Write": "writing file",
            "Edit": "editing file",
            "Bash": "running command",
            "Grep": "searching code",
            "Glob": "finding files",
        }
        return mapping.get(tool_name, f"{tool_name.lower()}ing...")
