"""Symbol and color mappings for TUI rendering of agents and structures."""
from __future__ import annotations

from hamlet.world_state.types import Agent, AgentState, AgentType, Structure, StructureType

__all__ = [
    "AGENT_SYMBOL",
    "AGENT_COLORS",
    "get_agent_color",
    "STRUCTURE_SYMBOLS",
    "MATERIAL_COLORS",
    "STAGE_SYMBOLS",
    "get_structure_symbol",
    "get_structure_color",
]

AGENT_SYMBOL = "@"

AGENT_COLORS: dict[AgentType, str] = {
    AgentType.RESEARCHER: "cyan",
    AgentType.CODER: "yellow",
    AgentType.EXECUTOR: "orange1",
    AgentType.PLANNER: "dark_green",
    AgentType.ARCHITECT: "magenta",
    AgentType.TESTER: "blue",
    AgentType.GENERAL: "white",
}


def get_agent_color(agent: Agent) -> str:
    """Return the display color for an agent, accounting for zombie state."""
    base_color = AGENT_COLORS.get(agent.inferred_type, "white")
    if agent.state == AgentState.ZOMBIE:
        return "green"
    return base_color


STRUCTURE_SYMBOLS: dict[StructureType, str] = {
    StructureType.HOUSE: "∩",
    StructureType.WORKSHOP: "◊",
    StructureType.LIBRARY: "⌂",
    StructureType.FORGE: "▲",
    StructureType.TOWER: "⎔",
    # ROAD intentionally omitted — roads use STAGE_SYMBOLS in get_structure_symbol
    StructureType.WELL: "○",
}

MATERIAL_COLORS: dict[str, str] = {
    "wood": "dark_orange",
    "stone": "grey50",
    "brick": "red",
}

STAGE_SYMBOLS: dict[int, str] = {
    0: "░",
    1: "▒",
    2: "▓",
    3: "█",
}


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
