"""Tests for hamlet.gui.symbol_config (WI-268).

Verifies that SymbolConfig dataclasses and default_config() produce correct values.
"""
from __future__ import annotations

import pytest

from hamlet.gui.symbol_config import (
    AgentVisual,
    StructureVisual,
    TerrainVisual,
    SymbolConfig,
    default_config,
)
from hamlet.world_state.types import AgentType, StructureType


class TestDefaultConfig:
    """Tests that default_config() returns values matching symbols.py hardcoded values."""

    def test_returns_symbol_config_instance(self) -> None:
        config = default_config()
        assert isinstance(config, SymbolConfig)

    def test_agent_visual_is_correct_type(self) -> None:
        config = default_config()
        assert isinstance(config.agent, AgentVisual)

    def test_structure_visual_is_correct_type(self) -> None:
        config = default_config()
        assert isinstance(config.structure, StructureVisual)

    def test_terrain_visual_is_correct_type(self) -> None:
        config = default_config()
        assert isinstance(config.terrain, TerrainVisual)


class TestAgentVisual:
    """Tests for AgentVisual values from default_config()."""

    def test_agent_symbol_is_at_sign(self) -> None:
        config = default_config()
        assert config.agent.symbol == "@"

    def test_zombie_color_is_green(self) -> None:
        config = default_config()
        assert config.agent.zombie_color == "green"

    def test_agent_colors_has_all_types(self) -> None:
        config = default_config()
        expected_keys = {
            AgentType.RESEARCHER,
            AgentType.CODER,
            AgentType.EXECUTOR,
            AgentType.PLANNER,
            AgentType.ARCHITECT,
            AgentType.TESTER,
            AgentType.GENERAL,
        }
        assert set(config.agent.colors.keys()) == expected_keys

    def test_agent_color_values(self) -> None:
        config = default_config()
        assert config.agent.colors[AgentType.RESEARCHER] == "cyan"
        assert config.agent.colors[AgentType.CODER] == "yellow"
        assert config.agent.colors[AgentType.EXECUTOR] == "orange1"
        assert config.agent.colors[AgentType.PLANNER] == "dark_green"
        assert config.agent.colors[AgentType.ARCHITECT] == "magenta"
        assert config.agent.colors[AgentType.TESTER] == "blue"
        assert config.agent.colors[AgentType.GENERAL] == "white"


class TestStructureVisual:
    """Tests for StructureVisual values from default_config()."""

    def test_structure_symbols_has_correct_types(self) -> None:
        config = default_config()
        expected_keys = {
            StructureType.HOUSE,
            StructureType.WORKSHOP,
            StructureType.LIBRARY,
            StructureType.FORGE,
            StructureType.TOWER,
            StructureType.WELL,
            StructureType.ROAD,
        }
        assert set(config.structure.symbols.keys()) == expected_keys

    def test_structure_symbol_values(self) -> None:
        config = default_config()
        assert config.structure.symbols[StructureType.HOUSE] == "∩"
        assert config.structure.symbols[StructureType.WORKSHOP] == "◊"
        assert config.structure.symbols[StructureType.LIBRARY] == "⌂"
        assert config.structure.symbols[StructureType.FORGE] == "▲"
        assert config.structure.symbols[StructureType.TOWER] == "⎔"
        assert config.structure.symbols[StructureType.WELL] == "○"

    def test_stage_symbols_has_four_stages(self) -> None:
        config = default_config()
        assert set(config.structure.stage_symbols.keys()) == {0, 1, 2, 3}

    def test_stage_symbol_values(self) -> None:
        config = default_config()
        assert config.structure.stage_symbols[0] == "░"
        assert config.structure.stage_symbols[1] == "▒"
        assert config.structure.stage_symbols[2] == "▓"
        assert config.structure.stage_symbols[3] == "█"

    def test_material_color_values(self) -> None:
        config = default_config()
        assert config.structure.material_colors["wood"] == "dark_orange"
        assert config.structure.material_colors["stone"] == "grey50"
        assert config.structure.material_colors["brick"] == "red"


class TestTerrainVisual:
    """Tests for TerrainVisual values from default_config()."""

    def test_terrain_symbols_has_five_entries(self) -> None:
        config = default_config()
        assert len(config.terrain.symbols) == 5
        expected_keys = {"water", "mountain", "forest", "meadow", "plain"}
        assert set(config.terrain.symbols.keys()) == expected_keys

    def test_terrain_colors_has_five_entries(self) -> None:
        config = default_config()
        assert len(config.terrain.colors) == 5
        expected_keys = {"water", "mountain", "forest", "meadow", "plain"}
        assert set(config.terrain.colors.keys()) == expected_keys

    def test_terrain_symbol_values(self) -> None:
        config = default_config()
        assert config.terrain.symbols["water"] == "~"
        assert config.terrain.symbols["mountain"] == "^"
        assert config.terrain.symbols["forest"] == "♣"
        assert config.terrain.symbols["meadow"] == '"'
        assert config.terrain.symbols["plain"] == "."

    def test_terrain_color_values(self) -> None:
        config = default_config()
        assert config.terrain.colors["water"] == "blue"
        assert config.terrain.colors["mountain"] == "grey85"
        assert config.terrain.colors["forest"] == "green"
        assert config.terrain.colors["meadow"] == "chartreuse"
        assert config.terrain.colors["plain"] == "white"


class TestSymbolConfigImmutability:
    """Tests that SymbolConfig and its components are frozen (immutable)."""

    def test_symbol_config_is_frozen(self) -> None:
        config = default_config()
        with pytest.raises((AttributeError, TypeError)):
            config.agent = None  # type: ignore[misc]

    def test_agent_visual_is_frozen(self) -> None:
        config = default_config()
        with pytest.raises((AttributeError, TypeError)):
            config.agent.symbol = "X"  # type: ignore[misc]

    def test_structure_visual_is_frozen(self) -> None:
        config = default_config()
        with pytest.raises((AttributeError, TypeError)):
            config.structure.material_colors = {}  # type: ignore[misc]

    def test_terrain_visual_is_frozen(self) -> None:
        config = default_config()
        with pytest.raises((AttributeError, TypeError)):
            config.terrain.symbols = {}  # type: ignore[misc]
