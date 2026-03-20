## Verdict: Pass (after rework)

Summarizer implementation correct, but awaited inline in `_handle_post_tool_use` — blocking the event pipeline for up to 5s per event. Current_activity also read from viewport-only agents, missing agents outside the view. No tests for ActivitySummarizer.

## Critical Findings

None.

## Significant Findings

### S1: Summarizer call blocks the event pipeline
- **File**: `src/hamlet/inference/engine.py:279`
- **Issue**: `await self._summarizer.summarize(...)` called inline in `_handle_post_tool_use`. Under sustained activity, every PostToolUse event could wait up to 5s (the timeout) before the engine processes the next event. Guiding principle explicitly requires the call not block the pipeline.
- **Impact**: Type inference, zombie detection, and work-unit accounting stall for all sessions during summarizer execution.
- **Suggested fix**: Use `asyncio.create_task(_summarize_and_update(...))` — fire and forget.

## Minor Findings

### M1: `current_activity` read from viewport agents only
- **File**: `src/hamlet/tui/app.py:150`
- **Issue**: `max(agents_list, ...)` uses `agents_list = get_agents_in_view(bounds)`. If all active agents are outside the viewport, current_activity shows blank even though agents are working.
- **Suggested fix**: Use `get_all_agents()` for the most-recent-agent selection.

### M2: No tests for ActivitySummarizer
- **File**: `tests/` (no test file existed)
- **Issue**: Zero tests for success path, error path, or timeout fallback — all named acceptance criteria.
- **Suggested fix**: Add `tests/test_summarizer.py` with happy path, exception fallback, and timeout fallback tests.

## Unmet Acceptance Criteria

- [ ] "Summarizer call must not block event processing pipeline" — `await` inline, not background task.
