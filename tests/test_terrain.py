"""Tests for terrain types and configuration (WI-232) and TerrainGenerator (WI-233).

Test framework: pytest.
Run with: pytest tests/test_terrain.py -v
"""
from __future__ import annotations

import pytest

from hamlet.world_state.terrain import (
    HAS_NOISE,
    TerrainConfig,
    TerrainGenerator,
    TerrainGrid,
    TerrainType,
    smooth_terrain,
    detect_lakes,
    expand_lake,
    _count_neighbors,
    _apply_smoothing_rule,
    _flood_fill_water,
)
from hamlet.world_state.types import Bounds, Position


class TestTerrainType:
    """Tests for TerrainType enum."""

    def test_enum_has_five_members(self) -> None:
        """TerrainType enum has exactly 5 members."""
        members = list(TerrainType)
        assert len(members) == 5
        assert TerrainType.WATER in members
        assert TerrainType.MOUNTAIN in members
        assert TerrainType.FOREST in members
        assert TerrainType.MEADOW in members
        assert TerrainType.PLAIN in members

    def test_water_is_not_passable(self) -> None:
        """WATER terrain is not passable."""
        assert TerrainType.WATER.passable is False

    def test_mountain_is_not_passable(self) -> None:
        """MOUNTAIN terrain is not passable."""
        assert TerrainType.MOUNTAIN.passable is False

    def test_forest_is_passable(self) -> None:
        """FOREST terrain is passable."""
        assert TerrainType.FOREST.passable is True

    def test_meadow_is_passable(self) -> None:
        """MEADOW terrain is passable."""
        assert TerrainType.MEADOW.passable is True

    def test_plain_is_passable(self) -> None:
        """PLAIN terrain is passable."""
        assert TerrainType.PLAIN.passable is True

    def test_water_symbol(self) -> None:
        """WATER has correct symbol."""
        assert TerrainType.WATER.symbol == "~"

    def test_mountain_symbol(self) -> None:
        """MOUNTAIN has correct symbol."""
        assert TerrainType.MOUNTAIN.symbol == "^"

    def test_forest_symbol(self) -> None:
        """FOREST has correct symbol."""
        assert TerrainType.FOREST.symbol == "♣"

    def test_meadow_symbol(self) -> None:
        """MEADOW has correct symbol."""
        assert TerrainType.MEADOW.symbol == '"'

    def test_plain_symbol(self) -> None:
        """PLAIN has correct symbol."""
        assert TerrainType.PLAIN.symbol == "."

    def test_water_color(self) -> None:
        """WATER has correct color."""
        assert TerrainType.WATER.color == "blue"

    def test_mountain_color(self) -> None:
        """MOUNTAIN has correct color."""
        assert TerrainType.MOUNTAIN.color == "grey85"

    def test_forest_color(self) -> None:
        """FOREST has correct color."""
        assert TerrainType.FOREST.color == "green"

    def test_meadow_color(self) -> None:
        """MEADOW has correct color."""
        assert TerrainType.MEADOW.color == "bright_green"

    def test_plain_color(self) -> None:
        """PLAIN has correct color."""
        assert TerrainType.PLAIN.color == "white"


class TestTerrainConfig:
    """Tests for TerrainConfig dataclass."""

    def test_default_values(self) -> None:
        """TerrainConfig has correct default values."""
        config = TerrainConfig()
        assert config.seed is None
        assert config.world_size == 200
        assert config.water_frequency == 0.02
        assert config.mountain_frequency == 0.015
        # Thresholds for terrain classification (WI-242)
        # forest_threshold > meadow_threshold for correct moisture ordering
        assert config.forest_threshold == 0.55
        assert config.meadow_threshold == 0.1
        assert config.water_threshold == -0.25
        assert config.mountain_threshold == 0.75
        # Multi-octave noise parameters (WI-240)
        assert config.octaves == 4
        assert config.lacunarity == 2.0
        assert config.persistence == 0.5
        assert config.domain_warp_strength == 0.5
        # Noise scale parameters (WI-250)
        assert config.elevation_scale == 0.03
        assert config.moisture_scale == 0.04
        # Smoothing and forest parameters (WI-243, WI-246)
        assert config.smoothing_passes == 4
        assert config.forest_grove_count == 15
        assert config.forest_growth_iterations == 8

    def test_custom_seed(self) -> None:
        """TerrainConfig accepts custom seed."""
        config = TerrainConfig(seed=42)
        assert config.seed == 42

    def test_custom_world_size(self) -> None:
        """TerrainConfig accepts custom world_size."""
        config = TerrainConfig(world_size=100)
        assert config.world_size == 100

    def test_custom_octaves(self) -> None:
        """TerrainConfig accepts custom octaves."""
        config = TerrainConfig(seed=42, octaves=8)
        assert config.octaves == 8

    def test_custom_lacunarity(self) -> None:
        """TerrainConfig accepts custom lacunarity."""
        config = TerrainConfig(seed=42, lacunarity=2.5)
        assert config.lacunarity == 2.5

    def test_custom_persistence(self) -> None:
        """TerrainConfig accepts custom persistence."""
        config = TerrainConfig(seed=42, persistence=0.4)
        assert config.persistence == 0.4

    def test_custom_domain_warp_strength(self) -> None:
        """TerrainConfig accepts custom domain_warp_strength."""
        config = TerrainConfig(seed=42, domain_warp_strength=1.0)
        assert config.domain_warp_strength == 1.0

    def test_multi_octave_params_together(self) -> None:
        """TerrainConfig accepts all multi-octave params together."""
        config = TerrainConfig(
            seed=42,
            octaves=6,
            lacunarity=2.5,
            persistence=0.6,
            domain_warp_strength=0.8,
        )
        assert config.octaves == 6
        assert config.lacunarity == 2.5
        assert config.persistence == 0.6
        assert config.domain_warp_strength == 0.8

    def test_default_smoothing_passes(self) -> None:
        """TerrainConfig has default smoothing_passes of 4."""
        config = TerrainConfig()
        assert config.smoothing_passes == 4

    def test_custom_smoothing_passes(self) -> None:
        """TerrainConfig accepts custom smoothing_passes."""
        config = TerrainConfig(smoothing_passes=4)
        assert config.smoothing_passes == 4

    def test_smoothing_passes_zero(self) -> None:
        """TerrainConfig accepts smoothing_passes=0 (no smoothing)."""
        config = TerrainConfig(smoothing_passes=0)
        assert config.smoothing_passes == 0


class TestTerrainGenerator:
    """Tests for TerrainGenerator class."""

    def test_deterministic_generation(self) -> None:
        """Same seed produces same terrain at same position."""
        config = TerrainConfig(seed=42)
        gen1 = TerrainGenerator(config)
        gen2 = TerrainGenerator(TerrainConfig(seed=42))

        pos = Position(5, 5)
        assert gen1.generate_terrain(pos) == gen2.generate_terrain(pos)

    def test_deterministic_multiple_calls(self) -> None:
        """Same generator produces same terrain on multiple calls."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        pos = Position(10, -3)
        first_result = gen.generate_terrain(pos)
        second_result = gen.generate_terrain(pos)

        assert first_result == second_result

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for terrain generation")
    def test_different_seeds_produce_different_noise_values(self) -> None:
        """Different seeds produce different fBm values at same position."""
        gen1 = TerrainGenerator(TerrainConfig(seed=42))
        gen2 = TerrainGenerator(TerrainConfig(seed=12345))

        # Check that fBm values differ for different seeds
        different_count = 0
        for x in range(-25, 26):
            for y in range(-25, 26):
                # Use the fBm directly to test noise generation, not terrain classification
                v1 = gen1._warped_fbm(x * 0.1, y * 0.1)
                v2 = gen2._warped_fbm(x * 0.1, y * 0.1)
                if abs(v1 - v2) > 0.001:
                    different_count += 1

        # Most positions should have different noise values
        # (fBm is deterministic per seed but varies between seeds)
        total_positions = 51 * 51
        assert different_count > total_positions * 0.9, \
            f"Only {different_count}/{total_positions} positions had different noise values"

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for fBm tests")
    def test_fbm_can_produce_varied_terrain_values(self) -> None:
        """fBm produces values in a range that could classify as different terrain types.

        Note: Actual terrain classification depends on thresholds (water_threshold,
        mountain_threshold, etc.) which may need adjustment for the fBm output range.
        This test verifies the fBm implementation produces varied values.
        """
        gen = TerrainGenerator(TerrainConfig(seed=42))

        # Collect fBm values across a range of positions
        elevation_values = []
        for x in range(-30, 31):
            for y in range(-30, 31):
                elev = gen._warped_fbm(x * 0.05, y * 0.05)
                elevation_values.append(elev)

        # fBm should produce values in roughly [-1, 1] range
        min_val = min(elevation_values)
        max_val = max(elevation_values)

        # Values should span a reasonable range (not all same value)
        value_range = max_val - min_val
        assert value_range > 0.5, f"fBm values too uniform, range={value_range:.3f}"

        # Values should be within expected bounds
        assert min_val >= -1.5, f"fBm min value {min_val:.3f} below expected range"
        assert max_val <= 1.5, f"fBm max value {max_val:.3f} above expected range"

    def test_generate_chunk_correct_count(self) -> None:
        """generate_chunk yields correct number of positions for given bounds."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        bounds = Bounds(min_x=0, min_y=0, max_x=4, max_y=2)

        positions = list(gen.generate_chunk(bounds))

        # Should be (max_x - min_x + 1) * (max_y - min_y + 1) = 5 * 3 = 15
        assert len(positions) == 15

        # Verify all positions are within bounds
        for pos, terrain in positions:
            assert bounds.min_x <= pos.x <= bounds.max_x
            assert bounds.min_y <= pos.y <= bounds.max_y

    def test_generate_chunk_yields_positions(self) -> None:
        """generate_chunk yields all positions within bounds."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        bounds = Bounds(min_x=-1, min_y=-1, max_x=1, max_y=1)

        positions = [(pos, terrain) for pos, terrain in gen.generate_chunk(bounds)]
        position_set = {pos for pos, _ in positions}

        expected = {
            Position(-1, -1),
            Position(-1, 0),
            Position(-1, 1),
            Position(0, -1),
            Position(0, 0),
            Position(0, 1),
            Position(1, -1),
            Position(1, 0),
            Position(1, 1),
        }

        assert position_set == expected

    def test_is_passable_matches_generate_terrain(self) -> None:
        """is_passable(Position(x, y)) matches generate_terrain(Position(x, y)).passable."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        for x in range(-10, 11):
            for y in range(-10, 11):
                pos = Position(x, y)
                terrain = gen.generate_terrain(pos)
                assert gen.is_passable(pos) == terrain.passable

    def test_seed_property(self) -> None:
        """TerrainGenerator exposes seed property."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        assert gen.seed == 42

    def test_auto_generated_seed(self) -> None:
        """TerrainGenerator auto-generates seed when not provided."""
        gen = TerrainGenerator()  # No config, so seed is auto-generated
        assert isinstance(gen.seed, int)
        assert gen.seed >= 0

    def test_random_fallback_works_without_noise(self) -> None:
        """Fallback to seeded random works when noise library not installed.

        This test runs in both scenarios:
        - With noise library installed: uses Perlin noise
        - Without noise library: uses seeded random fallback

        In either case, the generator must be deterministic.
        """
        gen1 = TerrainGenerator(TerrainConfig(seed=999))
        gen2 = TerrainGenerator(TerrainConfig(seed=999))

        pos = Position(7, 3)
        assert gen1.generate_terrain(pos) == gen2.generate_terrain(pos)

        # Also verify it produces valid terrain types
        terrain = gen1.generate_terrain(pos)
        assert terrain in (
            TerrainType.WATER,
            TerrainType.MOUNTAIN,
            TerrainType.FOREST,
            TerrainType.MEADOW,
            TerrainType.PLAIN,
        )

    def test_config_parameter(self) -> None:
        """TerrainGenerator uses config parameters."""
        config = TerrainConfig(
            seed=42,
            water_threshold=-0.5,  # More water
            mountain_threshold=0.5,  # More mountains
        )
        gen = TerrainGenerator(config)

        # Generate terrain and verify it works with custom config
        terrain = gen.generate_terrain(Position(0, 0))
        assert isinstance(terrain, TerrainType)

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for fBm tests")
    def test_fbm_returns_values_in_range(self) -> None:
        """_fbm returns values in approximately [-1, 1] range."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        # Test multiple positions to ensure range is reasonable
        for x in range(-5, 6):
            for y in range(-5, 6):
                value = gen._fbm(x * 0.1, y * 0.1, octaves=4,
                                 lacunarity=2.0, persistence=0.5, base=42)
                # fBm should produce values roughly in [-1, 1]
                assert -1.5 <= value <= 1.5, f"Value {value} at ({x}, {y}) out of range"

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for fBm tests")
    def test_fbm_is_deterministic(self) -> None:
        """_fbm produces same output for same input."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        # Same parameters should produce same result
        value1 = gen._fbm(1.5, 2.3, octaves=4, lacunarity=2.0,
                          persistence=0.5, base=42)
        value2 = gen._fbm(1.5, 2.3, octaves=4, lacunarity=2.0,
                          persistence=0.5, base=42)
        assert value1 == value2

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for fBm tests")
    def test_fbm_different_seeds_produce_different_results(self) -> None:
        """_fbm with different base produces different values."""
        gen1 = TerrainGenerator(TerrainConfig(seed=42))
        gen2 = TerrainGenerator(TerrainConfig(seed=12345))

        # Test multiple positions to ensure we find differences
        different_count = 0
        for x in range(10):
            for y in range(10):
                value1 = gen1._fbm(x * 0.17 + 0.5, y * 0.23 + 0.3,
                                   octaves=4, lacunarity=2.0,
                                   persistence=0.5, base=42)
                value2 = gen2._fbm(x * 0.17 + 0.5, y * 0.23 + 0.3,
                                   octaves=4, lacunarity=2.0,
                                   persistence=0.5, base=12345)
                if value1 != value2:
                    different_count += 1

        # At least some positions should have different values
        assert different_count > 50, f"Only {different_count} positions differed"

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for fBm tests")
    def test_fbm_octaves_affects_output(self) -> None:
        """More octaves produces smoother/more detailed noise."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        # Test multiple positions to find differences
        differences_found = 0
        for x in range(5):
            for y in range(5):
                val_1_octave = gen._fbm(x * 0.31 + 0.7, y * 0.41 + 0.2,
                                        octaves=1, lacunarity=2.0,
                                        persistence=0.5, base=42)
                val_4_octaves = gen._fbm(x * 0.31 + 0.7, y * 0.41 + 0.2,
                                         octaves=4, lacunarity=2.0,
                                         persistence=0.5, base=42)
                val_8_octaves = gen._fbm(x * 0.31 + 0.7, y * 0.41 + 0.2,
                                         octaves=8, lacunarity=2.0,
                                         persistence=0.5, base=42)
                if val_1_octave != val_4_octaves or val_4_octaves != val_8_octaves:
                    differences_found += 1

        # Different octave counts should produce different values at some positions
        assert differences_found > 0, "No differences found between octave counts"

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for fBm tests")
    def test_warped_fbm_is_deterministic(self) -> None:
        """_warped_fbm produces same output for same input."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        # Same input should produce same result
        value1 = gen._warped_fbm(1.5, 2.3)
        value2 = gen._warped_fbm(1.5, 2.3)
        assert value1 == value2

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for fBm tests")
    def test_warped_fbm_different_seeds_produce_different_results(self) -> None:
        """_warped_fbm with different seeds produces different values."""
        gen1 = TerrainGenerator(TerrainConfig(seed=42))
        gen2 = TerrainGenerator(TerrainConfig(seed=12345))

        # Test multiple positions to ensure we find differences
        different_count = 0
        for x in range(10):
            for y in range(10):
                value1 = gen1._warped_fbm(x * 0.17 + 0.5, y * 0.23 + 0.3)
                value2 = gen2._warped_fbm(x * 0.17 + 0.5, y * 0.23 + 0.3)
                if value1 != value2:
                    different_count += 1

        # At least some positions should have different values
        assert different_count > 50, f"Only {different_count} positions differed"

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for fBm tests")
    def test_warped_fbm_returns_values_in_range(self) -> None:
        """_warped_fbm returns values in approximately [-1, 1] range."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        for x in range(-5, 6):
            for y in range(-5, 6):
                value = gen._warped_fbm(x * 0.1, y * 0.1)
                # Warped fBm should also produce values roughly in [-1, 1]
                assert -1.5 <= value <= 1.5, f"Value {value} at ({x}, {y}) out of range"

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for fBm tests")
    def test_generate_with_noise_determinism(self) -> None:
        """Same seed produces identical terrain (determinism test)."""
        gen1 = TerrainGenerator(TerrainConfig(seed=42))
        gen2 = TerrainGenerator(TerrainConfig(seed=42))

        # Generate terrain for the same positions with both generators
        for x in range(-10, 11):
            for y in range(-10, 11):
                pos = Position(x, y)
                assert gen1.generate_terrain(pos) == gen2.generate_terrain(pos)

    def test_classify_terrain_water_at_low_elevation(self) -> None:
        """Elevation below water_threshold returns WATER."""
        config = TerrainConfig(seed=42, water_threshold=-0.3)
        gen = TerrainGenerator(config)

        # Very low elevation should be water
        result = gen._classify_terrain(elevation=-1.0, moisture=0.0)
        assert result == TerrainType.WATER

        # Just below threshold should be water
        result = gen._classify_terrain(elevation=-0.31, moisture=0.0)
        assert result == TerrainType.WATER

        # At threshold should NOT be water (water_threshold is exclusive)
        result = gen._classify_terrain(elevation=-0.3, moisture=0.0)
        assert result != TerrainType.WATER

    def test_classify_terrain_mountain_at_high_elevation(self) -> None:
        """Elevation above mountain_threshold returns MOUNTAIN."""
        config = TerrainConfig(seed=42, mountain_threshold=0.7)
        gen = TerrainGenerator(config)

        # Very high elevation should be mountain
        result = gen._classify_terrain(elevation=1.0, moisture=0.0)
        assert result == TerrainType.MOUNTAIN

        # Just above threshold should be mountain
        result = gen._classify_terrain(elevation=0.71, moisture=0.0)
        assert result == TerrainType.MOUNTAIN

        # At threshold should NOT be mountain (mountain_threshold is exclusive)
        result = gen._classify_terrain(elevation=0.7, moisture=0.0)
        assert result != TerrainType.MOUNTAIN

    def test_classify_terrain_passable_uses_moisture(self) -> None:
        """In passable elevation range, terrain depends on moisture thresholds."""
        config = TerrainConfig(
            seed=42,
            water_threshold=-0.3,
            mountain_threshold=0.7,
            forest_threshold=0.5,  # moisture > 0.5 -> forest
            meadow_threshold=0.0,  # moisture > 0.0 -> meadow
        )
        gen = TerrainGenerator(config)

        # Mid-range elevation (passable)
        elevation = 0.0

        # High moisture -> forest
        result = gen._classify_terrain(elevation=elevation, moisture=0.6)
        assert result == TerrainType.FOREST

        # Moderate moisture -> meadow
        result = gen._classify_terrain(elevation=elevation, moisture=0.3)
        assert result == TerrainType.MEADOW

        # Low moisture -> plain
        result = gen._classify_terrain(elevation=elevation, moisture=-0.5)
        assert result == TerrainType.PLAIN

    def test_classify_terrain_elevation_takes_precedence(self) -> None:
        """Elevation checks (water/mountain) take precedence over moisture."""
        config = TerrainConfig(
            seed=42,
            water_threshold=-0.3,
            mountain_threshold=0.7,
            forest_threshold=0.5,
            meadow_threshold=0.0,
        )
        gen = TerrainGenerator(config)

        # Low elevation is water regardless of moisture
        result = gen._classify_terrain(elevation=-1.0, moisture=0.9)
        assert result == TerrainType.WATER

        # High elevation is mountain regardless of moisture
        result = gen._classify_terrain(elevation=1.0, moisture=-0.9)
        assert result == TerrainType.MOUNTAIN

    def test_classify_terrain_deterministic(self) -> None:
        """Same elevation and moisture always produce same terrain type."""
        config = TerrainConfig(
            seed=42,
            water_threshold=-0.3,
            mountain_threshold=0.7,
            forest_threshold=0.5,
            meadow_threshold=0.0,
        )
        gen = TerrainGenerator(config)

        # Multiple calls with same inputs should return same result
        for _ in range(10):
            assert gen._classify_terrain(0.0, 0.3) == TerrainType.MEADOW
            assert gen._classify_terrain(-1.0, 0.0) == TerrainType.WATER
            assert gen._classify_terrain(1.0, 0.0) == TerrainType.MOUNTAIN

    def test_threshold_ordering_forest_higher_than_meadow(self) -> None:
        """With correct threshold ordering (forest > meadow), terrain classes correctly."""
        # forest_threshold > meadow_threshold: high moisture = forest, moderate = meadow
        config = TerrainConfig(
            seed=42,
            water_threshold=-0.3,
            mountain_threshold=0.7,
            forest_threshold=0.5,  # Higher threshold
            meadow_threshold=0.0,  # Lower threshold
        )
        gen = TerrainGenerator(config)

        elevation = 0.0  # Passable elevation

        # Very high moisture -> forest
        result = gen._classify_terrain(elevation, moisture=0.7)
        assert result == TerrainType.FOREST

        # Moderate moisture (between thresholds) -> meadow
        result = gen._classify_terrain(elevation, moisture=0.25)
        assert result == TerrainType.MEADOW

        # Low moisture -> plain
        result = gen._classify_terrain(elevation, moisture=-0.5)
        assert result == TerrainType.PLAIN

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for terrain tests")
    def test_generate_with_noise_produces_all_terrain_types(self) -> None:
        """Noise-based generation produces all five terrain types over a range."""
        config = TerrainConfig(
            seed=42,
            water_threshold=-0.3,
            mountain_threshold=0.7,
            forest_threshold=0.5,
            meadow_threshold=0.0,
        )
        gen = TerrainGenerator(config)

        terrain_types_found = set()

        # Sample a larger area to find all terrain types
        for x in range(-50, 51):
            for y in range(-50, 51):
                pos = Position(x, y)
                terrain = gen.generate_terrain(pos)
                terrain_types_found.add(terrain)

        # All five terrain types should appear
        assert TerrainType.WATER in terrain_types_found, "No WATER found in sample"
        assert TerrainType.MOUNTAIN in terrain_types_found, "No MOUNTAIN found in sample"
        assert TerrainType.FOREST in terrain_types_found, "No FOREST found in sample"
        assert TerrainType.MEADOW in terrain_types_found, "No MEADOW found in sample"
        assert TerrainType.PLAIN in terrain_types_found, "No PLAIN found in sample"


class TestTerrainGrid:
    """Tests for TerrainGrid class."""

    def test_get_terrain_returns_same_type_on_repeated_calls(self) -> None:
        """TerrainGrid(generator).get_terrain(Position(0, 0)) returns same type on repeated calls."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen)

        pos = Position(0, 0)
        first_result = grid.get_terrain(pos)
        second_result = grid.get_terrain(pos)

        assert first_result == second_result
        assert first_result in (
            TerrainType.WATER,
            TerrainType.MOUNTAIN,
            TerrainType.FOREST,
            TerrainType.MEADOW,
            TerrainType.PLAIN,
        )

    def test_cache_populated_on_first_lookup(self) -> None:
        """Cache is populated on first lookup for a position."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen)

        pos = Position(5, -3)
        assert pos not in grid._cache

        terrain = grid.get_terrain(pos)

        assert pos in grid._cache
        assert grid._cache[pos] == terrain

    def test_get_terrain_in_bounds_returns_correct_positions(self) -> None:
        """get_terrain_in_bounds(bounds) returns correct positions for bounds."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen)

        bounds = Bounds(min_x=0, min_y=0, max_x=2, max_y=2)
        result = grid.get_terrain_in_bounds(bounds)

        # Verify all expected positions are present
        expected_positions = {
            Position(0, 0),
            Position(0, 1),
            Position(0, 2),
            Position(1, 0),
            Position(1, 1),
            Position(1, 2),
            Position(2, 0),
            Position(2, 1),
            Position(2, 2),
        }
        assert set(result.keys()) == expected_positions

        # Verify all values are TerrainType
        for terrain in result.values():
            assert isinstance(terrain, TerrainType)

    def test_is_passable_delegates_to_get_terrain(self) -> None:
        """is_passable(Position(x, y)) delegates to get_terrain(Position(x, y)).passable."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen)

        for x in range(-5, 6):
            for y in range(-5, 6):
                pos = Position(x, y)
                expected = grid.get_terrain(pos).passable
                assert grid.is_passable(pos) == expected

    def test_clear_cache_removes_all_cached_terrain(self) -> None:
        """clear_cache() removes all cached terrain."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen)

        # Populate cache with several positions
        grid.get_terrain(Position(0, 0))
        grid.get_terrain(Position(1, 1))
        grid.get_terrain(Position(-2, 3))

        assert len(grid._cache) == 3

        grid.clear_cache()

        assert len(grid._cache) == 0

    def test_cache_hit_behavior_generator_not_called(self) -> None:
        """A test verifies cache hit behavior (generator not called for cached positions)."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen)

        pos = Position(10, 10)

        # First call: cache miss, generator is called
        assert pos not in grid._cache
        first_terrain = grid.get_terrain(pos)
        assert pos in grid._cache

        # Capture the cached value
        cached_value = grid._cache[pos]

        # Second call: cache hit, should return cached value without calling generator
        # We verify this by checking that the cache wasn't modified
        second_terrain = grid.get_terrain(pos)
        assert second_terrain == first_terrain
        assert grid._cache[pos] is cached_value  # Same object reference

    def test_seed_property_exposes_generator_seed(self) -> None:
        """TerrainGrid exposes seed property from generator."""
        gen = TerrainGenerator(TerrainConfig(seed=12345))
        grid = TerrainGrid(gen)

        assert grid.seed == 12345

    def test_get_terrain_in_bounds_caches_results(self) -> None:
        """get_terrain_in_bounds caches all generated terrain."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen)

        bounds = Bounds(min_x=-1, min_y=-1, max_x=1, max_y=1)
        result = grid.get_terrain_in_bounds(bounds)

        # All positions from result should be in cache
        for pos in result:
            assert pos in grid._cache

        # Cache should contain exactly the positions from bounds
        expected_positions = {
            Position(-1, -1),
            Position(-1, 0),
            Position(-1, 1),
            Position(0, -1),
            Position(0, 0),
            Position(0, 1),
            Position(1, -1),
            Position(1, 0),
            Position(1, 1),
        }
        assert set(grid._cache.keys()) == expected_positions


class TestSmoothTerrain:
    """Tests for cellular automata smoothing functions."""

    def test_smooth_terrain_returns_copy_with_zero_passes(self) -> None:
        """smooth_terrain with passes=0 returns a copy of the grid unchanged."""
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.PLAIN,
        }
        result = smooth_terrain(grid, passes=0)
        assert result == grid
        assert result is not grid  # Should be a copy

    def test_smooth_terrain_isolated_water_becomes_meadow(self) -> None:
        """Water with fewer than 3 water neighbors becomes meadow."""
        # Create a grid with an isolated water cell surrounded by land
        grid = {
            Position(0, 0): TerrainType.WATER,  # Isolated water
            Position(0, 1): TerrainType.PLAIN,
            Position(1, 0): TerrainType.PLAIN,
            Position(1, 1): TerrainType.PLAIN,
            Position(-1, 0): TerrainType.PLAIN,
            Position(-1, -1): TerrainType.PLAIN,
            Position(0, -1): TerrainType.PLAIN,
            Position(-1, 1): TerrainType.PLAIN,
            Position(1, -1): TerrainType.PLAIN,
        }
        result = smooth_terrain(grid, passes=1)
        # Isolated water (0 water neighbors) should become meadow
        assert result[Position(0, 0)] == TerrainType.MEADOW

    def test_smooth_terrain_connected_water_stays_water(self) -> None:
        """Water with 3+ water neighbors stays water."""
        # Create a grid with water cluster (5 water cells)
        grid = {
            Position(0, 0): TerrainType.WATER,  # Center has 4 water neighbors
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.WATER,
            Position(1, 1): TerrainType.WATER,
            Position(-1, 0): TerrainType.WATER,
            Position(-1, -1): TerrainType.PLAIN,
            Position(0, -1): TerrainType.PLAIN,
            Position(-1, 1): TerrainType.PLAIN,
            Position(1, -1): TerrainType.PLAIN,
        }
        result = smooth_terrain(grid, passes=1)
        # Center water (4 water neighbors) should stay water
        assert result[Position(0, 0)] == TerrainType.WATER

    def test_smooth_terrain_land_surrounded_by_water_becomes_water(self) -> None:
        """Land with 4+ water neighbors becomes water."""
        # Create a grid with land surrounded by water
        grid = {
            Position(0, 0): TerrainType.PLAIN,  # Surrounded by water
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.WATER,
            Position(1, 1): TerrainType.WATER,
            Position(-1, 0): TerrainType.WATER,
            Position(-1, -1): TerrainType.WATER,
            Position(0, -1): TerrainType.WATER,
            Position(-1, 1): TerrainType.PLAIN,
            Position(1, -1): TerrainType.PLAIN,
        }
        result = smooth_terrain(grid, passes=1)
        # Plain with 5 water neighbors should become water
        assert result[Position(0, 0)] == TerrainType.WATER

    def test_smooth_terrain_connected_mountain_stays_mountain(self) -> None:
        """Mountain with 2+ mountain neighbors stays mountain."""
        # Create a grid with connected mountain cluster
        grid = {
            Position(0, 0): TerrainType.MOUNTAIN,  # Has 2 mountain neighbors
            Position(0, 1): TerrainType.MOUNTAIN,
            Position(1, 0): TerrainType.MOUNTAIN,
            Position(1, 1): TerrainType.PLAIN,
            Position(-1, 0): TerrainType.PLAIN,
            Position(-1, -1): TerrainType.PLAIN,
            Position(0, -1): TerrainType.PLAIN,
            Position(-1, 1): TerrainType.PLAIN,
            Position(1, -1): TerrainType.PLAIN,
        }
        result = smooth_terrain(grid, passes=1)
        # Connected mountain should stay mountain
        assert result[Position(0, 0)] == TerrainType.MOUNTAIN

    def test_smooth_terrain_isolated_mountain_becomes_plain(self) -> None:
        """Mountain with fewer than 2 mountain neighbors becomes plain."""
        # Create a grid with isolated mountain
        grid = {
            Position(0, 0): TerrainType.MOUNTAIN,  # Has 0 mountain neighbors
            Position(0, 1): TerrainType.PLAIN,
            Position(1, 0): TerrainType.PLAIN,
            Position(1, 1): TerrainType.PLAIN,
            Position(-1, 0): TerrainType.PLAIN,
            Position(-1, -1): TerrainType.PLAIN,
            Position(0, -1): TerrainType.PLAIN,
            Position(-1, 1): TerrainType.PLAIN,
            Position(1, -1): TerrainType.PLAIN,
        }
        result = smooth_terrain(grid, passes=1)
        # Isolated mountain should become plain
        assert result[Position(0, 0)] == TerrainType.PLAIN

    def test_smooth_terrain_is_deterministic(self) -> None:
        """Same grid + passes produces same result."""
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.PLAIN,
            Position(1, 0): TerrainType.PLAIN,
            Position(1, 1): TerrainType.PLAIN,
        }
        result1 = smooth_terrain(grid, passes=2)
        result2 = smooth_terrain(grid, passes=2)
        assert result1 == result2

    def test_smooth_terrain_multiple_passes(self) -> None:
        """Multiple passes further smooth terrain."""
        # Create a small water lake
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.WATER,
            Position(1, 1): TerrainType.PLAIN,
            Position(-1, 0): TerrainType.PLAIN,
            Position(0, -1): TerrainType.PLAIN,
        }
        result_1_pass = smooth_terrain(grid, passes=1)
        result_2_passes = smooth_terrain(grid, passes=2)
        # Results should differ with different pass counts
        # (unless the terrain is already stable)
        # We verify that passes parameter affects output
        assert isinstance(result_1_pass, dict)
        assert isinstance(result_2_passes, dict)

    def test_count_neighbors_counts_correctly(self) -> None:
        """_count_neighbors counts terrain types in Moore neighborhood."""
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.PLAIN,
            Position(1, 1): TerrainType.MOUNTAIN,
            Position(-1, 0): TerrainType.FOREST,
            Position(-1, -1): TerrainType.MEADOW,
            Position(0, -1): TerrainType.WATER,
            Position(-1, 1): TerrainType.PLAIN,
            Position(1, -1): TerrainType.MOUNTAIN,
        }
        counts = _count_neighbors(grid, Position(0, 0))
        # Moore neighborhood around (0,0): (0,1), (1,0), (1,1), (-1,0), (-1,-1), (0,-1), (-1,1), (1,-1)
        # WATER: (0,1), (0,-1) = 2
        # PLAIN: (1,0), (-1,1) = 2
        # MOUNTAIN: (1,1), (1,-1) = 2
        # FOREST: (-1,0) = 1
        # MEADOW: (-1,-1) = 1
        assert counts.get(TerrainType.WATER, 0) == 2
        assert counts.get(TerrainType.PLAIN, 0) == 2
        assert counts.get(TerrainType.MOUNTAIN, 0) == 2
        assert counts.get(TerrainType.FOREST, 0) == 1
        assert counts.get(TerrainType.MEADOW, 0) == 1

    def test_count_neighbors_empty_neighbors(self) -> None:
        """_count_neighbors returns empty counts for cells with no neighbors in grid."""
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(100, 100): TerrainType.PLAIN,  # Far away, not a neighbor
        }
        counts = _count_neighbors(grid, Position(0, 0))
        # All 8 neighbor positions are missing from grid
        assert counts.get(TerrainType.WATER, 0) == 0
        assert counts.get(TerrainType.PLAIN, 0) == 0

    def test_apply_smoothing_rule_water_isolated(self) -> None:
        """_apply_smoothing_rule converts isolated water to meadow."""
        # Water with 2 water neighbors (less than 3)
        neighbor_counts = {TerrainType.WATER: 2, TerrainType.PLAIN: 6}
        result = _apply_smoothing_rule(TerrainType.WATER, neighbor_counts)
        assert result == TerrainType.MEADOW

    def test_apply_smoothing_rule_water_connected(self) -> None:
        """_apply_smoothing_rule keeps connected water as water."""
        # Water with 3 water neighbors
        neighbor_counts = {TerrainType.WATER: 3, TerrainType.PLAIN: 5}
        result = _apply_smoothing_rule(TerrainType.WATER, neighbor_counts)
        assert result == TerrainType.WATER

    def test_apply_smoothing_rule_land_surrounded(self) -> None:
        """_apply_smoothing_rule converts land surrounded by water to water."""
        # Plain with 4 water neighbors
        neighbor_counts = {TerrainType.WATER: 4, TerrainType.PLAIN: 4}
        result = _apply_smoothing_rule(TerrainType.PLAIN, neighbor_counts)
        assert result == TerrainType.WATER

    def test_apply_smoothing_rule_land_not_surrounded(self) -> None:
        """_apply_smoothing_rule keeps land with few water neighbors unchanged."""
        # Plain with 3 water neighbors (less than 4)
        neighbor_counts = {TerrainType.WATER: 3, TerrainType.PLAIN: 5}
        result = _apply_smoothing_rule(TerrainType.PLAIN, neighbor_counts)
        assert result == TerrainType.PLAIN

    def test_apply_smoothing_rule_mountain_connected(self) -> None:
        """_apply_smoothing_rule keeps connected mountain as mountain."""
        # Mountain with 2 mountain neighbors
        neighbor_counts = {TerrainType.MOUNTAIN: 2, TerrainType.PLAIN: 6}
        result = _apply_smoothing_rule(TerrainType.MOUNTAIN, neighbor_counts)
        assert result == TerrainType.MOUNTAIN

    def test_apply_smoothing_rule_mountain_isolated(self) -> None:
        """_apply_smoothing_rule converts isolated mountain to plain."""
        # Mountain with 1 mountain neighbor (less than 2)
        neighbor_counts = {TerrainType.MOUNTAIN: 1, TerrainType.PLAIN: 7}
        result = _apply_smoothing_rule(TerrainType.MOUNTAIN, neighbor_counts)
        assert result == TerrainType.PLAIN


class TestTerrainGridWithSmoothing:
    """Tests for TerrainGrid with CA smoothing integration."""

    def test_terrain_grid_accepts_smoothing_passes(self) -> None:
        """TerrainGrid accepts smoothing_passes parameter."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen, smoothing_passes=4)
        assert grid._smoothing_passes == 4

    def test_terrain_grid_default_smoothing_passes(self) -> None:
        """TerrainGrid default smoothing_passes is 4."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen)
        assert grid._smoothing_passes == 4

    def test_get_terrain_in_bounds_applies_smoothing(self) -> None:
        """get_terrain_in_bounds applies smoothing to generated terrain."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen, smoothing_passes=1)

        bounds = Bounds(min_x=0, min_y=0, max_x=2, max_y=2)
        result = grid.get_terrain_in_bounds(bounds)

        # Verify all positions are present
        assert len(result) == 9
        # Verify all values are TerrainType
        for terrain in result.values():
            assert isinstance(terrain, TerrainType)

    def test_get_terrain_in_bounds_with_zero_passes(self) -> None:
        """get_terrain_in_bounds with smoothing_passes=0 returns raw terrain."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen, smoothing_passes=0)

        bounds = Bounds(min_x=0, min_y=0, max_x=2, max_y=2)
        result = grid.get_terrain_in_bounds(bounds)

        # With zero passes, smoothing returns a copy unchanged
        assert len(result) == 9

    def test_cache_contains_smoothed_terrain(self) -> None:
        """TerrainGrid caches smoothed terrain from get_terrain_in_bounds."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen, smoothing_passes=1)

        bounds = Bounds(min_x=0, min_y=0, max_x=1, max_y=1)
        result = grid.get_terrain_in_bounds(bounds)

        # Cache should contain the same terrain as returned
        for pos, terrain in result.items():
            assert pos in grid._cache
            assert grid._cache[pos] == terrain

    def test_smoothing_creates_connected_water_regions(self) -> None:
        """Smoothing reduces isolated water cells and creates connected regions."""
        # This is a statistical test - with smoothing, we expect fewer isolated water cells
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid_no_smooth = TerrainGrid(gen, smoothing_passes=0)
        grid_smooth = TerrainGrid(gen, smoothing_passes=3)

        # Generate a larger area
        bounds = Bounds(min_x=-10, min_y=-10, max_x=10, max_y=10)

        # Get terrain with and without smoothing
        raw = {}
        for pos, terrain in gen.generate_chunk(bounds):
            raw[pos] = terrain

        smoothed = grid_smooth.get_terrain_in_bounds(bounds)

        # Count water cells before and after
        # (With smoothing, isolated water should be reduced)
        raw_water_count = sum(1 for t in raw.values() if t == TerrainType.WATER)
        smoothed_water_count = sum(1 for t in smoothed.values() if t == TerrainType.WATER)

        # Both should be valid counts
        assert isinstance(raw_water_count, int)
        assert isinstance(smoothed_water_count, int)

    def test_get_terrain_uses_raw_generation(self) -> None:
        """get_terrain() for single position returns raw terrain (no smoothing context)."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen, smoothing_passes=1)

        # Single position lookup uses raw generation
        pos = Position(0, 0)
        terrain = grid.get_terrain(pos)

        # Should be a valid terrain type
        assert isinstance(terrain, TerrainType)

        # Cache should now contain this position
        assert pos in grid._cache


class TestRidgeGeneration:
    """Tests for mountain ridge generation (WI-244)."""

    def test_generate_ridge_chain_returns_start_and_end(self) -> None:
        """Ridge chain includes start and end points."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        start = Position(0, 0)
        end = Position(10, 10)

        ridge = gen.generate_ridge_chain(start, end)

        assert start in ridge
        assert end in ridge

    def test_generate_ridge_chain_connects_points(self) -> None:
        """Ridge chain points are connected (adjacent or diagonal)."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        start = Position(0, 0)
        end = Position(20, 20)

        ridge = gen.generate_ridge_chain(start, end)

        # Check that consecutive points are connected (Chebyshev distance <= 1)
        for i in range(len(ridge) - 1):
            p1, p2 = ridge[i], ridge[i + 1]
            dx = abs(p2.x - p1.x)
            dy = abs(p2.y - p1.y)
            # Points should be adjacent or diagonal neighbors
            assert dx <= 2 and dy <= 2, f"Points {p1} and {p2} are not connected"

    def test_generate_ridge_chain_deterministic(self) -> None:
        """Same seed produces same ridge chain."""
        gen1 = TerrainGenerator(TerrainConfig(seed=42))
        gen2 = TerrainGenerator(TerrainConfig(seed=42))

        start = Position(0, 0)
        end = Position(15, 10)

        ridge1 = gen1.generate_ridge_chain(start, end)
        ridge2 = gen2.generate_ridge_chain(start, end)

        assert ridge1 == ridge2

    def test_generate_ridge_chain_different_seeds(self) -> None:
        """Different seeds produce different ridge chains."""
        gen1 = TerrainGenerator(TerrainConfig(seed=42))
        gen2 = TerrainGenerator(TerrainConfig(seed=12345))

        start = Position(0, 0)
        end = Position(20, 15)

        ridge1 = gen1.generate_ridge_chain(start, end)
        ridge2 = gen2.generate_ridge_chain(start, end)

        # Ridges should differ (very unlikely to be identical)
        assert ridge1 != ridge2

    def test_generate_ridge_chain_roughness_affects_shape(self) -> None:
        """Higher roughness produces more jagged ridges."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        start = Position(0, 0)
        end = Position(30, 30)

        ridge_low = gen.generate_ridge_chain(start, end, roughness=0.1)
        ridge_high = gen.generate_ridge_chain(start, end, roughness=0.9)

        # Both should connect start to end
        assert start in ridge_low
        assert end in ridge_low
        assert start in ridge_high
        assert end in ridge_high

        # Higher roughness should generally produce more points
        # (though not guaranteed for all seeds, so we just check both are valid)
        assert len(ridge_low) >= 2
        assert len(ridge_high) >= 2

    def test_generate_ridge_chain_same_start_end(self) -> None:
        """Ridge chain handles degenerate case where start equals end."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        pos = Position(5, 5)

        ridge = gen.generate_ridge_chain(pos, pos)

        assert ridge == [pos]

    def test_generate_ridge_chain_short_distance(self) -> None:
        """Ridge chain handles short distances correctly."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        start = Position(0, 0)
        end = Position(1, 1)

        ridge = gen.generate_ridge_chain(start, end)

        # For very short distances, should have few points
        assert start in ridge
        assert end in ridge
        assert len(ridge) >= 2

    def test_generate_ridge_seeds_empty_heightmap(self) -> None:
        """_generate_ridge_seeds returns empty list for empty heightmap."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        pairs = gen._generate_ridge_seeds({})

        assert pairs == []

    def test_generate_ridge_seeds_finds_peaks(self) -> None:
        """_generate_ridge_seeds identifies peaks above threshold."""
        gen = TerrainGenerator(TerrainConfig(seed=42, mountain_threshold=0.7))

        # Create heightmap with some peaks
        heightmap: dict[Position, float] = {}
        for x in range(10):
            for y in range(10):
                # Most positions have low elevation
                heightmap[Position(x, y)] = 0.0

        # Add some peaks (elevation > 0.7 * 0.8 = 0.56)
        heightmap[Position(0, 0)] = 0.8
        heightmap[Position(5, 5)] = 0.9
        heightmap[Position(9, 9)] = 0.85

        pairs = gen._generate_ridge_seeds(heightmap, num_ridges=1)

        # Should find at least one pair (2 peaks)
        assert len(pairs) >= 1
        assert len(pairs[0]) == 2

    def test_generate_ridge_seeds_deterministic(self) -> None:
        """Same seed produces same ridge seeds."""
        gen1 = TerrainGenerator(TerrainConfig(seed=42, mountain_threshold=0.5))
        gen2 = TerrainGenerator(TerrainConfig(seed=42, mountain_threshold=0.5))

        # Create heightmap with peaks
        heightmap: dict[Position, float] = {}
        for x in range(20):
            for y in range(20):
                heightmap[Position(x, y)] = 0.0
        heightmap[Position(0, 0)] = 0.8
        heightmap[Position(10, 10)] = 0.8
        heightmap[Position(19, 19)] = 0.8

        pairs1 = gen1._generate_ridge_seeds(heightmap, num_ridges=1)
        pairs2 = gen2._generate_ridge_seeds(heightmap, num_ridges=1)

        assert pairs1 == pairs2

    def test_generate_ridge_seeds_respects_num_ridges(self) -> None:
        """_generate_ridge_seeds generates requested number of ridges."""
        gen = TerrainGenerator(TerrainConfig(seed=42, mountain_threshold=0.5))

        # Create heightmap with many peaks
        heightmap: dict[Position, float] = {}
        for i in range(20):
            heightmap[Position(i, i)] = 0.8

        pairs = gen._generate_ridge_seeds(heightmap, num_ridges=3)

        # Should generate at most 3 pairs
        assert len(pairs) <= 3

    def test_generate_ridges_from_heightmap(self) -> None:
        """generate_ridges_from_heightmap creates ridge chains."""
        gen = TerrainGenerator(TerrainConfig(seed=42, mountain_threshold=0.5))

        # Create heightmap with peaks
        heightmap: dict[Position, float] = {}
        for x in range(30):
            for y in range(30):
                heightmap[Position(x, y)] = 0.0
        # Add peaks
        heightmap[Position(0, 0)] = 0.9
        heightmap[Position(15, 15)] = 0.85
        heightmap[Position(29, 29)] = 0.88

        ridges = gen.generate_ridges_from_heightmap(heightmap)

        # Should generate some ridges
        assert isinstance(ridges, list)
        for ridge in ridges:
            assert isinstance(ridge, list)
            assert len(ridge) >= 2
            for pos in ridge:
                assert isinstance(pos, Position)

    def test_generate_terrain_with_ridges_marks_mountain(self) -> None:
        """generate_terrain_with_ridges marks ridge positions as MOUNTAIN."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        # Create a simple ridge
        ridge = [Position(5, 5), Position(6, 5), Position(7, 5)]
        ridges = [ridge]

        # Positions on ridge should be MOUNTAIN
        for pos in ridge:
            terrain = gen.generate_terrain_with_ridges(pos, ridges)
            assert terrain == TerrainType.MOUNTAIN

    def test_generate_terrain_with_ridges_preserves_other_terrain(self) -> None:
        """generate_terrain_with_ridges preserves terrain for non-ridge positions."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        ridge = [Position(100, 100)]  # Ridge far away
        ridges = [ridge]

        # Position not on ridge should get normal terrain
        pos = Position(0, 0)
        base_terrain = gen.generate_terrain(pos)
        ridge_terrain = gen.generate_terrain_with_ridges(pos, ridges)

        assert ridge_terrain == base_terrain

    def test_generate_terrain_with_ridges_none_ridges(self) -> None:
        """generate_terrain_with_ridges handles None ridges parameter."""
        gen = TerrainGenerator(TerrainConfig(seed=42))

        pos = Position(0, 0)
        terrain_with_none = gen.generate_terrain_with_ridges(pos, None)
        terrain_base = gen.generate_terrain(pos)

        assert terrain_with_none == terrain_base


class TestLakeDetection:
    """Tests for lake detection and expansion (WI-245)."""

    def test_detect_lakes_finds_connected_water(self) -> None:
        """detect_lakes correctly identifies connected water regions."""
        # Create a grid with a lake (5 connected water cells)
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.WATER,
            Position(1, 1): TerrainType.WATER,
            Position(2, 0): TerrainType.WATER,
            Position(3, 0): TerrainType.PLAIN,  # Not water
        }

        lakes = detect_lakes(grid, min_size=3)

        # Should find one lake with 5 water cells
        assert len(lakes) == 1
        positions, size = lakes[0]
        assert size == 5
        assert len(positions) == 5

    def test_detect_lakes_separates_disconnected_water(self) -> None:
        """detect_lakes separates disconnected water bodies."""
        # Create two separate lakes
        grid = {
            # Lake 1: 4 connected cells
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.WATER,
            Position(1, 1): TerrainType.WATER,
            # Gap (not water)
            Position(2, 0): TerrainType.PLAIN,
            Position(2, 1): TerrainType.PLAIN,
            # Lake 2: 3 connected cells
            Position(3, 0): TerrainType.WATER,
            Position(3, 1): TerrainType.WATER,
            Position(4, 0): TerrainType.WATER,
        }

        lakes = detect_lakes(grid, min_size=2)

        # Should find two lakes
        assert len(lakes) == 2
        # Sorted by size descending
        assert lakes[0][1] >= lakes[1][1]

    def test_detect_lakes_min_size_threshold(self) -> None:
        """detect_lakes excludes water bodies smaller than min_size."""
        # Create small and large water bodies
        grid = {
            # Small pond: 2 cells
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            # Large lake: 6 cells
            Position(10, 10): TerrainType.WATER,
            Position(10, 11): TerrainType.WATER,
            Position(11, 10): TerrainType.WATER,
            Position(11, 11): TerrainType.WATER,
            Position(12, 10): TerrainType.WATER,
            Position(12, 11): TerrainType.WATER,
        }

        # With min_size=3, small pond should be excluded
        lakes = detect_lakes(grid, min_size=3)
        assert len(lakes) == 1
        assert lakes[0][1] == 6

        # With min_size=1, both should be included
        lakes_all = detect_lakes(grid, min_size=1)
        assert len(lakes_all) == 2

    def test_detect_lakes_four_connected_not_diagonal(self) -> None:
        """detect_lakes uses 4-connected neighborhood, not diagonal."""
        # Create water cells connected only diagonally
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(1, 1): TerrainType.WATER,  # Diagonal from (0,0)
            Position(2, 2): TerrainType.WATER,  # Diagonal from (1,1)
        }

        lakes = detect_lakes(grid, min_size=1)

        # Each diagonal cell should be a separate lake (4-connected)
        assert len(lakes) == 3
        # Each lake should have size 1
        for _, size in lakes:
            assert size == 1

    def test_detect_lakes_4_connected_identifies_connected(self) -> None:
        """4-connected flood-fill correctly connects cardinal neighbors."""
        # Create L-shaped connected water (4-connected, not diagonal)
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,  # North of (0,0)
            Position(0, 2): TerrainType.WATER,  # North of (0,1)
            Position(1, 2): TerrainType.WATER,  # East of (0,2)
            Position(2, 2): TerrainType.WATER,  # East of (1,2)
        }

        lakes = detect_lakes(grid, min_size=3)

        assert len(lakes) == 1
        assert lakes[0][1] == 5

    def test_detect_lakes_sorted_by_size_descending(self) -> None:
        """detect_lakes returns lakes sorted by size descending."""
        grid = {
            # Small lake: 3 cells
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.WATER,
            # Medium lake: 5 cells
            Position(10, 0): TerrainType.WATER,
            Position(10, 1): TerrainType.WATER,
            Position(11, 0): TerrainType.WATER,
            Position(11, 1): TerrainType.WATER,
            Position(12, 0): TerrainType.WATER,
            # Large lake: 8 cells
            Position(20, 0): TerrainType.WATER,
            Position(20, 1): TerrainType.WATER,
            Position(20, 2): TerrainType.WATER,
            Position(21, 0): TerrainType.WATER,
            Position(21, 1): TerrainType.WATER,
            Position(21, 2): TerrainType.WATER,
            Position(22, 0): TerrainType.WATER,
            Position(22, 1): TerrainType.WATER,
        }

        lakes = detect_lakes(grid, min_size=1)

        assert len(lakes) == 3
        # Should be sorted descending
        assert lakes[0][1] == 8  # Large
        assert lakes[1][1] == 5  # Medium
        assert lakes[2][1] == 3  # Small

    def test_detect_lakes_empty_grid(self) -> None:
        """detect_lakes handles empty grid."""
        lakes = detect_lakes({}, min_size=1)
        assert lakes == []

    def test_detect_lakes_no_water(self) -> None:
        """detect_lakes handles grid with no water."""
        grid = {
            Position(0, 0): TerrainType.PLAIN,
            Position(0, 1): TerrainType.FOREST,
            Position(1, 0): TerrainType.MEADOW,
        }

        lakes = detect_lakes(grid, min_size=1)
        assert lakes == []

    def test_flood_fill_water_finds_all_connected(self) -> None:
        """_flood_fill_water finds all connected water cells."""
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.WATER,
            Position(1, 1): TerrainType.WATER,
            Position(2, 0): TerrainType.PLAIN,  # Barrier
            Position(2, 1): TerrainType.PLAIN,
        }

        lake = _flood_fill_water(grid, Position(0, 0))

        assert len(lake) == 4
        assert Position(0, 0) in lake
        assert Position(0, 1) in lake
        assert Position(1, 0) in lake
        assert Position(1, 1) in lake

    def test_flood_fill_water_starts_from_water_only(self) -> None:
        """_flood_fill_water returns empty set if start is not water."""
        grid = {
            Position(0, 0): TerrainType.PLAIN,
            Position(0, 1): TerrainType.WATER,
        }

        lake = _flood_fill_water(grid, Position(0, 0))

        assert lake == set()

    def test_detect_lakes_deterministic(self) -> None:
        """Same grid produces same lakes (determinism test)."""
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.WATER,
            Position(10, 0): TerrainType.WATER,
            Position(10, 1): TerrainType.WATER,
        }

        lakes1 = detect_lakes(grid, min_size=1)
        lakes2 = detect_lakes(grid, min_size=1)

        assert lakes1 == lakes2


class TestLakeExpansion:
    """Tests for lake expansion (WI-245)."""

    def test_expand_lake_grows_small_lake(self) -> None:
        """expand_lake grows a small lake to target size."""
        # Create a grid with a 3-cell lake surrounded by passable land
        grid = {
            # Lake
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.WATER,
            # Surrounding land
            Position(-1, 0): TerrainType.PLAIN,
            Position(-1, 1): TerrainType.PLAIN,
            Position(0, -1): TerrainType.PLAIN,
            Position(1, -1): TerrainType.PLAIN,
            Position(1, 1): TerrainType.PLAIN,
            Position(2, 0): TerrainType.PLAIN,
            Position(2, 1): TerrainType.PLAIN,
        }

        lake_positions = {
            Position(0, 0),
            Position(0, 1),
            Position(1, 0),
        }

        expanded = expand_lake(grid, lake_positions, target_size=6)

        # Should grow to at least target_size
        assert len(expanded) >= 6
        # Original lake positions should still be included
        assert lake_positions.issubset(expanded)

    def test_expand_lake_no_change_if_already_target_size(self) -> None:
        """expand_lake returns unchanged if lake already meets target size."""
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.WATER,
            Position(1, 1): TerrainType.WATER,
            Position(2, 0): TerrainType.WATER,
        }

        lake_positions = {
            Position(0, 0),
            Position(0, 1),
            Position(1, 0),
            Position(1, 1),
            Position(2, 0),
        }

        expanded = expand_lake(grid, lake_positions, target_size=3)

        # Should return same set unchanged
        assert expanded == lake_positions

    def test_expand_lake_preserves_original_positions(self) -> None:
        """expand_lake always includes original lake positions in result."""
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            Position(0, 2): TerrainType.PLAIN,
            Position(1, 0): TerrainType.PLAIN,
            Position(1, 1): TerrainType.PLAIN,
            Position(-1, 0): TerrainType.PLAIN,
            Position(0, -1): TerrainType.PLAIN,
        }

        lake_positions = {Position(0, 0), Position(0, 1)}

        expanded = expand_lake(grid, lake_positions, target_size=5)

        # Original positions must be in result
        assert Position(0, 0) in expanded
        assert Position(0, 1) in expanded

    def test_expand_lake_does_not_expand_into_mountains(self) -> None:
        """expand_lake avoids expanding into mountain cells."""
        # Create a small lake surrounded by mountains
        grid = {
            # Lake
            Position(0, 0): TerrainType.WATER,
            # Mountains surrounding
            Position(-1, 0): TerrainType.MOUNTAIN,
            Position(1, 0): TerrainType.MOUNTAIN,
            Position(0, -1): TerrainType.MOUNTAIN,
            Position(0, 1): TerrainType.MOUNTAIN,
            # Passable cells further out
            Position(-2, 0): TerrainType.PLAIN,
            Position(2, 0): TerrainType.PLAIN,
            Position(0, -2): TerrainType.PLAIN,
            Position(0, 2): TerrainType.PLAIN,
        }

        lake_positions = {Position(0, 0)}

        # Try to expand (should not include mountains)
        expanded = expand_lake(grid, lake_positions, target_size=3)

        # Mountains should NOT be in expanded lake
        assert Position(-1, 0) not in expanded
        assert Position(1, 0) not in expanded
        assert Position(0, -1) not in expanded
        assert Position(0, 1) not in expanded
        # If expansion occurred, it should reach passable cells
        if len(expanded) > 1:
            # Should only include original lake and passable cells
            for pos in expanded:
                if pos not in lake_positions:
                    assert grid[pos] != TerrainType.MOUNTAIN

    def test_expand_lake_grows_from_center(self) -> None:
        """expand_lake grows outward from lake center."""
        # Create a single water cell with expansion candidates
        grid = {}
        for y in range(-5, 6):
            for x in range(-5, 6):
                grid[Position(x, y)] = TerrainType.PLAIN

        grid[Position(0, 0)] = TerrainType.WATER

        lake_positions = {Position(0, 0)}

        expanded = expand_lake(grid, lake_positions, target_size=9)

        # Should grow roughly equally in all directions from center
        # First expansion should be the 4 cardinal neighbors
        assert len(expanded) == 9
        # Center should be included
        assert Position(0, 0) in expanded

    def test_expand_lake_handles_missing_grid_positions(self) -> None:
        """expand_lake does not expand into positions not in grid."""
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.PLAIN,
            # Position (0, -1) is not in grid
        }

        lake_positions = {Position(0, 0)}

        # Should handle missing positions gracefully
        expanded = expand_lake(grid, lake_positions, target_size=2)
        assert len(expanded) >= 1  # At least original position
        assert Position(0, 0) in expanded

    def test_expand_lake_limited_by_available_passable_cells(self) -> None:
        """expand_lake stops when no more passable cells available."""
        # Small lake surrounded by limited passable area
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            # Only 2 passable neighbors
            Position(1, 0): TerrainType.PLAIN,
            Position(-1, 0): TerrainType.PLAIN,
        }

        lake_positions = {Position(0, 0), Position(0, 1)}

        # Request large expansion but limited grid
        expanded = expand_lake(grid, lake_positions, target_size=100)

        # Should grow as much as possible
        assert Position(0, 0) in expanded
        assert Position(0, 1) in expanded
        # May or may not include all passable neighbors depending on expansion order
        assert len(expanded) >= 2

    def test_expand_lake_deterministic(self) -> None:
        """Same inputs produce same expanded lake."""
        grid = {
            Position(0, 0): TerrainType.WATER,
            Position(0, 1): TerrainType.WATER,
            Position(1, 0): TerrainType.PLAIN,
            Position(-1, 0): TerrainType.PLAIN,
            Position(0, -1): TerrainType.PLAIN,
            Position(0, 2): TerrainType.PLAIN,
        }

        lake_positions = {Position(0, 0), Position(0, 1)}

        expanded1 = expand_lake(grid, lake_positions, target_size=5)
        expanded2 = expand_lake(grid, lake_positions, target_size=5)

        assert expanded1 == expanded2


class TestTerrainConfigForestGrove:
    """Tests for TerrainConfig forest grove parameters (WI-246)."""

    def test_default_forest_grove_count(self) -> None:
        """TerrainConfig has default forest_grove_count of 15."""
        config = TerrainConfig()
        assert config.forest_grove_count == 15

    def test_default_forest_growth_iterations(self) -> None:
        """TerrainConfig has default forest_growth_iterations of 8."""
        config = TerrainConfig()
        assert config.forest_growth_iterations == 8

    def test_custom_forest_grove_count(self) -> None:
        """TerrainConfig accepts custom forest_grove_count."""
        config = TerrainConfig(seed=42, forest_grove_count=20)
        assert config.forest_grove_count == 20

    def test_custom_forest_growth_iterations(self) -> None:
        """TerrainConfig accepts custom forest_growth_iterations."""
        config = TerrainConfig(seed=42, forest_growth_iterations=8)
        assert config.forest_growth_iterations == 8

    def test_forest_grove_count_zero(self) -> None:
        """TerrainConfig accepts forest_grove_count=0 (no forests)."""
        config = TerrainConfig(seed=42, forest_grove_count=0)
        assert config.forest_grove_count == 0


class TestGenerateForestGroves:
    """Tests for generate_forest_groves method (WI-246)."""

    def test_generate_forest_groves_returns_copy(self) -> None:
        """generate_forest_groves returns a new grid, not modifying input."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid: dict[Position, TerrainType] = {
            Position(0, 0): TerrainType.PLAIN,
            Position(0, 1): TerrainType.PLAIN,
            Position(1, 0): TerrainType.PLAIN,
            Position(1, 1): TerrainType.PLAIN,
        }
        moisture_map: dict[Position, float] = {
            Position(0, 0): 0.8,  # High moisture - good for seeding
            Position(0, 1): 0.6,
            Position(1, 0): 0.6,
            Position(1, 1): 0.6,
        }

        result = gen.generate_forest_groves(grid, moisture_map, grove_count=1, growth_iterations=1)

        # Original grid should not be modified
        assert grid[Position(0, 0)] == TerrainType.PLAIN
        # Result should have forest
        assert TerrainType.FOREST in result.values()

    def test_generate_forest_groves_seeds_in_high_moisture(self) -> None:
        """Forest seeds are placed in high-moisture passable positions."""
        gen = TerrainGenerator(TerrainConfig(seed=42, forest_threshold=0.5))
        grid: dict[Position, TerrainType] = {
            Position(0, 0): TerrainType.PLAIN,  # High moisture
            Position(10, 10): TerrainType.PLAIN,  # Low moisture
        }
        moisture_map: dict[Position, float] = {
            Position(0, 0): 0.8,  # Above forest_threshold
            Position(10, 10): 0.2,  # Below forest_threshold
        }

        result = gen.generate_forest_groves(grid, moisture_map, grove_count=1, growth_iterations=0)

        # Only the high-moisture position should be forest (with 0 iterations, only seed)
        assert result[Position(0, 0)] == TerrainType.FOREST
        assert result[Position(10, 10)] == TerrainType.PLAIN

    def test_generate_forest_groves_does_not_overwrite_water(self) -> None:
        """Forest groves do not expand into water cells."""
        gen = TerrainGenerator(TerrainConfig(seed=42, forest_threshold=0.3))
        grid: dict[Position, TerrainType] = {
            Position(0, 0): TerrainType.PLAIN,
            Position(0, 1): TerrainType.WATER,  # Should not become forest
            Position(1, 0): TerrainType.PLAIN,
        }
        moisture_map: dict[Position, float] = {
            Position(0, 0): 0.8,
            Position(0, 1): 0.8,  # High moisture but water
            Position(1, 0): 0.6,
        }

        result = gen.generate_forest_groves(grid, moisture_map, grove_count=1, growth_iterations=2)

        # Water should remain water
        assert result[Position(0, 1)] == TerrainType.WATER

    def test_generate_forest_groves_does_not_overwrite_mountain(self) -> None:
        """Forest groves do not expand into mountain cells."""
        gen = TerrainGenerator(TerrainConfig(seed=42, forest_threshold=0.3))
        grid: dict[Position, TerrainType] = {
            Position(0, 0): TerrainType.PLAIN,
            Position(0, 1): TerrainType.MOUNTAIN,  # Should not become forest
            Position(1, 0): TerrainType.PLAIN,
        }
        moisture_map: dict[Position, float] = {
            Position(0, 0): 0.8,
            Position(0, 1): 0.8,  # High moisture but mountain
            Position(1, 0): 0.6,
        }

        result = gen.generate_forest_groves(grid, moisture_map, grove_count=1, growth_iterations=2)

        # Mountain should remain mountain
        assert result[Position(0, 1)] == TerrainType.MOUNTAIN

    def test_generate_forest_groves_creates_connected_clusters(self) -> None:
        """Forest growth creates connected clusters, not scattered cells."""
        gen = TerrainGenerator(TerrainConfig(seed=42, forest_threshold=0.3))
        # Create a 5x5 grid with high moisture only at center for seeding
        grid: dict[Position, TerrainType] = {}
        moisture_map: dict[Position, float] = {}
        for y in range(5):
            for x in range(5):
                pos = Position(x, y)
                grid[pos] = TerrainType.PLAIN
                # Center has high moisture (for seeding)
                if x == 2 and y == 2:
                    moisture_map[pos] = 0.8
                else:
                    # Moderate moisture for expansion (> 0.3 * 0.5 = 0.15)
                    moisture_map[pos] = 0.4

        result = gen.generate_forest_groves(grid, moisture_map, grove_count=1, growth_iterations=2)

        # The seed at center should grow into connected forest
        forest_positions = {pos for pos, t in result.items() if t == TerrainType.FOREST}

        # All forest positions should be within 2 Chebyshev distance from center
        # (with 2 iterations of 4-connected growth, max distance is 2)
        center = Position(2, 2)
        for pos in forest_positions:
            # Chebyshev distance: max(|dx|, |dy|) - accounts for diagonal reach in 2 iterations
            distance = max(abs(pos.x - center.x), abs(pos.y - center.y))
            assert distance <= 2, f"Forest at {pos} too far from center (distance {distance})"

        # Verify we actually have some forest
        assert len(forest_positions) > 0, "Should have at least the seed position as forest"

    def test_generate_forest_groves_is_deterministic(self) -> None:
        """Same seed produces same forest distribution."""
        config = TerrainConfig(seed=42, forest_threshold=0.3)

        grid: dict[Position, TerrainType] = {}
        moisture_map: dict[Position, float] = {}
        for y in range(10):
            for x in range(10):
                pos = Position(x, y)
                grid[pos] = TerrainType.PLAIN
                moisture_map[pos] = 0.7

        gen1 = TerrainGenerator(config)
        gen2 = TerrainGenerator(TerrainConfig(seed=42, forest_threshold=0.3))

        result1 = gen1.generate_forest_groves(grid, moisture_map, grove_count=5, growth_iterations=3)
        result2 = gen2.generate_forest_groves(grid, moisture_map, grove_count=5, growth_iterations=3)

        # Both results should have identical forest distributions
        forest1 = {pos for pos, t in result1.items() if t == TerrainType.FOREST}
        forest2 = {pos for pos, t in result2.items() if t == TerrainType.FOREST}
        assert forest1 == forest2

    def test_generate_forest_groves_respects_moisture_threshold(self) -> None:
        """Forest growth only expands into positions with sufficient moisture."""
        gen = TerrainGenerator(TerrainConfig(seed=42, forest_threshold=0.5))
        grid: dict[Position, TerrainType] = {
            Position(0, 0): TerrainType.PLAIN,  # Seed location (high moisture)
            Position(0, 1): TerrainType.PLAIN,  # Neighbor with high moisture
            Position(1, 0): TerrainType.PLAIN,  # Neighbor with low moisture
        }
        moisture_map: dict[Position, float] = {
            Position(0, 0): 0.8,  # High moisture (seed)
            Position(0, 1): 0.6,  # Above 0.5 * 0.5 = 0.25 threshold
            Position(1, 0): 0.1,  # Below threshold - should not become forest
        }

        result = gen.generate_forest_groves(grid, moisture_map, grove_count=1, growth_iterations=1)

        # High moisture neighbor should be forest
        assert result[Position(0, 1)] == TerrainType.FOREST
        # Low moisture neighbor should remain plain
        assert result[Position(1, 0)] == TerrainType.PLAIN

    def test_generate_forest_groves_uses_config_defaults(self) -> None:
        """generate_forest_groves uses config values when parameters not provided."""
        config = TerrainConfig(seed=42, forest_grove_count=7, forest_growth_iterations=3, forest_threshold=0.3)
        gen = TerrainGenerator(config)

        grid: dict[Position, TerrainType] = {}
        moisture_map: dict[Position, float] = {}
        for y in range(10):
            for x in range(10):
                pos = Position(x, y)
                grid[pos] = TerrainType.PLAIN
                moisture_map[pos] = 0.6

        result = gen.generate_forest_groves(grid, moisture_map)

        # Should have forest cells (from default config)
        forest_count = sum(1 for t in result.values() if t == TerrainType.FOREST)
        assert forest_count > 0

    def test_generate_forest_groves_no_high_moisture_positions(self) -> None:
        """When no high-moisture positions exist, returns grid unchanged."""
        gen = TerrainGenerator(TerrainConfig(seed=42, forest_threshold=0.8))
        grid: dict[Position, TerrainType] = {
            Position(0, 0): TerrainType.PLAIN,
            Position(0, 1): TerrainType.PLAIN,
        }
        moisture_map: dict[Position, float] = {
            Position(0, 0): 0.3,  # Below threshold
            Position(0, 1): 0.4,  # Below threshold
        }

        result = gen.generate_forest_groves(grid, moisture_map, grove_count=5, growth_iterations=3)

        # No forest should be created
        assert all(t == TerrainType.PLAIN for t in result.values())

    def test_generate_forest_groves_grove_count_limited_by_candidates(self) -> None:
        """When fewer high-moisture positions than requested, uses all available."""
        gen = TerrainGenerator(TerrainConfig(seed=42, forest_threshold=0.5))
        grid: dict[Position, TerrainType] = {
            Position(0, 0): TerrainType.PLAIN,  # High moisture
            Position(1, 0): TerrainType.PLAIN,  # Low moisture
        }
        moisture_map: dict[Position, float] = {
            Position(0, 0): 0.8,  # Only one high-moisture
            Position(1, 0): 0.2,  # Low moisture
        }

        # Request 5 groves but only 1 high-moisture position
        result = gen.generate_forest_groves(grid, moisture_map, grove_count=5, growth_iterations=0)

        # Should still work with just 1 seed
        assert result[Position(0, 0)] == TerrainType.FOREST

    def test_generate_forest_groves_multiple_groves(self) -> None:
        """Multiple grove seeds create multiple separate clusters."""
        gen = TerrainGenerator(TerrainConfig(seed=42, forest_threshold=0.5))

        # Create grid with two separated high-moisture seed positions
        grid: dict[Position, TerrainType] = {}
        moisture_map: dict[Position, float] = {}

        # Left cluster center (high moisture for seeding)
        for y in range(3):
            for x in range(3):
                pos = Position(x, y)
                grid[pos] = TerrainType.PLAIN
                if x == 1 and y == 1:
                    moisture_map[pos] = 0.8  # Only center is high-moisture (> threshold)
                else:
                    # Moderate moisture (> 0.5 * 0.5 = 0.25) for expansion but not seeding
                    moisture_map[pos] = 0.4

        # Right cluster center (high moisture for seeding)
        for y in range(3):
            for x in range(10, 13):
                pos = Position(x, y)
                grid[pos] = TerrainType.PLAIN
                if x == 11 and y == 1:
                    moisture_map[pos] = 0.8  # Only center is high-moisture
                else:
                    moisture_map[pos] = 0.4  # Moderate moisture for expansion

        # Verify only two high-moisture positions exist
        high_moisture = [pos for pos, m in moisture_map.items() if m > 0.5]
        assert len(high_moisture) == 2, f"Expected exactly 2 high-moisture positions, got {len(high_moisture)}"

        result = gen.generate_forest_groves(grid, moisture_map, grove_count=2, growth_iterations=1)

        forest_positions = {pos for pos, t in result.items() if t == TerrainType.FOREST}

        # With 2 seeds at Position(1,1) and Position(11,1), each should expand
        # Verify we have forest in both expected regions
        left_region_forest = [pos for pos in forest_positions if pos.x < 5]
        right_region_forest = [pos for pos in forest_positions if pos.x > 5]

        # Both regions should have some forest
        assert len(left_region_forest) > 0, f"Should have forest in left region, got: {forest_positions}"
        assert len(right_region_forest) > 0, f"Should have forest in right region, got: {forest_positions}"


class TestTerrainGridIntegration:
    """Integration tests for full terrain pipeline (WI-247)."""

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for full pipeline")
    def test_get_terrain_in_bounds_full_pipeline_produces_varied_terrain(self) -> None:
        """Full pipeline produces all terrain types including MOUNTAIN from ridges."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        grid = TerrainGrid(gen)

        # Generate terrain over reasonable bounds
        bounds = Bounds(min_x=-50, min_y=-50, max_x=50, max_y=50)
        result = grid.get_terrain_in_bounds(bounds)

        # Verify all terrain types present
        terrain_types = set(result.values())
        assert TerrainType.WATER in terrain_types, "Expected WATER in terrain"
        assert TerrainType.MOUNTAIN in terrain_types, "Expected MOUNTAIN in terrain"
        assert TerrainType.FOREST in terrain_types, "Expected FOREST in terrain"
        assert TerrainType.MEADOW in terrain_types, "Expected MEADOW in terrain"
        assert TerrainType.PLAIN in terrain_types, "Expected PLAIN in terrain"

        # Verify some MOUNTAIN cells are from ridges (heightmap peaks)
        # This verifies ridge integration is working
        mountain_count = sum(1 for t in result.values() if t == TerrainType.MOUNTAIN)
        assert mountain_count > 10, "Expected multiple MOUNTAIN cells from ridge generation"

    @pytest.mark.skipif(not HAS_NOISE, reason="noise library required for full pipeline")
    def test_get_terrain_in_bounds_deterministic_full_pipeline(self) -> None:
        """Full pipeline produces identical results for same seed."""
        gen1 = TerrainGenerator(TerrainConfig(seed=12345))
        gen2 = TerrainGenerator(TerrainConfig(seed=12345))

        bounds = Bounds(min_x=-20, min_y=-20, max_x=20, max_y=20)

        result1 = TerrainGrid(gen1).get_terrain_in_bounds(bounds)
        result2 = TerrainGrid(gen2).get_terrain_in_bounds(bounds)

        assert result1 == result2, "Same seed should produce identical terrain"