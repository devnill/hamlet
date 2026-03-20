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

    def test_render_shows_project_name(self) -> None:
        """StatusBar render output includes the project name."""
        bar = StatusBar()
        bar.project_name = "my-project"

        text = bar.render()

        assert "Project: my-project" in text

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

    def test_reactive_project_name_update(self) -> None:
        """Reactive property project_name can be updated."""
        bar = StatusBar()
        assert bar.project_name == ""

        bar.project_name = "test-project"

        assert bar.project_name == "test-project"

    @pytest.mark.asyncio
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
            status.project_name = "integration-test"
            await pilot.pause()

            text = status.render()
            assert "Agents: 7" in text
            assert "Structures: 4" in text
            assert "Project: integration-test" in text
