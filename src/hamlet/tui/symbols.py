"""Symbol and color mappings for TUI rendering of agents and structures.

All values are now sourced from hamlet.gui.symbol_config.default_config().
Public exports are preserved identically for backwards compatibility.
"""
from __future__ import annotations

from hamlet.gui.symbol_config import default_config
from hamlet.world_state.types import Agent, AgentState, Structure, StructureType

__all__ = [
    "AGENT_SYMBOL",
    "AGENT_COLORS",
    "get_agent_color",
    "STRUCTURE_SYMBOLS",
    "MATERIAL_COLORS",
    "STAGE_SYMBOLS",
    "get_structure_symbol",
    "get_structure_color",
    "TERRAIN_SYMBOLS",
    "TERRAIN_COLORS",
    "get_terrain_symbol",
    "get_terrain_color",
]

_config = default_config()

AGENT_SYMBOL: str = _config.agent.symbol
AGENT_COLORS = _config.agent.colors

STRUCTURE_SYMBOLS = _config.structure.symbols
MATERIAL_COLORS = _config.structure.material_colors
STAGE_SYMBOLS = _config.structure.stage_symbols

TERRAIN_SYMBOLS = _config.terrain.symbols
TERRAIN_COLORS = _config.terrain.colors


def get_agent_color(agent: Agent) -> str:
    """Return the display color for an agent, accounting for zombie state."""
    base_color = AGENT_COLORS.get(agent.inferred_type, "white")
    if agent.state == AgentState.ZOMBIE:
        return _config.agent.zombie_color
    return base_color


def get_structure_symbol(structure: Structure) -> str:
    """Return the display symbol for a structure.

    Roads use stage progression symbols; all other structures use their type symbol.
    """
    if structure.type == StructureType.ROAD:
        return STAGE_SYMBOLS.get(structure.stage, "#")
    return STRUCTURE_SYMBOLS.get(structure.type, "#")


def get_structure_color(structure: Structure) -> str:
    """Return the display color for a structure based on its material."""
    return MATERIAL_COLORS.get(structure.material, "white")


def get_terrain_symbol(terrain_type: str) -> str:
    """Return symbol for terrain type."""
    return TERRAIN_SYMBOLS.get(terrain_type, ".")


def get_terrain_color(terrain_type: str) -> str:
    """Return Rich color name for terrain type."""
    return TERRAIN_COLORS.get(terrain_type, "white")
