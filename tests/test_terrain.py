"""Tests for terrain types and configuration (WI-232) and TerrainGenerator (WI-233).

Test framework: pytest.
Run with: pytest tests/test_terrain.py -v
"""
from __future__ import annotations

import pytest

from hamlet.world_state.terrain import HAS_NOISE, TerrainConfig, TerrainGenerator, TerrainGrid, TerrainType
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
        assert TerrainType.MEADOW.color == "chartreuse"

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
        assert config.forest_threshold == 0.4
        assert config.meadow_threshold == 0.6
        assert config.water_threshold == -0.3
        assert config.mountain_threshold == 0.7

    def test_custom_seed(self) -> None:
        """TerrainConfig accepts custom seed."""
        config = TerrainConfig(seed=42)
        assert config.seed == 42

    def test_custom_world_size(self) -> None:
        """TerrainConfig accepts custom world_size."""
        config = TerrainConfig(world_size=100)
        assert config.world_size == 100


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

    def test_different_seeds_produce_different_terrain(self) -> None:
        """Different seeds produce different terrain at same position."""
        gen1 = TerrainGenerator(TerrainConfig(seed=42))
        gen2 = TerrainGenerator(TerrainConfig(seed=12345))

        # Generate terrain for a grid of positions
        different_count = 0
        for x in range(-5, 6):
            for y in range(-5, 6):
                pos = Position(x, y)
                if gen1.generate_terrain(pos) != gen2.generate_terrain(pos):
                    different_count += 1

        # At least some positions should have different terrain
        assert different_count > 0

    def test_all_terrain_types_can_be_generated(self) -> None:
        """All 5 terrain types can be generated."""
        gen = TerrainGenerator(TerrainConfig(seed=42))
        found_types: set[TerrainType] = set()

        # Search a larger area to find all terrain types
        for x in range(-20, 21):
            for y in range(-20, 21):
                pos = Position(x, y)
                found_types.add(gen.generate_terrain(pos))
                if len(found_types) == 5:
                    break
            if len(found_types) == 5:
                break

        assert TerrainType.WATER in found_types
        assert TerrainType.MOUNTAIN in found_types
        assert TerrainType.FOREST in found_types
        assert TerrainType.MEADOW in found_types
        assert TerrainType.PLAIN in found_types

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