"""Tests for terrain symbols and colors in TUI rendering (work item WI-236).

Test framework: pytest (see pyproject.toml dev dependencies).
Run with: pytest tests/test_tui_symbols.py -v
"""
from __future__ import annotations

import pytest

from hamlet.tui.symbols import (
    TERRAIN_SYMBOLS,
    TERRAIN_COLORS,
    get_terrain_symbol,
    get_terrain_color,
)


class TestTerrainSymbols:
    """Test suite for terrain symbols and colors."""

    def test_terrain_symbols_has_five_entries(self) -> None:
        """TERRAIN_SYMBOLS dict has exactly 5 entries matching TerrainType values."""
        assert len(TERRAIN_SYMBOLS) == 5
        expected_keys = {"water", "mountain", "forest", "meadow", "plain"}
        assert set(TERRAIN_SYMBOLS.keys()) == expected_keys

    def test_terrain_colors_has_five_entries(self) -> None:
        """TERRAIN_COLORS dict has exactly 5 entries with valid Rich color names."""
        assert len(TERRAIN_COLORS) == 5
        expected_keys = {"water", "mountain", "forest", "meadow", "plain"}
        assert set(TERRAIN_COLORS.keys()) == expected_keys

    def test_get_terrain_symbol_water_returns_tilde(self) -> None:
        """get_terrain_symbol('water') returns '~'."""
        assert get_terrain_symbol("water") == "~"

    def test_get_terrain_symbol_mountain_returns_caret(self) -> None:
        """get_terrain_symbol('mountain') returns '^'."""
        assert get_terrain_symbol("mountain") == "^"

    def test_get_terrain_color_water_returns_blue(self) -> None:
        """get_terrain_color('water') returns 'blue'."""
        assert get_terrain_color("water") == "blue"

    def test_get_terrain_color_forest_returns_green(self) -> None:
        """get_terrain_color('forest') returns 'green'."""
        assert get_terrain_color("forest") == "green"

    def test_unknown_terrain_type_returns_dot_symbol(self) -> None:
        """Unknown terrain types return '.' symbol."""
        assert get_terrain_symbol("unknown") == "."
        assert get_terrain_symbol("volcano") == "."
        assert get_terrain_symbol("") == "."

    def test_unknown_terrain_type_returns_white_color(self) -> None:
        """Unknown terrain types return 'white' color."""
        assert get_terrain_color("unknown") == "white"
        assert get_terrain_color("volcano") == "white"
        assert get_terrain_color("") == "white"

    def test_terrain_symbol_values_are_correct(self) -> None:
        """All terrain symbols match their expected values."""
        assert TERRAIN_SYMBOLS["water"] == "~"
        assert TERRAIN_SYMBOLS["mountain"] == "^"
        assert TERRAIN_SYMBOLS["forest"] == "♣"
        assert TERRAIN_SYMBOLS["meadow"] == '"'
        assert TERRAIN_SYMBOLS["plain"] == "."

    def test_terrain_color_values_are_correct(self) -> None:
        """All terrain colors match their expected values."""
        assert TERRAIN_COLORS["water"] == "blue"
        assert TERRAIN_COLORS["mountain"] == "grey85"
        assert TERRAIN_COLORS["forest"] == "green"
        assert TERRAIN_COLORS["meadow"] == "chartreuse"
        assert TERRAIN_COLORS["plain"] == "white"