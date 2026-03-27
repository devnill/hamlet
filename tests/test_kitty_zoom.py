from hamlet.gui.kitty.zoom import ZoomLevel, ZoomConfig, get_zoom_config, next_zoom, prev_zoom


def test_next_zoom_close_to_medium():
    assert next_zoom(ZoomLevel.CLOSE) == ZoomLevel.MEDIUM


def test_next_zoom_medium_to_far():
    assert next_zoom(ZoomLevel.MEDIUM) == ZoomLevel.FAR


def test_next_zoom_far_wraps_to_close():
    assert next_zoom(ZoomLevel.FAR) == ZoomLevel.CLOSE


def test_prev_zoom_far_to_medium():
    assert prev_zoom(ZoomLevel.FAR) == ZoomLevel.MEDIUM


def test_prev_zoom_medium_to_close():
    assert prev_zoom(ZoomLevel.MEDIUM) == ZoomLevel.CLOSE


def test_prev_zoom_close_wraps_to_far():
    assert prev_zoom(ZoomLevel.CLOSE) == ZoomLevel.FAR


def test_get_zoom_config_close_tile_pixels():
    config = get_zoom_config(ZoomLevel.CLOSE)
    assert config.tile_pixels == 16


def test_get_zoom_config_medium_tile_pixels():
    config = get_zoom_config(ZoomLevel.MEDIUM)
    assert config.tile_pixels == 8


def test_get_zoom_config_far_tile_pixels():
    config = get_zoom_config(ZoomLevel.FAR)
    assert config.tile_pixels == 1


def test_get_zoom_config_close_render_mode():
    config = get_zoom_config(ZoomLevel.CLOSE)
    assert config.render_mode == "sprite"


def test_get_zoom_config_medium_render_mode():
    config = get_zoom_config(ZoomLevel.MEDIUM)
    assert config.render_mode == "sprite"


def test_get_zoom_config_far_render_mode():
    config = get_zoom_config(ZoomLevel.FAR)
    assert config.render_mode == "character"


def test_get_zoom_config_returns_zoom_config_instance():
    config = get_zoom_config(ZoomLevel.CLOSE)
    assert isinstance(config, ZoomConfig)


def test_zoom_config_is_frozen():
    config = get_zoom_config(ZoomLevel.CLOSE)
    try:
        config.tile_pixels = 99  # type: ignore[misc]
        assert False, "Expected FrozenInstanceError"
    except Exception:
        pass


def test_zoom_config_level_field():
    config = get_zoom_config(ZoomLevel.MEDIUM)
    assert config.level == ZoomLevel.MEDIUM
