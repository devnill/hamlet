"""Tests for StatusBar TUI widget (work item 086).

Test framework: pytest + pytest-asyncio (see pyproject.toml dev dependencies).
Run with: pytest tests/test_tui_status_bar.py -v
"""
from __future__ import annotations

import pytest

from hamlet.tui.status_bar import StatusBar


class TestStatusBar:
    """Test suite for StatusBar widget."""

    def test_render_shows_agent_count(self) -> None:
        """StatusBar render output includes the agent count."""
        bar = StatusBar()
        bar.agent_count = 5

        text = bar.render()

        assert "Agents: 5" in text

    def test_render_shows_village_name(self) -> None:
        """StatusBar render output includes the village name."""
        bar = StatusBar()
        bar.village_name = "TestVillage"

        text = bar.render()

        assert "Village: TestVillage" in text

    def test_render_shows_village_dash_when_empty(self) -> None:
        """StatusBar render output shows em dash when village name is empty."""
        bar = StatusBar()
        bar.village_name = ""

        text = bar.render()

        assert "Village: \u2014" in text

    def test_render_does_not_show_project(self) -> None:
        """StatusBar render output does not contain 'Project:'."""
        bar = StatusBar()

        text = bar.render()

        assert "Project:" not in text

    def test_render_shows_structure_count(self) -> None:
        """StatusBar render output includes the structure count."""
        bar = StatusBar()
        bar.structure_count = 3

        text = bar.render()

        assert "Structures: 3" in text

    def test_render_shows_viewport_position(self) -> None:
        """StatusBar render output includes the viewport position."""
        bar = StatusBar()
        bar.viewport_pos = (10, 20)

        text = bar.render()

        assert "(10, 20)" in text

    def test_reactive_agent_count_update(self) -> None:
        """Reactive property agent_count can be updated."""
        bar = StatusBar()
        assert bar.agent_count == 0

        bar.agent_count = 10

        assert bar.agent_count == 10

    def test_reactive_village_name_update(self) -> None:
        """Reactive property village_name can be updated."""
        bar = StatusBar()
        assert bar.village_name == ""

        bar.village_name = "test-village"

        assert bar.village_name == "test-village"

    def test_render_shows_cursor_summary_when_set(self) -> None:
        """StatusBar render output includes cursor_summary when non-empty."""
        bar = StatusBar()
        bar.cursor_summary = "coder, Edit, TestVillage"

        text = bar.render()

        assert "coder, Edit, TestVillage" in text

    def test_render_hides_cursor_summary_when_empty(self) -> None:
        """StatusBar render output does not show empty cursor_summary."""
        bar = StatusBar()
        bar.cursor_summary = ""

        text = bar.render()

        # The output should not have an extra separator for empty cursor_summary
        assert "│ │" not in text

    def test_cursor_summary_appears_after_viewport_position(self) -> None:
        """Cursor summary appears after viewport position in the output."""
        bar = StatusBar()
        bar.viewport_pos = (5, 10)
        bar.cursor_summary = "House L3, MyVillage"

        text = bar.render()

        # The cursor_summary should appear after the viewport position
        assert "(5, 10) │ House L3, MyVillage" in text

    async def test_render_integration(self) -> None:
        """Integration test using Textual's testing patterns."""
        from textual.app import App

        class TestStatusApp(App):
            def compose(self):
                yield StatusBar()

        async with TestStatusApp().run_test() as pilot:
            status = pilot.app.query_one(StatusBar)
            status.agent_count = 7
            status.structure_count = 4
            status.village_name = "IntegrationVillage"
            await pilot.pause()

            text = status.render()
            assert "Agents: 7" in text
            assert "Structures: 4" in text
            assert "Village: IntegrationVillage" in text
            assert "Project:" not in text

    async def test_render_integration_with_cursor_summary(self) -> None:
        """Integration test with cursor_summary."""
        from textual.app import App

        class TestStatusApp(App):
            def compose(self):
                yield StatusBar()

        async with TestStatusApp().run_test() as pilot:
            status = pilot.app.query_one(StatusBar)
            status.agent_count = 3
            status.village_name = "CursorTest"
            status.cursor_summary = "plain"
            await pilot.pause()

            text = status.render()
            assert "plain" in text
            assert "Village: CursorTest" in text
