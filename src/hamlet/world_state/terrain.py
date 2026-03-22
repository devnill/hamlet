"""Terrain types and configuration for world generation."""
from __future__ import annotations

import random
from collections import defaultdict
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

    def generate_forest_groves(
        self,
        grid: dict["Position", TerrainType],
        moisture_map: dict["Position", float],
        grove_count: int | None = None,
        growth_iterations: int | None = None,
    ) -> dict["Position", TerrainType]:
        """Create forest groves from seeds in high-moisture areas.

        This method applies a seeding and growth algorithm to create natural
        forest clusters. Seeds are placed in high-moisture passable positions,
        then iteratively expand to neighboring cells with moderate moisture.

        Args:
            grid: Dictionary mapping positions to terrain types (after smoothing
                  and any ridge/lake processing)
            moisture_map: Dictionary mapping positions to moisture values
            grove_count: Number of forest grove seeds to plant. If None, uses
                        config's forest_grove_count (default 10)
            growth_iterations: Number of growth iterations per grove. If None,
                              uses config's forest_growth_iterations (default 5)

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

        # Find high-moisture passable positions for seeding
        high_moisture = [
            pos for pos, m in moisture_map.items()
            if m > self._config.forest_threshold
            and pos in grid
            and grid[pos] not in (TerrainType.WATER, TerrainType.MOUNTAIN)
        ]

        if not high_moisture:
            return result

        # Select N random seed positions using seeded random for determinism
        self._random.seed(self._seed + 7777)
        seeds = self._random.sample(high_moisture, min(grove_count, len(high_moisture)))

        # Initialize groves: each grove starts as a single seed position
        groves: list[set[Position]] = [{seed} for seed in seeds]

        # Growth iterations
        for _ in range(growth_iterations):
            new_groves: list[set[Position]] = []
            for grove in groves:
                # Expand each grove by adding passable neighbors
                expansion: set[Position] = set()
                for pos in grove:
                    # Check 4 cardinal neighbors (not diagonal)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        neighbor = Position(pos.x + dx, pos.y + dy)
                        if neighbor in grid:
                            # Don't overwrite water, mountains, or existing forest
                            if grid[neighbor] in (TerrainType.WATER, TerrainType.MOUNTAIN):
                                continue
                            # Only expand if moisture is reasonable for forest
                            if neighbor in moisture_map:
                                if moisture_map[neighbor] > self._config.forest_threshold * 0.5:
                                    expansion.add(neighbor)
                new_groves.append(grove | expansion)
            groves = new_groves

        # Apply forest to grid
        for grove in groves:
            for pos in grove:
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
    """Apply CA rules for coherent terrain regions.

    Rules:
    - Isolated water (fewer than 3 water neighbors) becomes meadow
    - Land surrounded by water (4+ water neighbors) becomes water
    - Mountains persist if connected (2+ mountain neighbors), else become plain
    - Forests expand into passable terrain with 5+ forest neighbors
    - Isolated forest (fewer than 2 forest neighbors) becomes meadow
    - Passable terrain (plain/meadow) with 4+ forest neighbors becomes forest

    Args:
        terrain: Current terrain type at this position
        neighbor_counts: Counts of each terrain type in the neighborhood

    Returns:
        New terrain type after applying smoothing rule
    """
    water_neighbors = neighbor_counts.get(TerrainType.WATER, 0)
    mountain_neighbors = neighbor_counts.get(TerrainType.MOUNTAIN, 0)
    forest_neighbors = neighbor_counts.get(TerrainType.FOREST, 0)

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

    # Passable terrain (plain/meadow) can become forest if surrounded by forest
    if terrain in (TerrainType.PLAIN, TerrainType.MEADOW):
        if forest_neighbors >= 5:
            return TerrainType.FOREST

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
        2. Generate ridges from heightmap peaks
        3. Classify terrain from elevation/moisture thresholds
        4. Apply CA smoothing
        5. Detect and expand lakes
        6. Generate forest groves

        When noise library is unavailable, falls back to basic generation
        with smoothing only (no ridges, lakes, or forest clustering).

        Results are cached and returned.
        """
        # Import at runtime to avoid circular import
        from .types import Bounds, Position

        # Check if noise library is available for full pipeline
        if HAS_NOISE:
            # Step 1: Generate heightmap and moisture map
            heightmap, moisture_map = self._generator.generate_heightmap_and_moisture(bounds)

            # Step 2: Generate ridges from heightmap
            ridges = self._generator.generate_ridges_from_heightmap(heightmap)

            # Step 3: Classify terrain
            terrain: dict[Position, TerrainType] = {}
            for pos in heightmap:
                elevation = heightmap[pos]
                moisture = moisture_map[pos]
                terrain[pos] = self._generator._classify_terrain(elevation, moisture)

            # Step 4: Mark ridge positions as MOUNTAIN
            for ridge in ridges:
                for pos in ridge:
                    # Only mark positions within bounds; ridges extending outside
                    # bounds are truncated at the boundary
                    if pos in terrain:
                        terrain[pos] = TerrainType.MOUNTAIN

            # Step 5: Apply CA smoothing
            smoothed = smooth_terrain(terrain, passes=self._smoothing_passes)

            # Step 6: Process lakes - detect and expand small water bodies
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

            # Step 7: Apply forest grove generation
            if self._generator._config.forest_grove_count > 0:
                smoothed = self._generator.generate_forest_groves(
                    smoothed,
                    moisture_map,
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
]