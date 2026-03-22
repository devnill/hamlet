"""Terrain types and configuration for world generation."""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Iterator

try:
    import noise  # type: ignore

    HAS_NOISE = True
except ImportError:
    HAS_NOISE = False

if TYPE_CHECKING:
    from .types import Bounds, Position


class TerrainType(Enum):
    """Terrain types with inherent properties."""
    WATER = "water"
    MOUNTAIN = "mountain"
    FOREST = "forest"
    MEADOW = "meadow"
    PLAIN = "plain"

    @property
    def passable(self) -> bool:
        """True if agents/structures can occupy this terrain."""
        return self in (TerrainType.FOREST, TerrainType.MEADOW, TerrainType.PLAIN)

    @property
    def symbol(self) -> str:
        """Symbol for TUI rendering."""
        symbols = {
            TerrainType.WATER: "~",
            TerrainType.MOUNTAIN: "^",
            TerrainType.FOREST: "♣",
            TerrainType.MEADOW: '"',
            TerrainType.PLAIN: ".",
        }
        return symbols[self]

    @property
    def color(self) -> str:
        """Rich color name for TUI rendering."""
        colors = {
            TerrainType.WATER: "blue",
            TerrainType.MOUNTAIN: "grey85",
            TerrainType.FOREST: "green",
            TerrainType.MEADOW: "chartreuse",
            TerrainType.PLAIN: "white",
        }
        return colors[self]


@dataclass
class TerrainConfig:
    """Configuration for terrain generation."""
    seed: int | None = None  # None = generate random seed
    world_size: int = 200  # world is [-100, 100] x [-100, 100]
    water_frequency: float = 0.02
    mountain_frequency: float = 0.015
    forest_threshold: float = 0.4
    meadow_threshold: float = 0.6
    water_threshold: float = -0.3
    mountain_threshold: float = 0.7


class TerrainGenerator:
    """Generates terrain deterministically from a seed."""

    def __init__(self, config: TerrainConfig | None = None) -> None:
        self._config = config or TerrainConfig()
        self._seed = (
            self._config.seed
            if self._config.seed is not None
            else random.randint(0, 2**31 - 1)
        )
        self._random = random.Random(self._seed)

    @property
    def seed(self) -> int:
        return self._seed

    def generate_terrain(self, position: "Position") -> TerrainType:
        """Generate terrain type for a single position.

        Deterministic: same seed + position always returns same terrain type.
        Uses Perlin noise if available, otherwise falls back to seeded random.
        """
        if HAS_NOISE:
            return self._generate_with_noise(position)
        return self._generate_with_random(position)

    def _generate_with_noise(self, position: "Position") -> TerrainType:
        """Generate terrain using Perlin noise."""
        x, y = position.x, position.y
        # Multi-frequency noise for natural variation
        water_val = noise.pnoise2(
            x * self._config.water_frequency,
            y * self._config.water_frequency,
            base=self._seed,
        )
        mountain_val = noise.pnoise2(
            x * self._config.mountain_frequency,
            y * self._config.mountain_frequency,
            base=self._seed + 1000,
        )

        if water_val < self._config.water_threshold:
            return TerrainType.WATER
        if mountain_val > self._config.mountain_threshold:
            return TerrainType.MOUNTAIN

        # Use combined noise for forest/meadow/plain
        combined = (water_val + mountain_val) / 2
        if combined < self._config.forest_threshold:
            return TerrainType.FOREST
        if combined < self._config.meadow_threshold:
            return TerrainType.MEADOW
        return TerrainType.PLAIN

    def _generate_with_random(self, position: "Position") -> TerrainType:
        """Generate terrain using seeded random (fallback when noise lib unavailable)."""
        # Deterministic hash from position
        self._random.seed(self._seed + hash((position.x, position.y)))
        val = self._random.random()

        if val < 0.15:  # ~15% water
            return TerrainType.WATER
        if val > 0.90:  # ~10% mountains
            return TerrainType.MOUNTAIN
        if val < 0.40:  # ~25% forest
            return TerrainType.FOREST
        if val < 0.65:  # ~25% meadow
            return TerrainType.MEADOW
        return TerrainType.PLAIN  # ~25% plain

    def generate_chunk(self, bounds: "Bounds") -> Iterator[tuple["Position", TerrainType]]:
        """Generate terrain for all positions within bounds.

        Yields (position, terrain_type) tuples for each cell in the bounding box.
        """
        # Import at runtime to avoid circular import
        from .types import Bounds, Position

        for y in range(bounds.min_y, bounds.max_y + 1):
            for x in range(bounds.min_x, bounds.max_x + 1):
                pos = Position(x, y)
                yield pos, self.generate_terrain(pos)

    def is_passable(self, position: "Position") -> bool:
        """Check if position is passable (not water or mountain)."""
        return self.generate_terrain(position).passable


class TerrainGrid:
    """In-memory terrain storage with on-demand generation."""

    def __init__(self, generator: TerrainGenerator) -> None:
        """Initialize with a terrain generator for on-demand generation."""
        self._generator = generator
        self._cache: dict[Position, TerrainType] = {}

    @property
    def seed(self) -> int:
        """Return the generator's seed."""
        return self._generator.seed

    def get_terrain(self, position: "Position") -> TerrainType:
        """Return terrain type at position.

        Returns cached terrain if available, otherwise generates and caches.
        """
        if position not in self._cache:
            self._cache[position] = self._generator.generate_terrain(position)
        return self._cache[position]

    def get_terrain_in_bounds(self, bounds: "Bounds") -> dict["Position", TerrainType]:
        """Return terrain for all positions within bounds.

        Uses chunk generation for efficiency, caches results.
        """
        result: dict[Position, TerrainType] = {}
        for pos, terrain in self._generator.generate_chunk(bounds):
            self._cache[pos] = terrain
            result[pos] = terrain
        return result

    def is_passable(self, position: "Position") -> bool:
        """Check if position is passable for agents and structures."""
        return self.get_terrain(position).passable

    def clear_cache(self) -> None:
        """Clear all cached terrain. Used when seed changes."""
        self._cache.clear()


__all__ = ["TerrainType", "TerrainConfig", "TerrainGenerator", "TerrainGrid"]