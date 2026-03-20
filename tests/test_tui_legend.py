"""Tests for LegendOverlay TUI widget (work item 086).

Test framework: pytest + pytest-asyncio (see pyproject.toml dev dependencies).
Run with: pytest tests/test_tui_legend.py -v
"""
from __future__ import annotations

import pytest

from hamlet.tui.legend import LegendOverlay


class TestLegendOverlay:
    """Test suite for LegendOverlay widget."""

    def test_render_contains_agent_legend(self) -> None:
        """LegendOverlay render output contains agent legend section."""
        legend = LegendOverlay()

        text = legend.render()

        assert "Agents" in text
        assert "Researcher" in text
        assert "Coder" in text
        assert "Executor" in text
        assert "Architect" in text
        assert "Tester" in text
        assert "General" in text

    def test_render_contains_structure_legend(self) -> None:
        """LegendOverlay render output contains structure legend section."""
        legend = LegendOverlay()

        text = legend.render()

        assert "Structures" in text
        assert "House" in text
        assert "Workshop" in text
        assert "Library" in text
        assert "Forge" in text
        assert "Tower" in text
        assert "Road" in text
        assert "Well" in text

    def test_render_contains_materials_legend(self) -> None:
        """LegendOverlay render output contains materials legend section."""
        legend = LegendOverlay()

        text = legend.render()

        assert "Materials" in text
        assert "Wood" in text
        assert "Stone" in text
        assert "Brick" in text
        assert "Enhanced" in text

    def test_render_contains_states_legend(self) -> None:
        """LegendOverlay render output contains states legend section."""
        legend = LegendOverlay()

        text = legend.render()

        assert "States" in text
        assert "Active" in text
        assert "Idle" in text
        assert "Zombie" in text

    def test_render_contains_help_text(self) -> None:
        """LegendOverlay render output contains help text for controls."""
        legend = LegendOverlay()

        text = legend.render()

        assert "Press / to toggle" in text
        assert "Esc to close" in text

    @pytest.mark.asyncio
    async def test_initial_display_is_false(self) -> None:
        """LegendOverlay is initially hidden via display: none CSS."""
        from textual.app import App

        class TestLegendApp(App):
            def compose(self):
                yield LegendOverlay()

        async with TestLegendApp().run_test() as pilot:
            legend = pilot.app.query_one(LegendOverlay)
            assert legend.display is False

    @pytest.mark.asyncio
    async def test_display_can_be_set_true(self) -> None:
        """Setting display to True shows the overlay."""
        from textual.app import App

        class TestLegendApp(App):
            def compose(self):
                yield LegendOverlay()

        async with TestLegendApp().run_test() as pilot:
            legend = pilot.app.query_one(LegendOverlay)
            assert legend.display is False

            legend.display = True
            await pilot.pause()

            assert legend.display is True

    @pytest.mark.asyncio
    async def test_display_can_be_toggled(self) -> None:
        """display can be toggled on and off."""
        from textual.app import App

        class TestLegendApp(App):
            def compose(self):
                yield LegendOverlay()

        async with TestLegendApp().run_test() as pilot:
            legend = pilot.app.query_one(LegendOverlay)
            assert legend.display is False

            legend.display = True
            await pilot.pause()
            assert legend.display is True

            legend.display = False
            await pilot.pause()
            assert legend.display is False

    def test_no_bindings_on_overlay(self) -> None:
        """LegendOverlay has no BINDINGS of its own; key dispatch belongs to HamletApp."""
        assert "BINDINGS" not in LegendOverlay.__dict__

    def test_no_on_key_handler(self) -> None:
        """LegendOverlay has no on_key handler; key handling belongs to HamletApp."""
        assert not hasattr(LegendOverlay, "on_key")

    def test_no_action_toggle_legend(self) -> None:
        """action_toggle_legend is not defined on the overlay; it lives in HamletApp."""
        assert not hasattr(LegendOverlay, "action_toggle_legend")

    def test_no_action_hide_legend(self) -> None:
        """action_hide_legend is not defined on the overlay; it lives in HamletApp."""
        assert not hasattr(LegendOverlay, "action_hide_legend")

    @pytest.mark.asyncio
    async def test_render_integration(self) -> None:
        """Integration test using Textual's testing patterns."""
        from textual.app import App

        class TestLegendApp(App):
            def compose(self):
                yield LegendOverlay()

        async with TestLegendApp().run_test() as pilot:
            legend = pilot.app.query_one(LegendOverlay)
            legend.display = True
            await pilot.pause()

            text = legend.render()
            assert "Legend" in text
            assert legend.display is True
