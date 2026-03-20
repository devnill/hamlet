"""Tests for EventLog TUI widget (work item 086).

Test framework: pytest + pytest-asyncio (see pyproject.toml dev dependencies).
Run with: pytest tests/test_tui_event_log.py -v
"""
from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import MagicMock

import pytest

from hamlet.tui.event_log import EventLog


def _make_event_entry(timestamp: datetime, summary: str) -> MagicMock:
    """Create a mock EventLogEntry with the given timestamp and summary."""
    event = MagicMock()
    event.timestamp = timestamp
    event.summary = summary
    return event


class TestEventLog:
    """Test suite for EventLog widget."""

    def test_render_shows_timestamped_events(self) -> None:
        """EventLog render output shows events with timestamps."""
        log = EventLog()
        event1 = _make_event_entry(
            datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC),
            "Agent spawned"
        )
        event2 = _make_event_entry(
            datetime(2025, 1, 15, 10, 31, 30, tzinfo=UTC),
            "Structure built"
        )
        log.events = [event1, event2]

        text = log.render()

        assert "[10:30:00] Agent spawned" in text
        assert "[10:31:30] Structure built" in text

    def test_render_limits_to_max_lines(self) -> None:
        """EventLog render output respects max_lines limit."""
        log = EventLog()
        log.max_lines = 3

        events = [
            _make_event_entry(datetime(2025, 1, 15, 10, i, 0, tzinfo=UTC), f"Event {i}")
            for i in range(10)
        ]
        log.events = events

        text = log.render()
        lines = text.split("\n")

        # Should only show last 3 events
        assert len(lines) == 3
        assert "Event 7" in lines[0]
        assert "Event 8" in lines[1]
        assert "Event 9" in lines[2]

    def test_render_no_events(self) -> None:
        """EventLog shows 'No events' when event list is empty."""
        log = EventLog()
        log.events = []

        text = log.render()

        assert text == "No events"

    def test_reactive_max_lines_update(self) -> None:
        """Reactive property max_lines can be updated."""
        log = EventLog()
        assert log.max_lines == 5

        log.max_lines = 10

        assert log.max_lines == 10

    def test_reactive_events_update(self) -> None:
        """Reactive property events can be updated."""
        log = EventLog()
        assert log.events == []

        event = _make_event_entry(datetime.now(UTC), "Test event")
        log.events = [event]

        assert len(log.events) == 1
        assert log.events[0].summary == "Test event"

    def test_render_fewer_events_than_max(self) -> None:
        """EventLog handles case when events < max_lines."""
        log = EventLog()
        log.max_lines = 10

        events = [
            _make_event_entry(datetime(2025, 1, 15, 10, i, 0, tzinfo=UTC), f"Event {i}")
            for i in range(3)
        ]
        log.events = events

        text = log.render()
        lines = text.split("\n")

        # Should show all 3 events
        assert len(lines) == 3
        assert "Event 0" in lines[0]
        assert "Event 1" in lines[1]
        assert "Event 2" in lines[2]

    @pytest.mark.asyncio
    async def test_render_integration(self) -> None:
        """Integration test using Textual's testing patterns."""
        from textual.app import App

        class TestEventApp(App):
            def compose(self):
                yield EventLog()

        async with TestEventApp().run_test() as pilot:
            event_log = pilot.app.query_one(EventLog)
            event = _make_event_entry(datetime.now(UTC), "Integration test event")
            event_log.events = [event]
            await pilot.pause()

            text = event_log.render()
            assert "Integration test event" in text
