"""Tests for KittyRenderer."""

from __future__ import annotations

import io
from pathlib import Path

from hamlet.gui.kitty.renderer import KittyRenderer, _RICH_TO_RGB
from hamlet.gui.kitty.sprites import SpriteHandle, SpriteManager
from hamlet.gui.kitty.zoom import ZoomLevel, get_zoom_config
from hamlet.gui.symbol_config import default_config
from hamlet.viewport.coordinates import Position as VPosition, Size
from hamlet.viewport.state import ViewportState
from hamlet.world_state.types import (
    Agent,
    AgentState,
    AgentType,
    Position,
    Structure,
    StructureType,
)


def _make_viewport(cols: int = 40, rows: int = 20) -> ViewportState:
    return ViewportState(
        center=VPosition(0, 0),
        size=Size(cols, rows),
    )


def _make_agent(
    agent_type: AgentType = AgentType.GENERAL,
    state: AgentState = AgentState.ACTIVE,
    x: int = 0,
    y: int = 0,
) -> Agent:
    return Agent(
        id="agent-1",
        session_id="sess-1",
        project_id="proj-1",
        village_id="vil-1",
        inferred_type=agent_type,
        position=Position(x, y),
        state=state,
    )


def _make_structure(
    struct_type: StructureType = StructureType.HOUSE,
    x: int = 0,
    y: int = 0,
    stage: int = 0,
    material: str = "wood",
) -> Structure:
    return Structure(
        id="struct-1",
        village_id="vil-1",
        type=struct_type,
        position=Position(x, y),
        stage=stage,
        material=material,
    )


class TestKittyRendererEmptyFrame:
    """Render with empty data should not crash."""

    def test_empty_render(self):
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=40, rows=20)
        vp = _make_viewport()

        renderer.render_frame(vp, agents=[], structures=[], terrain_data={}, event_log=[])

        result = output.getvalue()
        # Should contain clear sequence and status bar at minimum
        assert "\x1b[2J" in result
        assert "hamlet" in result

    def test_cleanup(self):
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=40, rows=20)
        renderer.cleanup()
        result = output.getvalue()
        # Should contain delete-all kitty sequence and reset
        assert "\x1b_Ga=d,d=a;\x1b\\" in result
        assert "\x1b[0m" in result


class TestRoadStructure:
    """ROAD structure renders without KeyError (Q-10 fix)."""

    def test_road_renders(self):
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=40, rows=20)
        vp = _make_viewport()
        road = _make_structure(struct_type=StructureType.ROAD, x=0, y=0)

        renderer.render_frame(vp, agents=[], structures=[road], terrain_data={}, event_log=[])

        result = output.getvalue()
        # ROAD symbol is "="
        assert "=" in result

    def test_all_structure_types_render(self):
        """Every StructureType renders without KeyError."""
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=80, rows=40)
        vp = _make_viewport(cols=80, rows=40)

        structures = [
            _make_structure(struct_type=st, x=i, y=0)
            for i, st in enumerate(StructureType)
        ]
        # Assign unique IDs
        for i, s in enumerate(structures):
            s.id = f"struct-{i}"

        renderer.render_frame(vp, agents=[], structures=structures, terrain_data={}, event_log=[])
        # No exception means success


class TestTerrainData:
    """Terrain data renders terrain symbols (Q-11 fix)."""

    def test_terrain_with_entries(self):
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=40, rows=20)
        vp = _make_viewport()

        terrain_data = {
            (0, 0): "water",
            (1, 0): "forest",
        }

        renderer.render_frame(vp, agents=[], structures=[], terrain_data=terrain_data, event_log=[])

        result = output.getvalue()
        config = default_config()
        # Water symbol should appear
        assert config.terrain.symbols["water"] in result
        # Forest symbol should appear
        assert config.terrain.symbols["forest"] in result

    def test_empty_terrain_data(self):
        """Empty terrain_data dict should not crash."""
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=40, rows=20)
        vp = _make_viewport()

        renderer.render_frame(vp, agents=[], structures=[], terrain_data={}, event_log=[])
        # No exception means success

    def test_terrain_with_dict_entries(self):
        """Terrain data as dict values with 'type' key."""
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=40, rows=20)
        vp = _make_viewport()

        terrain_data = {
            (0, 0): {"type": "mountain"},
        }

        renderer.render_frame(vp, agents=[], structures=[], terrain_data=terrain_data, event_log=[])

        result = output.getvalue()
        assert default_config().terrain.symbols["mountain"] in result


class TestZombieAgent:
    """Zombie agents use zombie_color."""

    def test_zombie_uses_zombie_color(self):
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=40, rows=20)
        vp = _make_viewport()

        zombie = _make_agent(state=AgentState.ZOMBIE, x=0, y=0)

        renderer.render_frame(vp, agents=[zombie], structures=[], terrain_data={}, event_log=[])

        result = output.getvalue()
        config = default_config()
        # zombie_color is "green" -> RGB (0, 255, 0)
        r, g, b = _RICH_TO_RGB[config.agent.zombie_color]
        expected_escape = f"\x1b[38;2;{r};{g};{b}m"
        assert expected_escape in result
        # Agent symbol should appear
        assert config.agent.symbol in result

    def test_active_agent_uses_type_color(self):
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=40, rows=20)
        vp = _make_viewport()

        agent = _make_agent(agent_type=AgentType.CODER, state=AgentState.ACTIVE, x=0, y=0)

        renderer.render_frame(vp, agents=[agent], structures=[], terrain_data={}, event_log=[])

        result = output.getvalue()
        config = default_config()
        r, g, b = _RICH_TO_RGB[config.agent.colors[AgentType.CODER]]
        expected_escape = f"\x1b[38;2;{r};{g};{b}m"
        assert expected_escape in result


class TestRichToRgb:
    """_RICH_TO_RGB has entries for all colors used in default_config()."""

    def test_all_agent_colors_present(self):
        config = default_config()
        for agent_type, color in config.agent.colors.items():
            assert color in _RICH_TO_RGB, f"Missing color {color!r} for {agent_type}"
        assert config.agent.zombie_color in _RICH_TO_RGB

    def test_all_terrain_colors_present(self):
        config = default_config()
        for terrain_type, color in config.terrain.colors.items():
            assert color in _RICH_TO_RGB, f"Missing color {color!r} for terrain {terrain_type}"

    def test_all_material_colors_present(self):
        config = default_config()
        for material, color in config.structure.material_colors.items():
            assert color in _RICH_TO_RGB, f"Missing color {color!r} for material {material}"

    def test_has_13_entries(self):
        assert len(_RICH_TO_RGB) == 13


class TestHud:
    """Status bar and event log rendering."""

    def test_status_bar_on_row_0(self):
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=40, rows=20)
        vp = _make_viewport()

        renderer.render_frame(vp, agents=[], structures=[], terrain_data={}, event_log=[])

        result = output.getvalue()
        # Row 0 -> terminal row 1, col 1: \x1b[1;1H
        assert "\x1b[1;1H" in result
        assert "hamlet" in result

    def test_event_log_bottom_rows(self):
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=40, rows=20)
        vp = _make_viewport()

        events = ["event one", "event two", "event three"]
        renderer.render_frame(vp, agents=[], structures=[], terrain_data={}, event_log=events)

        result = output.getvalue()
        assert "event one" in result
        assert "event two" in result
        assert "event three" in result


class TestZoomLevels:
    """Zoom level setting works."""

    def test_set_zoom(self):
        output = io.StringIO()
        renderer = KittyRenderer(output=output, cols=40, rows=20)

        renderer.set_zoom(ZoomLevel.CLOSE)
        assert renderer._zoom_level == ZoomLevel.CLOSE
        assert renderer._zoom_config.render_mode == "sprite"

        renderer.set_zoom(ZoomLevel.FAR)
        assert renderer._zoom_level == ZoomLevel.FAR
        assert renderer._zoom_config.render_mode == "character"


class TestSpriteRendering:
    """Sprite path produces Kitty graphics display sequences with pixel coords."""

    def test_terrain_sprite_blitted_with_pixel_coords(self):
        sprite_mgr = SpriteManager(assets_dir=Path("/nonexistent"))
        # Manually inject a cached handle and mark it uploaded
        handle = SpriteHandle(image_id=42, width=16, height=16)
        sprite_mgr._cache[("terrain_water_16.png", 16)] = handle
        sprite_mgr._uploaded_ids.add(42)

        assert sprite_mgr.is_uploaded(42)

        output = io.StringIO()
        renderer = KittyRenderer(
            output=output, cols=40, rows=20, sprite_manager=sprite_mgr
        )
        renderer.set_zoom(ZoomLevel.CLOSE)

        vp = _make_viewport()
        terrain_data = {(0, 0): "water"}

        renderer.render_frame(
            vp, agents=[], structures=[], terrain_data=terrain_data, event_log=[]
        )

        result = output.getvalue()
        # Should contain a Kitty display action
        assert "\x1b_Ga=p" in result

        # The world coord (0,0) maps to screen center (20, 10).
        # Pixel offsets should be 20*16=320, 10*16=160
        zoom_cfg = get_zoom_config(ZoomLevel.CLOSE)
        expected_px = 20 * zoom_cfg.tile_pixels
        expected_py = 10 * zoom_cfg.tile_pixels
        assert f"X={expected_px}" in result
        assert f"Y={expected_py}" in result
