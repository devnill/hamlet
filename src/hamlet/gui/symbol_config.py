"""Symbol and color configuration for hamlet renderers.

Defines frozen dataclasses for agent, structure, and terrain visuals,
and a default_config() factory that returns values matching the TUI's
current hardcoded symbol/color mappings.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from hamlet.world_state.types import AgentType, StructureType
from hamlet.inference.types import TYPE_COLORS


@dataclass(frozen=True)
class AgentVisual:
    """Visual configuration for agent rendering."""

    symbol: str
    colors: dict[AgentType, str]
    zombie_color: str

    def __hash__(self) -> int:
        # frozen dataclass requires hashable fields; provide custom hash for dict field
        return hash((self.symbol, tuple(sorted(self.colors.items())), self.zombie_color))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AgentVisual):
            return NotImplemented
        return (
            self.symbol == other.symbol
            and self.colors == other.colors
            and self.zombie_color == other.zombie_color
        )


@dataclass(frozen=True)
class StructureVisual:
    """Visual configuration for structure rendering."""

    symbols: dict[StructureType, str]
    stage_symbols: dict[int, str]
    material_colors: dict[str, str]

    def __hash__(self) -> int:
        return hash((
            tuple(sorted(self.symbols.items())),
            tuple(sorted(self.stage_symbols.items())),
            tuple(sorted(self.material_colors.items())),
        ))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StructureVisual):
            return NotImplemented
        return (
            self.symbols == other.symbols
            and self.stage_symbols == other.stage_symbols
            and self.material_colors == other.material_colors
        )


@dataclass(frozen=True)
class TerrainVisual:
    """Visual configuration for terrain rendering."""

    symbols: dict[str, str]
    colors: dict[str, str]

    def __hash__(self) -> int:
        return hash((
            tuple(sorted(self.symbols.items())),
            tuple(sorted(self.colors.items())),
        ))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TerrainVisual):
            return NotImplemented
        return self.symbols == other.symbols and self.colors == other.colors


@dataclass(frozen=True)
class SymbolConfig:
    """Aggregated symbol and color configuration for all renderable entity types."""

    agent: AgentVisual
    structure: StructureVisual
    terrain: TerrainVisual

    def __hash__(self) -> int:
        return hash((self.agent, self.structure, self.terrain))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SymbolConfig):
            return NotImplemented
        return (
            self.agent == other.agent
            and self.structure == other.structure
            and self.terrain == other.terrain
        )


def default_config() -> SymbolConfig:
    """Return a SymbolConfig with default values matching symbols.py hardcoded values."""
    agent = AgentVisual(
        symbol="@",
        colors=TYPE_COLORS.copy(),
        zombie_color="green",
    )

    structure = StructureVisual(
        symbols={
            StructureType.HOUSE: "∩",
            StructureType.WORKSHOP: "◊",
            StructureType.LIBRARY: "⌂",
            StructureType.FORGE: "▲",
            StructureType.TOWER: "⎔",
            StructureType.WELL: "○",
            StructureType.ROAD: "=",
        },
        stage_symbols={
            0: "░",
            1: "▒",
            2: "▓",
            3: "█",
        },
        material_colors={
            "wood": "dark_orange",
            "stone": "grey50",
            "brick": "red",
        },
    )

    terrain = TerrainVisual(
        symbols={
            "water": "~",
            "mountain": "^",
            "forest": "♣",
            "meadow": '"',
            "plain": ".",
        },
        colors={
            "water": "blue",
            "mountain": "grey85",
            "forest": "green",
            "meadow": "chartreuse",
            "plain": "white",
        },
    )

    return SymbolConfig(agent=agent, structure=structure, terrain=terrain)


__all__ = [
    "AgentVisual",
    "StructureVisual",
    "TerrainVisual",
    "SymbolConfig",
    "default_config",
]
