"""Terrain types and configuration for world generation."""
from __future__ import annotations

import logging
import random
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Iterator

logger = logging.getLogger(__name__)

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
            TerrainType.MEADOW: "bright_green",
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
    # Thresholds for terrain classification:
    # - water_threshold: elevation below this = water (impassable)
    # - mountain_threshold: elevation above this = mountain (impassable)
    # - forest_threshold: moisture above this = forest (higher moisture)
    # - meadow_threshold: moisture above this = meadow (moderate moisture)
    # Note: For correct ordering, forest_threshold should be > meadow_threshold
    forest_threshold: float = 0.55
    meadow_threshold: float = 0.1
    water_threshold: float = -0.25
    mountain_threshold: float = 0.75
    octaves: int = 4  # number of noise layers to combine
    lacunarity: float = 2.0  # frequency multiplier per octave
    persistence: float = 0.5  # amplitude decay per octave
    # Noise scale - lower values create larger, more coherent terrain features
    elevation_scale: float = 0.03  # scale factor for elevation noise
    moisture_scale: float = 0.04  # scale factor for moisture noise
    # Domain warping
    domain_warp_strength: float = 0.5  # strength of coordinate distortion
    # Cellular automata smoothing
    smoothing_passes: int = 4  # number of CA iterations for terrain smoothing
    # Forest grove generation (WI-246)
    forest_grove_count: int = 15  # number of forest grove seeds
    forest_growth_iterations: int = 8  # growth iterations per grove
    # Lake generation (WI-245)
    min_lake_size: int = 10  # minimum connected water cells for a "lake"
    lake_expansion_factor: float = 1.5  # how much to expand small lakes
    # Ridge generation (WI-244)
    ridge_count: int | None = None  # number of ridge chains; None = auto (world_size // 50)
    # Biome region generation (WI-254)
    region_scale: float = 100.0  # characteristic size of biome regions (50-200 cells)
    region_blending: float = 0.3  # 0.0 = sharp transitions, 1.0 = full blending
    # Water features (WI-255)
    river_count: int | None = None  # number of rivers; None = auto (world_size // 80)
    pond_count: int | None = None  # number of ponds; None = auto (world_size // 25)
    min_pond_size: int = 5  # minimum pond size (cells)
    max_pond_size: int = 15  # maximum pond size (cells)
    water_percentage_target: float | None = None  # target water percentage; None = no enforcement
    # Forest clustering (WI-256)
    forest_water_adjacency_bonus: float = 0.3  # bonus probability for forest seeds near water
    forest_region_bias_strength: float = 0.5  # how much region bias affects forest growth
    forest_percentage_target: float | None = None  # target forest percentage; None = no enforcement

    def __post_init__(self) -> None:
        if self.region_scale < 10:
            logger.warning(
                "region_scale=%s is very small; recommended range is 50-200",
                self.region_scale,
            )
        if self.region_scale > 500:
            logger.warning(
                "region_scale=%s is very large; recommended range is 50-200",
                self.region_scale,
            )
        if self.octaves > 10:
            logger.warning(
                "octaves=%s may cause slow generation; recommended range is 1-8",
                self.octaves,
            )
        # water_threshold is an elevation threshold (noise range [-1, 1])
        if self.water_threshold < -1 or self.water_threshold > 1:
            logger.warning("water_threshold=%s is outside normal range [-1, 1]", self.water_threshold)
        # mountain_threshold is an elevation threshold (noise range [-1, 1])
        if self.mountain_threshold < -1 or self.mountain_threshold > 1:
            logger.warning("mountain_threshold=%s is outside normal range [-1, 1]", self.mountain_threshold)
        # forest_threshold and meadow_threshold are moisture thresholds (noise range [-1, 1])
        for name in ("forest_threshold", "meadow_threshold"):
            value = getattr(self, name)
            if value < -1 or value > 1:
                logger.warning("%s=%s is outside normal range [-1, 1]", name, value)
        if self.water_percentage_target is not None and (
            self.water_percentage_target < 0 or self.water_percentage_target > 50
        ):
            logger.warning(
                "water_percentage_target=%s; recommended range is 0-50",
                self.water_percentage_target,
            )
        if self.forest_percentage_target is not None and (
            self.forest_percentage_target < 0 or self.forest_percentage_target > 50
        ):
            logger.warning(
                "forest_percentage_target=%s; recommended range is 0-50",
                self.forest_percentage_target,
            )


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

    def _fbm(
        self,
        x: float,
        y: float,
        octaves: int,
        lacunarity: float,
        persistence: float,
        base: int,
    ) -> float:
        """Fractal Brownian motion - combines multiple noise octaves.

        Args:
            x: X coordinate (unscaled)
            y: Y coordinate (unscaled)
            octaves: Number of noise layers to combine
            lacunarity: Frequency multiplier per octave (typically 2.0)
            persistence: Amplitude decay per octave (typically 0.5)
            base: Seed offset for noise generation

        Returns:
            Normalized noise value in approximately [-1, 1] range
        """
        value = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0

        for _ in range(octaves):
            value += amplitude * noise.pnoise2(
                x * frequency, y * frequency, base=base
            )
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity

        return value / max_value

    def _warped_fbm(self, x: float, y: float) -> float:
        """fBm with domain warping for organic terrain shapes.

        Domain warping distorts the input coordinates using noise,
        creating more natural, flowing terrain patterns.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Warped fBm noise value
        """
        warp = self._config.domain_warp_strength

        # First warp pass
        wx = x + warp * noise.pnoise2(x, y, base=self._seed)
        wy = y + warp * noise.pnoise2(x, y, base=self._seed + 100)

        # Second warp pass for more organic shapes
        wx = wx + warp * 0.5 * noise.pnoise2(wx, wy, base=self._seed + 200)
        wy = wy + warp * 0.5 * noise.pnoise2(wx, wy, base=self._seed + 300)

        return self._fbm(
            wx, wy, self._config.octaves,
            self._config.lacunarity, self._config.persistence,
            self._seed
        )

    def _generate_with_noise(self, position: "Position") -> TerrainType:
        """Generate terrain using Perlin noise with fBm and domain warping.

        Uses two noise layers:
        - Elevation (primary): Generated by _warped_fbm for organic shapes
        - Moisture (secondary): Simple fBm with different seed for biome variation

        Classification uses elevation for water/mountain, then moisture for
        forest/meadow/plain in passable areas.
        """
        x, y = position.x, position.y

        # Use warped fBm for elevation (primary layer)
        elevation = self._warped_fbm(
            x * self._config.elevation_scale,
            y * self._config.elevation_scale
        )

        # Secondary noise for moisture/biome variation (different seed)
        moisture = self._fbm(
            x * self._config.moisture_scale,
            y * self._config.moisture_scale,
            self._config.octaves,
            self._config.lacunarity,
            self._config.persistence,
            self._seed + 1000,
        )

        return self._classify_terrain(elevation, moisture)

    def _classify_terrain(self, elevation: float, moisture: float) -> TerrainType:
        """Classify terrain from combined elevation and moisture values.

        Threshold-based classification:
        - Water at lowest elevations (elevation < water_threshold)
        - Mountain at highest elevations (elevation > mountain_threshold)
        - Forest in high moisture areas (moisture > forest_threshold)
        - Meadow in moderate moisture areas (moisture > meadow_threshold but <= forest_threshold)
        - Plains in dry areas

        Note: For sensible terrain distribution, forest_threshold should be > meadow_threshold.
        The check order ensures higher moisture values produce forest, moderate values produce meadow.

        Args:
            elevation: Noise value from _warped_fbm (approx range [-1, 1])
            moisture: Secondary noise value from _fbm (approx range [-1, 1])

        Returns:
            TerrainType based on threshold classification
        """
        # Water at lowest elevations
        if elevation < self._config.water_threshold:
            return TerrainType.WATER

        # Mountains at highest elevations
        if elevation > self._config.mountain_threshold:
            return TerrainType.MOUNTAIN

        # In passable areas, use moisture thresholds
        # Check higher threshold first for correct ordering
        # Higher moisture -> forest (if moisture > forest_threshold)
        # Moderate moisture -> meadow (if moisture > meadow_threshold)
        # Low moisture -> plain
        if moisture > self._config.forest_threshold:
            return TerrainType.FOREST
        if moisture > self._config.meadow_threshold:
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

    def generate_heightmap_and_moisture(
        self, bounds: "Bounds"
    ) -> tuple[dict["Position", float], dict["Position", float]]:
        """Generate elevation and moisture maps for terrain classification.

        This method exposes the raw noise values used for terrain classification,
        allowing post-processing (ridges, lakes, forests) to use the underlying
        data rather than just the final terrain types.

        Args:
            bounds: Bounding box to generate maps for

        Returns:
            Tuple of (heightmap, moisture_map) dictionaries mapping positions
            to their elevation and moisture values respectively.

        Raises:
            ImportError: If noise library is not available (HAS_NOISE is False)
        """
        if not HAS_NOISE:
            raise ImportError(
                "noise library is required for heightmap generation. "
                "Install with: pip install noise"
            )

        # Import at runtime to avoid circular import
        from .types import Bounds, Position

        heightmap: dict[Position, float] = {}
        moisture_map: dict[Position, float] = {}

        for y in range(bounds.min_y, bounds.max_y + 1):
            for x in range(bounds.min_x, bounds.max_x + 1):
                pos = Position(x, y)
                x_scaled = x * self._config.elevation_scale
                y_scaled = y * self._config.elevation_scale

                # Elevation from warped fBm
                elevation = self._warped_fbm(x_scaled, y_scaled)
                heightmap[pos] = elevation

                # Moisture from secondary fBm with different seed
                moisture = self._fbm(
                    x * self._config.moisture_scale,
                    y * self._config.moisture_scale,
                    self._config.octaves,
                    self._config.lacunarity,
                    self._config.persistence,
                    self._seed + 1000,
                )
                moisture_map[pos] = moisture

        return heightmap, moisture_map

    def is_passable(self, position: "Position") -> bool:
        """Check if position is passable (not water or mountain)."""
        return self.generate_terrain(position).passable

    def generate_ridge_chain(
        self,
        start: "Position",
        end: "Position",
        roughness: float = 0.5,
    ) -> list["Position"]:
        """Generate a ridge chain from start to end using midpoint displacement.

        Uses recursive midpoint displacement with perpendicular offset to create
        natural-looking mountain ridges. The ridge positions can be used to mark
        cells as MOUNTAIN terrain.

        Args:
            start: Starting position of the ridge
            end: Ending position of the ridge
            roughness: Controls how much the ridge deviates from a straight line.
                      Higher values create more jagged ridges. Default 0.5.

        Returns:
            List of Position objects forming the ridge chain, including start and end.
            All positions are guaranteed to be connected (adjacent or diagonal).
        """
        # Import at runtime to avoid circular import
        from .types import Position

        # Handle degenerate case: same start and end
        if start.x == end.x and start.y == end.y:
            return [start]

        points = [start, end]

        # Iterate until segments are small enough (unit length or less)
        max_iterations = 20  # Safety limit to prevent infinite loops
        for _ in range(max_iterations):
            new_points: list[Position] = []

            for i in range(len(points) - 1):
                p1, p2 = points[i], points[i + 1]

                # Calculate midpoint
                mid_x = (p1.x + p2.x) // 2
                mid_y = (p1.y + p2.y) // 2

                # Calculate segment vector and length
                dx = p2.x - p1.x
                dy = p2.y - p1.y
                length = (dx * dx + dy * dy) ** 0.5

                if length < 1.5:
                    # Segment is already unit length, skip displacement
                    continue

                # Calculate perpendicular displacement
                # Use seeded random for determinism
                self._random.seed(self._seed + hash((p1, p2, i)))
                # Limit displacement to ensure connectivity
                max_displacement = min(roughness, 0.3) * length
                displacement = self._random.uniform(-1, 1) * max_displacement

                # Normalize perpendicular direction
                perp_x = -dy / length
                perp_y = dx / length

                # Apply displacement
                mid_x += int(perp_x * displacement)
                mid_y += int(perp_y * displacement)

                new_points.append(Position(mid_x, mid_y))

            if not new_points:
                break

            # Insert new points between existing ones
            for j, p in enumerate(new_points):
                points.insert(2 * j + 1, p)

            # Stop when all segments are unit length or less
            if all(
                abs(points[i].x - points[i + 1].x) + abs(points[i].y - points[i + 1].y) <= 2
                for i in range(len(points) - 1)
            ):
                break

        # Fill in any gaps to ensure all points are connected
        return self._fill_ridge_gaps(points)

    def _fill_ridge_gaps(self, points: list["Position"]) -> list["Position"]:
        """Fill gaps between consecutive points to ensure connectivity.

        After midpoint displacement, consecutive points may have gaps larger than
        1 cell. This method interpolates points to ensure all consecutive points
        are adjacent (Chebyshev distance 1).

        Args:
            points: List of Position objects, potentially with gaps.

        Returns:
            New list of Position objects with all gaps filled.
        """
        # Import at runtime to avoid circular import
        from .types import Position

        if len(points) <= 1:
            return points

        result: list[Position] = [points[0]]

        for i in range(1, len(points)):
            prev = points[i - 1]
            curr = points[i]

            # Calculate Chebyshev distance
            dx = curr.x - prev.x
            dy = curr.y - prev.y
            chebyshev_dist = max(abs(dx), abs(dy))

            if chebyshev_dist <= 1:
                # Already connected, just add the point
                result.append(curr)
            else:
                # Need to interpolate points between prev and curr
                # Use simple line interpolation
                steps = chebyshev_dist
                for step in range(1, steps + 1):
                    interp_x = prev.x + dx * step // steps
                    interp_y = prev.y + dy * step // steps
                    interp_pos = Position(interp_x, interp_y)
                    # Avoid duplicating the last point if it's the same as current
                    if step == steps:
                        result.append(curr)
                    else:
                        result.append(interp_pos)

        return result

    def _generate_ridge_seeds(
        self,
        heightmap: dict["Position", float],
        num_ridges: int | None = None,
    ) -> list[tuple["Position", "Position"]]:
        """Find pairs of high-elevation points to connect with ridges.

        Identifies peak positions (cells with elevation above a threshold)
        and selects pairs to connect with ridge chains.

        Args:
            heightmap: Dictionary mapping positions to elevation values.
                       Expected to come from fBm terrain generation.
            num_ridges: Number of ridge pairs to generate. If None, calculated
                       based on world_size (world_size // 50).

        Returns:
            List of (start, end) position tuples for ridge generation.
        """
        # Import at runtime to avoid circular import
        from .types import Position

        # Find peaks: positions with elevation above threshold
        # Use 80% of mountain_threshold as peak threshold
        peak_threshold = self._config.mountain_threshold * 0.8
        peaks = [pos for pos, h in heightmap.items() if h > peak_threshold]

        if len(peaks) < 2:
            return []

        # Determine number of ridges based on world size
        if num_ridges is None:
            num_ridges = max(1, self._config.world_size // 50)

        # Seed random for determinism
        self._random.seed(self._seed + 9999)

        # Select pairs of peaks to connect
        pairs: list[tuple[Position, Position]] = []
        used_peaks: set[Position] = set()

        for _ in range(num_ridges):
            if len(peaks) - len(used_peaks) < 2:
                break

            # Get available peaks
            available = [p for p in peaks if p not in used_peaks]
            if len(available) < 2:
                break

            # Select two random peaks
            p1, p2 = self._random.sample(available, 2)
            pairs.append((p1, p2))
            used_peaks.add(p1)
            used_peaks.add(p2)

        return pairs

    def generate_terrain_with_ridges(
        self,
        position: "Position",
        ridges: list[list["Position"]] | None = None,
    ) -> TerrainType:
        """Generate terrain type, overriding with MOUNTAIN for ridge positions.

        First generates terrain using standard fBm classification, then checks
        if the position is part of any ridge chain. Ridge positions are always
        marked as MOUNTAIN terrain.

        Args:
            position: Position to generate terrain for
            ridges: List of ridge chains (each chain is a list of Position).
                   If None, uses default ridge generation.

        Returns:
            TerrainType for the position, considering ridges.
        """
        # Get base terrain
        base_terrain = self.generate_terrain(position)

        # Check if position is on any ridge
        if ridges:
            for ridge in ridges:
                if position in ridge:
                    return TerrainType.MOUNTAIN

        return base_terrain

    def _get_region_bias(self, position: "Position") -> dict[TerrainType, float]:
        """Calculate biome region bias for a position.

        Uses low-frequency noise to create large-scale biome regions. Each region
        has a tendency toward certain terrain types based on the region's "character".

        The bias is returned as a dictionary mapping terrain types to bias values.
        These values modify the probability of each terrain type at this position.

        Args:
            position: Position to calculate bias for

        Returns:
            Dictionary mapping TerrainType to bias values (typically -0.3 to +0.3)
        """
        if not HAS_NOISE:
            # Without noise library, return neutral bias
            return {
                TerrainType.WATER: 0.0,
                TerrainType.MOUNTAIN: 0.0,
                TerrainType.FOREST: 0.0,
                TerrainType.MEADOW: 0.0,
                TerrainType.PLAIN: 0.0,
            }

        x, y = position.x, position.y

        # Scale factor based on region_scale parameter
        # Lower scale = larger regions (inverse relationship)
        # region_scale=100 should produce regions ~100 cells across
        region_scale_factor = 1.0 / self._config.region_scale

        # Generate three independent noise layers for biome character
        # Using very low frequency for macro-scale patterns
        region_octaves = 2  # Fewer octaves for smoother regions
        region_lacunarity = 2.0
        region_persistence = 0.5

        # Primary biome character (determines dominant terrain tendency)
        biome_char = self._fbm(
            x * region_scale_factor,
            y * region_scale_factor,
            region_octaves,
            region_lacunarity,
            region_persistence,
            self._seed + 5000,  # Different seed space for regions
        )

        # Secondary biome modifier (adds variation within regions)
        biome_mod = self._fbm(
            x * region_scale_factor * 1.5,
            y * region_scale_factor * 1.5,
            region_octaves,
            region_lacunarity,
            region_persistence,
            self._seed + 6000,
        )

        # Combine to determine biome bias
        # biome_char ranges roughly [-1, 1]
        # Map this to terrain type biases

        bias: dict[TerrainType, float] = {
            TerrainType.WATER: 0.0,
            TerrainType.MOUNTAIN: 0.0,
            TerrainType.FOREST: 0.0,
            TerrainType.MEADOW: 0.0,
            TerrainType.PLAIN: 0.0,
        }

        # Scale bias strength by region_blending parameter
        bias_strength = self._config.region_blending * 0.3  # Max ±0.15 adjustment (bias_strength * biome_char * 0.5)

        # Map biome_char to terrain biases
        # Values near -1: wet bias (more water/forest)
        # Values near 0: moderate bias (meadow focus)
        # Values near +1: dry/elevated bias (more mountain/plain)

        if biome_char < -0.33:
            # Wet region bias: more water and forest
            # biome_char ranges from -1 (wettest) to -0.33 (boundary)
            # Water bias should be HIGHER for wetter regions (more negative biome_char)
            # Use -biome_char to invert: -1 -> 1.0 (max), -0.33 -> 0.33 (min)
            bias[TerrainType.WATER] = bias_strength * (-biome_char) * 0.5
            bias[TerrainType.FOREST] = bias_strength * 0.3
            # Secondary modifier adds local variation
            bias[TerrainType.FOREST] += biome_mod * bias_strength * 0.2
        elif biome_char < 0.33:
            # Temperate region bias: balanced, slight meadow tendency
            bias[TerrainType.MEADOW] = bias_strength * 0.2
            bias[TerrainType.PLAIN] = bias_strength * 0.1
        else:
            # Dry/elevated region bias: more plains and mountains
            bias[TerrainType.PLAIN] = bias_strength * (biome_char - 0.33) * 0.5
            bias[TerrainType.MOUNTAIN] = bias_strength * 0.15
            # Secondary modifier can add variety
            bias[TerrainType.MOUNTAIN] += biome_mod * bias_strength * 0.1

        return bias

    def _apply_region_bias(
        self,
        elevation: float,
        moisture: float,
        region_bias: dict[TerrainType, float],
    ) -> TerrainType:
        """Apply biome region bias to terrain classification.

        Modifies the effective elevation and moisture thresholds based on
        region bias, then classifies terrain. This creates terrain that
        reflects regional character while maintaining local variation.

        Args:
            elevation: Raw elevation value from warped fBm
            moisture: Raw moisture value from secondary fBm
            region_bias: Bias values from _get_region_bias()

        Returns:
            TerrainType after applying region-influenced classification
        """
        # Apply region bias by adjusting thresholds
        # A positive bias for WATER makes it easier to become water
        # (effectively lowers the water_threshold)

        # Adjusted thresholds (lower = more of that terrain type)
        water_threshold = self._config.water_threshold - region_bias[TerrainType.WATER]
        mountain_threshold = self._config.mountain_threshold - region_bias[TerrainType.MOUNTAIN]
        forest_threshold = self._config.forest_threshold - region_bias[TerrainType.FOREST]
        meadow_threshold = self._config.meadow_threshold - region_bias[TerrainType.MEADOW]

        # Standard classification with adjusted thresholds
        # Water at lowest elevations
        if elevation < water_threshold:
            return TerrainType.WATER

        # Mountains at highest elevations
        if elevation > mountain_threshold:
            return TerrainType.MOUNTAIN

        # In passable areas, use moisture thresholds
        if moisture > forest_threshold:
            return TerrainType.FOREST
        if moisture > meadow_threshold:
            return TerrainType.MEADOW
        return TerrainType.PLAIN

    def generate_terrain_with_regions(self, position: "Position") -> TerrainType:
        """Generate terrain with biome region influence.

        Combines local terrain noise with regional biome biases to create
        coherent terrain patterns at multiple scales.

        Args:
            position: Position to generate terrain for

        Returns:
            TerrainType influenced by local noise and regional bias
        """
        if not HAS_NOISE:
            return self._generate_with_random(position)

        x, y = position.x, position.y

        # Get elevation and moisture from standard fBm
        elevation = self._warped_fbm(
            x * self._config.elevation_scale,
            y * self._config.elevation_scale
        )

        moisture = self._fbm(
            x * self._config.moisture_scale,
            y * self._config.moisture_scale,
            self._config.octaves,
            self._config.lacunarity,
            self._config.persistence,
            self._seed + 1000,
        )

        # Get regional biome bias
        region_bias = self._get_region_bias(position)

        # Apply bias to classification
        return self._apply_region_bias(elevation, moisture, region_bias)

    def generate_forest_groves(
        self,
        grid: dict["Position", TerrainType],
        moisture_map: dict["Position", float],
        water_positions: set["Position"] | None = None,
        region_biases: dict["Position", dict[TerrainType, float]] | None = None,
        grove_count: int | None = None,
        growth_iterations: int | None = None,
    ) -> dict["Position", TerrainType]:
        """Create forest groves from seeds with water adjacency and region bias.

        This method applies a seeding and growth algorithm to create natural
        forest clusters. Seeds are preferentially placed near water features
        and in high-moisture passable positions, then iteratively expand to
        neighboring cells with moisture and region bias influence.

        WI-256: Forest Clustering Near Features
        - Forests preferentially spawn near water features
        - Forest density varies by biome region (higher in wet/forest-prone regions)
        - Forests form coherent clusters, not scattered cells

        Args:
            grid: Dictionary mapping positions to terrain types (after smoothing
                  and any ridge/lake/river/pond processing)
            moisture_map: Dictionary mapping positions to moisture values
            water_positions: Set of positions that are water (rivers, lakes, ponds).
                           Used to preferentially place forest seeds near water.
                           If None, derived from grid (positions with WATER terrain).
            region_biases: Dictionary mapping positions to terrain bias dictionaries.
                          Used to vary forest density by biome region.
                          If None, no region bias is applied.
            grove_count: Number of forest grove seeds to plant. If None, uses
                        config's forest_grove_count (default 15)
            growth_iterations: Number of growth iterations per grove. If None,
                              uses config's forest_growth_iterations (default 8)

        Returns:
            New dictionary with forest groves added to passable terrain.
            Does not modify water or mountain cells.
        """
        # Import at runtime to avoid circular import
        from .types import Position

        if grove_count is None:
            grove_count = self._config.forest_grove_count
        if growth_iterations is None:
            growth_iterations = self._config.forest_growth_iterations

        result = grid.copy()

        # Derive water positions from grid if not provided
        if water_positions is None:
            water_positions = {
                pos for pos, t in grid.items()
                if t == TerrainType.WATER
            }

        # Find all passable positions (candidates for forest)
        passable_positions = {
            pos for pos, t in grid.items()
            if t not in (TerrainType.WATER, TerrainType.MOUNTAIN)
        }

        # Find positions adjacent to water (for preferential seeding)
        water_adjacent: set[Position] = set()
        for water_pos in water_positions:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = Position(water_pos.x + dx, water_pos.y + dy)
                if neighbor in passable_positions:
                    water_adjacent.add(neighbor)

        # Find high-moisture passable positions for seeding
        high_moisture = [
            pos for pos, m in moisture_map.items()
            if m > self._config.forest_threshold
            and pos in passable_positions
        ]

        if not high_moisture:
            return result

        # Calculate seed probabilities with water adjacency bonus
        # Seeds near water get higher probability (WI-256)
        seed_candidates: list[tuple[Position, float]] = []
        for pos in high_moisture:
            # Base probability from moisture level
            base_prob = moisture_map.get(pos, 0.5)

            # Bonus for water adjacency (WI-256)
            water_bonus = 0.0
            if pos in water_adjacent:
                water_bonus = self._config.forest_water_adjacency_bonus

            # Region bias influence (WI-256)
            region_bonus = 0.0
            if region_biases is not None and pos in region_biases:
                # Positive forest bias increases probability
                region_bonus = region_biases[pos].get(TerrainType.FOREST, 0.0)

            total_prob = min(1.0, base_prob + water_bonus + region_bonus)
            seed_candidates.append((pos, total_prob))

        # Sort by probability (highest first) and select seeds
        seed_candidates.sort(key=lambda x: x[1], reverse=True)

        # Select N random positions weighted by probability
        self._random.seed(self._seed + 7777)

        # Take top candidates with some randomization
        # Use a pool of top 2x candidates, then select randomly
        candidate_pool_size = min(len(seed_candidates), grove_count * 2)
        candidate_pool = [pos for pos, _ in seed_candidates[:candidate_pool_size]]

        # Select from pool (with weighted preference for higher-ranked candidates)
        seeds: list[Position] = []
        if len(candidate_pool) <= grove_count:
            seeds = candidate_pool
        else:
            # Weighted selection: earlier candidates have higher probability
            weights = [candidate_pool_size - i for i in range(len(candidate_pool))]
            total_weight = sum(weights)
            while len(seeds) < grove_count and len(seeds) < len(candidate_pool):
                # Select candidate based on weight
                r = self._random.uniform(0, total_weight)
                cumulative = 0
                for i, pos in enumerate(candidate_pool):
                    cumulative += weights[i]
                    if r <= cumulative and pos not in seeds:
                        seeds.append(pos)
                        break
                else:
                    # Fallback: pick random candidate
                    remaining = [p for p in candidate_pool if p not in seeds]
                    if remaining:
                        seeds.append(self._random.choice(remaining))

        if not seeds:
            return result

        # Initialize groves: each grove starts as a single seed position
        groves: list[set[Position]] = [{seed} for seed in seeds]

        # Growth iterations with region bias influence
        for iteration in range(growth_iterations):
            new_groves: list[set[Position]] = []
            for grove in groves:
                # Expand each grove by adding passable neighbors
                expansion: set[Position] = set()
                for pos in grove:
                    # Check 4 cardinal neighbors (not diagonal)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        neighbor = Position(pos.x + dx, pos.y + dy)
                        if neighbor not in grid:
                            continue
                        # Don't overwrite water, mountains, or existing forest
                        if result.get(neighbor) in (TerrainType.WATER, TerrainType.MOUNTAIN, TerrainType.FOREST):
                            continue
                        if neighbor not in passable_positions:
                            continue

                        # Check moisture threshold
                        if neighbor in moisture_map:
                            base_threshold = self._config.forest_threshold * 0.5

                            # Region bias influence on growth (WI-256)
                            # Higher forest bias = lower threshold = easier to grow forest
                            if region_biases is not None and neighbor in region_biases:
                                forest_bias = region_biases[neighbor].get(TerrainType.FOREST, 0.0)
                                # Scale bias strength (positive bias lowers threshold)
                                threshold_adjustment = forest_bias * self._config.forest_region_bias_strength
                                effective_threshold = base_threshold - threshold_adjustment
                            else:
                                effective_threshold = base_threshold

                            if moisture_map[neighbor] > effective_threshold:
                                expansion.add(neighbor)
                new_groves.append(grove | expansion)
            groves = new_groves

        # Apply forest to grid
        forest_count = 0
        for grove in groves:
            for pos in grove:
                result[pos] = TerrainType.FOREST
                forest_count += 1

        # Apply forest percentage target if configured (WI-256)
        if self._config.forest_percentage_target is not None and forest_count > 0:
            result = self._apply_forest_percentage_target(
                result, water_positions, passable_positions, forest_count
            )

        return result

    def _apply_forest_percentage_target(
        self,
        grid: dict["Position", TerrainType],
        water_positions: set["Position"],
        passable_positions: set["Position"],
        current_forest_count: int,
    ) -> dict["Position", TerrainType]:
        """Adjust forest coverage to meet target percentage.

        If forest percentage is above target, removes forests starting from
        those furthest from water. If below target, adds forests near water
        and in forest-biased regions.

        WI-256: Forest percentage control for balanced terrain distribution.

        Args:
            grid: Current terrain grid with forests
            water_positions: Set of water positions
            passable_positions: Set of passable positions
            current_forest_count: Number of forest cells currently

        Returns:
            Grid with adjusted forest coverage
        """
        from .types import Position

        # Count total passable cells
        total_passable = len(passable_positions)
        if total_passable == 0:
            return grid

        target_percentage = self._config.forest_percentage_target
        if target_percentage is None:
            return grid

        target_count = int(total_passable * target_percentage)

        result = grid.copy()

        if current_forest_count > target_count:
            # Need to remove excess forests
            # Remove forests furthest from water first (WI-256: keep forests near water)
            forest_positions = [
                pos for pos, t in grid.items()
                if t == TerrainType.FOREST
            ]

            # Calculate distance to nearest water for each forest
            def water_distance(pos: Position) -> float:
                """Calculate minimum Chebyshev distance to any water position."""
                if not water_positions:
                    return float('inf')
                return min(
                    max(abs(pos.x - wp.x), abs(pos.y - wp.y))
                    for wp in water_positions
                )

            # Sort by distance (furthest first)
            forest_positions.sort(key=water_distance, reverse=True)

            # Remove excess forests
            to_remove = len(forest_positions) - target_count
            for pos in forest_positions[:to_remove]:
                if pos in result:
                    result[pos] = TerrainType.PLAIN  # Revert to plain

        elif current_forest_count < target_count:
            # Need to add more forests
            # Add forests near water first (WI-256: forests near water)
            non_forest_passable = [
                pos for pos in passable_positions
                if grid.get(pos) not in (TerrainType.FOREST, TerrainType.WATER, TerrainType.MOUNTAIN)
            ]

            # Sort by distance to water (nearest first)
            def water_distance(pos: Position) -> float:
                if not water_positions:
                    return 0.0
                return min(
                    max(abs(pos.x - wp.x), abs(pos.y - wp.y))
                    for wp in water_positions
                )

            non_forest_passable.sort(key=water_distance)

            # Add forests
            to_add = target_count - current_forest_count
            for pos in non_forest_passable[:to_add]:
                result[pos] = TerrainType.FOREST

        return result

    def generate_ridges_from_heightmap(
        self,
        heightmap: dict["Position", float],
    ) -> list[list["Position"]]:
        """Generate ridge chains connecting high-elevation points.

        Identifies peaks in the heightmap and generates ridge chains connecting
        them using midpoint displacement for natural-looking mountain ranges.

        Args:
            heightmap: Dictionary mapping positions to elevation values.

        Returns:
            List of ridge chains, where each chain is a list of Position objects.
        """
        pairs = self._generate_ridge_seeds(heightmap)
        ridges: list[list["Position"]] = []

        for start, end in pairs:
            ridge = self.generate_ridge_chain(start, end)
            ridges.append(ridge)

        return ridges

    def _find_river_sources(
        self,
        heightmap: dict["Position", float],
        grid: dict["Position", TerrainType],
        count: int,
    ) -> list["Position"]:
        """Find suitable river source positions at high elevation.

        River sources should be:
        - At high elevation (near mountains)
        - In passable terrain (not already water or mountain)
        - Not too close to each other

        Args:
            heightmap: Dictionary mapping positions to elevation values
            grid: Dictionary mapping positions to terrain types
            count: Number of sources to find

        Returns:
            List of Position objects suitable as river sources
        """
        from .types import Position

        # Find positions that could be river sources
        # Must be passable terrain and above a certain elevation
        candidate_positions: list[tuple[Position, float]] = []

        for pos, elevation in heightmap.items():
            # Skip if not in grid or already water/mountain
            if pos not in grid:
                continue
            if grid[pos] in (TerrainType.WATER, TerrainType.MOUNTAIN):
                continue
            # Prefer higher elevation for river sources
            # Use threshold above which streams would naturally form
            if elevation > self._config.water_threshold + 0.3:
                candidate_positions.append((pos, elevation))

        if not candidate_positions:
            return []

        # Sort by elevation (highest first)
        candidate_positions.sort(key=lambda x: x[1], reverse=True)

        # Select sources spaced apart from each other
        sources: list[Position] = []
        min_distance = max(10, self._config.world_size // 20)  # Minimum distance between sources

        for pos, _ in candidate_positions:
            # Check distance from existing sources
            too_close = False
            for existing in sources:
                dx = abs(pos.x - existing.x)
                dy = abs(pos.y - existing.y)
                if dx < min_distance and dy < min_distance:
                    too_close = True
                    break

            if not too_close:
                sources.append(pos)
                if len(sources) >= count:
                    break

        return sources

    def _trace_river_downhill(
        self,
        start: "Position",
        heightmap: dict["Position", float],
        grid: dict["Position", TerrainType],
        existing_water: set["Position"],
    ) -> list["Position"]:
        """Trace a river path from source downhill to water or boundary.

        Rivers follow the steepest descent path until they reach:
        - Existing water (lake or another river)
        - The boundary of the heightmap
        - A local minimum (basin)

        Args:
            start: Starting position for the river
            heightmap: Dictionary mapping positions to elevation values
            grid: Dictionary mapping positions to terrain types
            existing_water: Set of positions already marked as water

        Returns:
            List of Position objects forming the river path
        """
        from .types import Position

        path: list[Position] = [start]
        visited: set[Position] = {start}
        current = start

        # Maximum river length to prevent infinite loops
        max_length = len(heightmap) // 2

        while len(path) < max_length:
            # Get 4-connected neighbors
            neighbors = [
                Position(current.x + dx, current.y + dy)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
            ]

            # Filter to valid positions
            valid_neighbors = [n for n in neighbors if n in heightmap]

            if not valid_neighbors:
                break

            # Check if any neighbor is existing water (river flows into lake/river)
            for n in valid_neighbors:
                if n in existing_water:
                    return path

            # Find the lowest neighbor (steepest descent)
            lowest = min(valid_neighbors, key=lambda n: heightmap.get(n, 0.0))

            # Check if we've reached a local minimum
            if heightmap.get(lowest, 0.0) >= heightmap.get(current, 0.0):
                # At a local minimum - river ends here (forms a small pond)
                break

            # Avoid cycles
            if lowest in visited:
                break

            visited.add(lowest)
            path.append(lowest)
            current = lowest

        return path

    def generate_rivers(
        self,
        heightmap: dict["Position", float],
        grid: dict["Position", TerrainType],
        count: int | None = None,
    ) -> list[list["Position"]]:
        """Generate rivers flowing from high to low elevation.

        Creates rivers that follow elevation gradients, starting from
        high-elevation sources and flowing downhill until they reach
        water or the map boundary.

        Args:
            heightmap: Dictionary mapping positions to elevation values
            grid: Dictionary mapping positions to terrain types
            count: Number of rivers to generate. If None, uses config's
                  river_count or auto-calculates from world_size.

        Returns:
            List of river paths, where each path is a list of Position objects.
        """
        from .types import Position

        if count is None:
            count = self._config.river_count
            if count is None:
                # Auto-calculate: roughly one river per 80 cells of world size
                count = max(1, self._config.world_size // 80)

        if count <= 0:
            return []

        # Find river sources at high elevation
        sources = self._find_river_sources(heightmap, grid, count)

        if not sources:
            return []

        # Trace each river downhill
        rivers: list[list[Position]] = []
        existing_water: set[Position] = set()

        # Include existing water from grid
        for pos, terrain in grid.items():
            if terrain == TerrainType.WATER:
                existing_water.add(pos)

        # Seed random for determinism in path selection
        self._random.seed(self._seed + 8888)

        for source in sources:
            path = self._trace_river_downhill(source, heightmap, grid, existing_water)

            # Only add rivers that have some length
            if len(path) >= 3:
                rivers.append(path)
                # Add river positions to existing_water so later rivers can connect
                for pos in path:
                    existing_water.add(pos)

        return rivers

    def _find_pond_sites(
        self,
        heightmap: dict["Position", float],
        grid: dict["Position", TerrainType],
        count: int,
        existing_water: set["Position"],
    ) -> list["Position"]:
        """Find suitable pond sites in lowland areas.

        Ponds should be placed:
        - In passable terrain (not already water or mountain)
        - At low elevation (natural basins)
        - Away from existing water features

        Args:
            heightmap: Dictionary mapping positions to elevation values
            grid: Dictionary mapping positions to terrain types
            count: Number of sites to find
            existing_water: Set of positions already marked as water

        Returns:
            List of Position objects suitable as pond centers
        """
        from .types import Position

        # Find positions that could be pond sites
        candidate_positions: list[tuple[Position, float]] = []

        for pos, elevation in heightmap.items():
            # Skip if not in grid or already water/mountain
            if pos not in grid:
                continue
            if grid[pos] in (TerrainType.WATER, TerrainType.MOUNTAIN):
                continue
            # Prefer lower elevation for ponds (natural basins)
            if elevation < self._config.water_threshold + 0.1:
                candidate_positions.append((pos, elevation))

        if not candidate_positions:
            return []

        # Sort by elevation (lowest first)
        candidate_positions.sort(key=lambda x: x[1])

        # Select sites spaced apart from existing water and each other
        sites: list[Position] = []
        min_distance = max(8, self._config.world_size // 30)  # Minimum distance

        for pos, _ in candidate_positions:
            # Check distance from existing water and other sites
            too_close = False

            for water_pos in existing_water:
                dx = abs(pos.x - water_pos.x)
                dy = abs(pos.y - water_pos.y)
                if dx < min_distance and dy < min_distance:
                    too_close = True
                    break

            if not too_close:
                for existing_site in sites:
                    dx = abs(pos.x - existing_site.x)
                    dy = abs(pos.y - existing_site.y)
                    if dx < min_distance and dy < min_distance:
                        too_close = True
                        break

            if not too_close:
                sites.append(pos)
                if len(sites) >= count:
                    break

        return sites

    def generate_ponds(
        self,
        heightmap: dict["Position", float],
        grid: dict["Position", TerrainType],
        existing_water: set["Position"],
        count: int | None = None,
    ) -> list[set["Position"]]:
        """Generate small isolated water bodies (ponds).

        Creates ponds in lowland areas with random size variation within
        the configured size range. Ponds are placed away from existing
        water features to ensure they remain isolated.

        Args:
            heightmap: Dictionary mapping positions to elevation values
            grid: Dictionary mapping positions to terrain types
            existing_water: Set of positions already marked as water
            count: Number of ponds to generate. If None, uses config's
                  pond_count or auto-calculates from world_size.

        Returns:
            List of pond position sets, each containing all cells in a pond.
        """
        from .types import Position

        if count is None:
            count = self._config.pond_count
            if count is None:
                # Auto-calculate: roughly one pond per 25 cells of world size
                count = max(1, self._config.world_size // 25)

        if count <= 0:
            return []

        # Find pond sites in lowland areas
        sites = self._find_pond_sites(heightmap, grid, count, existing_water)

        if not sites:
            return []

        ponds: list[set[Position]] = []

        # Seed random for determinism in pond size
        self._random.seed(self._seed + 9999)

        for site in sites:
            # Random pond size within configured range
            size = self._random.randint(
                self._config.min_pond_size,
                self._config.max_pond_size
            )

            # Grow pond from center using flood-fill-like expansion
            pond: set[Position] = {site}
            frontier: list[Position] = [site]

            while len(pond) < size and frontier:
                current = frontier.pop(0)

                # Check 4-connected neighbors
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    neighbor = Position(current.x + dx, current.y + dy)

                    if neighbor in pond:
                        continue
                    if neighbor not in grid:
                        continue
                    # Don't expand into mountains
                    if grid[neighbor] == TerrainType.MOUNTAIN:
                        continue
                    # Don't merge with existing water
                    if neighbor in existing_water:
                        continue

                    pond.add(neighbor)
                    frontier.append(neighbor)

                    if len(pond) >= size:
                        break

            if len(pond) >= self._config.min_pond_size:
                ponds.append(pond)

        return ponds

    def _enforce_water_percentage(
        self,
        grid: dict["Position", TerrainType],
        water_positions: set["Position"],
        target_percentage: float,
    ) -> dict["Position", TerrainType]:
        """Enforce a target water percentage by adding or removing water.

        Args:
            grid: Current terrain grid
            water_positions: Set of current water positions
            target_percentage: Target water percentage (0.0 to 1.0)

        Returns:
            Modified terrain grid with adjusted water content
        """
        from .types import Position

        if not grid:
            return grid

        total_cells = len(grid)
        target_water = int(total_cells * target_percentage)
        current_water = len(water_positions)

        result = grid.copy()
        updated_water = set(water_positions)

        if current_water > target_water:
            # Remove excess water: convert to meadow or plain
            # Prefer removing isolated water cells (fewer neighbors)
            excess_count = current_water - target_water

            # Score water cells by isolation (fewer water neighbors = more isolated)
            def water_neighbors(pos: "Position") -> int:
                count = 0
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    neighbor = Position(pos.x + dx, pos.y + dy)
                    if neighbor in updated_water:
                        count += 1
                return count

            # Sort water by isolation (lowest neighbors first)
            water_list = list(updated_water)
            water_list.sort(key=water_neighbors)

            # Convert most isolated water cells to meadow/plain
            removed = 0
            for pos in water_list:
                if removed >= excess_count:
                    break
                # Convert to meadow or plain based on random choice
                result[pos] = TerrainType.MEADOW if self._random.random() < 0.5 else TerrainType.PLAIN
                updated_water.discard(pos)
                removed += 1

        elif current_water < target_water:
            # Add more water: convert passable terrain near existing water
            needed = target_water - current_water

            # Start with candidates adjacent to existing water
            frontier: set["Position"] = set()
            for pos in updated_water:
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    neighbor = Position(pos.x + dx, pos.y + dy)
                    if neighbor in result and result[neighbor].passable:
                        frontier.add(neighbor)

            # Convert passable cells to water, expanding outward
            added = 0
            while added < needed and frontier:
                # Pick a random candidate from frontier
                candidates = list(frontier)
                self._random.shuffle(candidates)

                for pos in candidates:
                    if added >= needed:
                        break
                    if result[pos] == TerrainType.WATER:
                        frontier.discard(pos)
                        continue
                    result[pos] = TerrainType.WATER
                    updated_water.add(pos)
                    added += 1

                    # Add neighbors to frontier
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        neighbor = Position(pos.x + dx, pos.y + dy)
                        if neighbor in result and result[neighbor].passable:
                            frontier.add(neighbor)

                # If we've exhausted frontier but still need more, fill randomly
                if added < needed and not frontier:
                    passable = [p for p, t in result.items()
                                if t.passable and t != TerrainType.WATER]
                    self._random.shuffle(passable)
                    for pos in passable:
                        if added >= needed:
                            break
                        result[pos] = TerrainType.WATER
                        updated_water.add(pos)
                        added += 1
                    break

        return result


def smooth_terrain(
    grid: dict["Position", TerrainType],
    passes: int = 2
) -> dict["Position", TerrainType]:
    """Apply cellular automata smoothing to create connected regions.

    Args:
        grid: Dictionary mapping positions to terrain types
        passes: Number of smoothing iterations (default 2)

    Returns:
        New dictionary with smoothed terrain assignments
    """
    # Import at runtime to avoid circular import
    from .types import Position

    if passes <= 0:
        return grid.copy()

    result = grid.copy()

    for _ in range(passes):
        new_grid: dict[Position, TerrainType] = {}
        for pos, terrain in result.items():
            neighbors = _count_neighbors(result, pos)
            new_grid[pos] = _apply_smoothing_rule(terrain, neighbors)
        result = new_grid

    return result


def _count_neighbors(
    grid: dict["Position", TerrainType],
    pos: "Position"
) -> dict[TerrainType, int]:
    """Count terrain types in 8-neighbor Moore neighborhood.

    Args:
        grid: Dictionary mapping positions to terrain types
        pos: Center position to count neighbors around

    Returns:
        Dictionary mapping terrain types to neighbor counts
    """
    # Import at runtime to avoid circular import
    from .types import Position

    counts: dict[TerrainType, int] = defaultdict(int)
    for dy in [-1, 0, 1]:
        for dx in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            neighbor = Position(pos.x + dx, pos.y + dy)
            if neighbor in grid:
                counts[grid[neighbor]] += 1
    return dict(counts)


def _apply_smoothing_rule(
    terrain: TerrainType,
    neighbor_counts: dict[TerrainType, int]
) -> TerrainType:
    """Apply CA rules for coherent terrain regions and gradual biome transitions.

    Rules:
    WATER:
    - Isolated water (< 3 water neighbors) becomes meadow
    - Connected water (3+ water neighbors) stays water

    MOUNTAIN:
    - Connected mountains (2+ mountain neighbors) stay mountain
    - Isolated mountains become plain
    - Passable terrain adjacent to mountains (3+ mountain neighbors) becomes mountain

    FOREST:
    - Connected forests (2+ forest neighbors) stay forest
    - Isolated forests (< 2 forest neighbors) become meadow
    - Passable terrain (plain/meadow) with 5+ forest neighbors becomes forest

    MEADOW/PLAIN transitions:
    - Plains with 5+ meadow neighbors become meadow (meadow expansion)
    - Meadows with 5+ plain neighbors become plain (plain expansion)
    - Creates gradual boundaries between grassland types

    WATER expansion:
    - Land with 4+ water neighbors becomes water

    Args:
        terrain: Current terrain type at this position
        neighbor_counts: Counts of each terrain type in the neighborhood

    Returns:
        New terrain type after applying smoothing rule
    """
    water_neighbors = neighbor_counts.get(TerrainType.WATER, 0)
    mountain_neighbors = neighbor_counts.get(TerrainType.MOUNTAIN, 0)
    forest_neighbors = neighbor_counts.get(TerrainType.FOREST, 0)
    meadow_neighbors = neighbor_counts.get(TerrainType.MEADOW, 0)
    plain_neighbors = neighbor_counts.get(TerrainType.PLAIN, 0)

    if terrain == TerrainType.WATER:
        # Isolated water (few water neighbors) becomes meadow
        if water_neighbors < 3:
            return TerrainType.MEADOW
        return TerrainType.WATER

    if terrain == TerrainType.MOUNTAIN:
        # Mountains persist if connected, otherwise become plain
        if mountain_neighbors >= 2:
            return TerrainType.MOUNTAIN
        return TerrainType.PLAIN

    if terrain == TerrainType.FOREST:
        # Forests persist if connected (2+ forest neighbors), otherwise meadow
        if forest_neighbors >= 2:
            return TerrainType.FOREST
        return TerrainType.MEADOW

    # Land can become water if surrounded
    if water_neighbors >= 4:
        return TerrainType.WATER

    # Passable terrain transitions
    if terrain in (TerrainType.PLAIN, TerrainType.MEADOW):
        # Mountain foothills: passable terrain near mountains
        if mountain_neighbors >= 3:
            return TerrainType.MOUNTAIN

        # Forest expansion into passable terrain
        if forest_neighbors >= 5:
            return TerrainType.FOREST

        # Meadow-plain gradual transitions
        # Plains become meadow if surrounded by meadows
        if terrain == TerrainType.PLAIN and meadow_neighbors >= 5:
            return TerrainType.MEADOW

        # Meadows become plain if surrounded by plains
        if terrain == TerrainType.MEADOW and plain_neighbors >= 5:
            return TerrainType.PLAIN

    return terrain


def detect_lakes(
    grid: dict["Position", TerrainType],
    min_size: int = 5
) -> list[tuple[set["Position"], int]]:
    """Find all connected water regions using flood-fill.

    Identifies connected components of water cells using 4-connected
    neighborhood (north, south, east, west - not diagonals).

    Args:
        grid: Dictionary mapping positions to terrain types
        min_size: Minimum size for a water body to be considered a lake.
            Smaller water bodies are excluded from results.

    Returns:
        List of (positions, size) tuples for each lake, sorted by size
        descending (largest first).
    """
    from .types import Position

    visited: set[Position] = set()
    lakes: list[tuple[set[Position], int]] = []

    for pos, terrain in grid.items():
        if pos in visited:
            continue
        if terrain != TerrainType.WATER:
            continue

        # Flood-fill from this water cell
        lake = _flood_fill_water(grid, pos)
        visited.update(lake)

        if len(lake) >= min_size:
            lakes.append((lake, len(lake)))

    # Sort by size descending
    lakes.sort(key=lambda x: x[1], reverse=True)
    return lakes


def _flood_fill_water(
    grid: dict["Position", TerrainType],
    start: "Position"
) -> set["Position"]:
    """Flood-fill from start position to find connected water cells.

    Uses 4-connected neighborhood (cardinal directions only).

    Args:
        grid: Dictionary mapping positions to terrain types
        start: Starting position for flood-fill

    Returns:
        Set of all connected water positions
    """
    from .types import Position

    lake: set[Position] = set()
    stack: list[Position] = [start]

    while stack:
        pos = stack.pop()
        if pos in lake:
            continue
        if pos not in grid or grid[pos] != TerrainType.WATER:
            continue

        lake.add(pos)
        # Add 4-connected neighbors (north, south, east, west)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            stack.append(Position(pos.x + dx, pos.y + dy))

    return lake


def expand_lake(
    grid: dict["Position", TerrainType],
    lake_positions: set["Position"],
    target_size: int
) -> set["Position"]:
    """Expand a small lake to target size by growing from center.

    Expansion uses nearest-neighbor growth from the lake center, avoiding
    mountains to preserve mountain/water adjacency boundaries.

    Args:
        grid: Dictionary mapping positions to terrain types
        lake_positions: Current set of water positions forming the lake
        target_size: Target number of cells for the expanded lake

    Returns:
        Set of positions for the expanded lake. If lake already meets or
        exceeds target_size, returns the original lake_positions unchanged.
    """
    from .types import Position

    if len(lake_positions) >= target_size:
        return lake_positions

    # Find center of lake
    center_x = sum(p.x for p in lake_positions) // len(lake_positions)
    center_y = sum(p.y for p in lake_positions) // len(lake_positions)
    center = Position(center_x, center_y)

    expanded: set[Position] = set(lake_positions)
    frontier: list[Position] = [center]

    while len(expanded) < target_size and frontier:
        pos = frontier.pop(0)

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = Position(pos.x + dx, pos.y + dy)

            if neighbor in expanded:
                continue
            if neighbor not in grid:
                continue
            # Don't expand into mountains
            if grid[neighbor] == TerrainType.MOUNTAIN:
                continue

            expanded.add(neighbor)
            frontier.append(neighbor)

            if len(expanded) >= target_size:
                break

    return expanded


class TerrainGrid:
    """In-memory terrain storage with on-demand generation."""

    def __init__(
        self,
        generator: TerrainGenerator,
        smoothing_passes: int | None = None
    ) -> None:
        """Initialize with a terrain generator for on-demand generation.

        Args:
            generator: TerrainGenerator instance for terrain generation
            smoothing_passes: Number of CA smoothing passes. If None, uses
                generator's config.smoothing_passes (default 2)
        """
        self._generator = generator
        if smoothing_passes is None:
            # Use config's smoothing_passes if available
            self._smoothing_passes = generator._config.smoothing_passes
        else:
            self._smoothing_passes = smoothing_passes
        self._cache: dict[Position, TerrainType] = {}

    @property
    def seed(self) -> int:
        """Return the generator's seed."""
        return self._generator.seed

    def get_terrain(self, position: "Position") -> TerrainType:
        """Return terrain type at position.

        Returns cached terrain if available, otherwise generates and caches.
        Note: Single position lookup uses raw terrain without smoothing.
        For smoothed terrain, use get_terrain_in_bounds() on a bounds containing
        the position.
        """
        if position not in self._cache:
            self._cache[position] = self._generator.generate_terrain(position)
        return self._cache[position]

    def get_terrain_in_bounds(self, bounds: "Bounds") -> dict["Position", TerrainType]:
        """Return terrain for all positions within bounds.

        Generates terrain through the full pipeline:
        1. Generate heightmap and moisture map (fBm with domain warping)
        2. Generate biome region biases (WI-254)
        3. Generate ridges from heightmap peaks
        4. Classify terrain with region bias influence
        5. Apply CA smoothing
        6. Detect and expand lakes
        7. Generate rivers following elevation gradients (WI-255)
        8. Generate ponds in lowland areas (WI-255)
        9. Apply forest grove generation

        When noise library is unavailable, falls back to basic generation
        with smoothing only (no ridges, lakes, rivers, ponds, or forest clustering).

        Results are cached and returned.
        """
        # Import at runtime to avoid circular import
        from .types import Bounds, Position

        # Check if noise library is available for full pipeline
        if HAS_NOISE:
            # Step 1: Generate heightmap and moisture map
            heightmap, moisture_map = self._generator.generate_heightmap_and_moisture(bounds)

            # Step 2: Generate biome region biases for each position
            region_biases: dict[Position, dict[TerrainType, float]] = {}
            for pos in heightmap:
                region_biases[pos] = self._generator._get_region_bias(pos)

            # Step 3: Generate ridges from heightmap
            ridges = self._generator.generate_ridges_from_heightmap(heightmap)

            # Step 4: Classify terrain with region bias influence
            terrain: dict[Position, TerrainType] = {}
            for pos in heightmap:
                elevation = heightmap[pos]
                moisture = moisture_map[pos]
                terrain[pos] = self._generator._apply_region_bias(
                    elevation, moisture, region_biases[pos]
                )

            # Step 5: Mark ridge positions as MOUNTAIN
            for ridge in ridges:
                for pos in ridge:
                    # Only mark positions within bounds; ridges extending outside
                    # bounds are truncated at the boundary
                    if pos in terrain:
                        terrain[pos] = TerrainType.MOUNTAIN

            # Step 6: Apply CA smoothing
            smoothed = smooth_terrain(terrain, passes=self._smoothing_passes)

            # Step 7: Process lakes - detect and expand small water bodies
            # Get ALL water bodies (min_size=1) so we can expand small ones
            lakes = detect_lakes(smoothed, min_size=1)
            for lake_positions, size in lakes:
                if size < self._generator._config.min_lake_size:
                    # Expand small water bodies
                    target_size = int(
                        self._generator._config.min_lake_size
                        * self._generator._config.lake_expansion_factor
                    )
                    expanded = expand_lake(smoothed, lake_positions, target_size)
                    for pos in expanded:
                        smoothed[pos] = TerrainType.WATER

            # Step 8: Generate rivers following elevation gradients (WI-255)
            # Collect existing water positions for river tracing
            existing_water: set[Position] = {
                pos for pos, t in smoothed.items() if t == TerrainType.WATER
            }

            rivers = self._generator.generate_rivers(
                heightmap, smoothed,
                count=self._generator._config.river_count
            )
            for river_path in rivers:
                for pos in river_path:
                    if pos in smoothed:
                        smoothed[pos] = TerrainType.WATER
                        existing_water.add(pos)

            # Step 9: Generate ponds in lowland areas (WI-255)
            ponds = self._generator.generate_ponds(
                heightmap, smoothed, existing_water,
                count=self._generator._config.pond_count
            )
            for pond_positions in ponds:
                for pos in pond_positions:
                    if pos in smoothed:
                        smoothed[pos] = TerrainType.WATER
                        existing_water.add(pos)

            # Step 10: Enforce water percentage target (WI-255)
            if self._generator._config.water_percentage_target is not None:
                smoothed = self._generator._enforce_water_percentage(
                    smoothed, existing_water, self._generator._config.water_percentage_target
                )

            # Step 11: Apply forest grove generation (WI-256: with water adjacency and region bias)
            if self._generator._config.forest_grove_count > 0:
                smoothed = self._generator.generate_forest_groves(
                    smoothed,
                    moisture_map,
                    water_positions=existing_water,
                    region_biases=region_biases,
                    grove_count=self._generator._config.forest_grove_count,
                    growth_iterations=self._generator._config.forest_growth_iterations,
                )

            # Cache and return results
            for pos, t in smoothed.items():
                self._cache[pos] = t

            return smoothed
        else:
            # Fallback: basic generation with smoothing only
            raw_terrain: dict[Position, TerrainType] = {}
            for pos, terrain in self._generator.generate_chunk(bounds):
                raw_terrain[pos] = terrain

            # Apply smoothing
            smoothed = smooth_terrain(raw_terrain, passes=self._smoothing_passes)

            # Cache and return smoothed results
            for pos, terrain in smoothed.items():
                self._cache[pos] = terrain

            return smoothed

    def is_passable(self, position: "Position") -> bool:
        """Check if position is passable for agents and structures."""
        return self.get_terrain(position).passable

    def clear_cache(self) -> None:
        """Clear all cached terrain. Used when seed changes."""
        self._cache.clear()


def generate_water_features(
    heightmap: dict["Position", float],
    grid: dict["Position", TerrainType],
    config: TerrainConfig,
    seed: int,
) -> tuple[list[list["Position"]], list[set["Position"]]]:
    """Generate rivers and ponds from heightmap data.

    This is a convenience function that wraps the TerrainGenerator methods
    for generating water features. It creates a temporary generator with
    the given config and seed.

    Args:
        heightmap: Dictionary mapping positions to elevation values
        grid: Dictionary mapping positions to terrain types
        config: TerrainConfig with water feature parameters
        seed: Random seed for deterministic generation

    Returns:
        Tuple of (rivers, ponds) where:
        - rivers: List of river paths (each path is a list of Position objects)
        - ponds: List of pond position sets (each set contains all cells in a pond)
    """
    generator = TerrainGenerator(config)
    generator._seed = seed
    generator._random = random.Random(seed)

    # Generate existing water set from grid
    existing_water: set[Position] = {
        pos for pos, terrain in grid.items() if terrain == TerrainType.WATER
    }

    # Generate rivers
    rivers = generator.generate_rivers(
        heightmap, grid,
        count=config.river_count
    )

    # Generate ponds
    ponds = generator.generate_ponds(
        heightmap, grid, existing_water,
        count=config.pond_count
    )

    return rivers, ponds


__all__ = [
    "TerrainType",
    "TerrainConfig",
    "TerrainGenerator",
    "TerrainGrid",
    "smooth_terrain",
    "detect_lakes",
    "expand_lake",
    "_count_neighbors",
    "_apply_smoothing_rule",
    "_flood_fill_water",
    # WI-255: Water feature generation
    "generate_water_features",
]