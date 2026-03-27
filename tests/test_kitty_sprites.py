"""Tests for hamlet.gui.kitty.sprites module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from hamlet.gui.kitty.sprites import SpriteHandle, SpriteManager, _snap_size


# --- SpriteHandle ---


def test_sprite_handle_is_frozen():
    handle = SpriteHandle(image_id=1, width=16, height=16)
    try:
        handle.width = 32  # type: ignore[misc]
        raise AssertionError("Expected FrozenInstanceError")
    except AttributeError:
        pass


def test_sprite_handle_fields():
    handle = SpriteHandle(image_id=42, width=16, height=16)
    assert handle.image_id == 42
    assert handle.width == 16
    assert handle.height == 16


# --- Size snapping ---


def test_snap_size_exact():
    assert _snap_size(16) == 16
    assert _snap_size(8) == 8


def test_snap_size_larger_than_max():
    assert _snap_size(32) == 16


def test_snap_size_between():
    assert _snap_size(12) == 8


def test_snap_size_below_minimum():
    assert _snap_size(4) == 8
    assert _snap_size(1) == 8


# --- SpriteManager.load_sprite ---


def test_load_sprite_returns_none_for_missing_file(tmp_path: Path):
    mgr = SpriteManager(assets_dir=tmp_path)
    result = mgr.load_sprite("nonexistent.png", 16)
    assert result is None


def test_load_sprite_returns_handle(tmp_path: Path):
    png_file = tmp_path / "test.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    mgr = SpriteManager(assets_dir=tmp_path)
    handle = mgr.load_sprite("test.png", 16)

    assert handle is not None
    assert handle.image_id == 1
    assert handle.width == 16
    assert handle.height == 16


def test_load_sprite_cache_hit(tmp_path: Path):
    png_file = tmp_path / "test.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    mgr = SpriteManager(assets_dir=tmp_path)
    h1 = mgr.load_sprite("test.png", 16)
    h2 = mgr.load_sprite("test.png", 16)

    assert h1 is h2  # exact same object


def test_next_id_increments_for_distinct_sprites(tmp_path: Path):
    (tmp_path / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "b.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    mgr = SpriteManager(assets_dir=tmp_path)
    h1 = mgr.load_sprite("a.png", 16)
    h2 = mgr.load_sprite("b.png", 16)

    assert h1 is not None
    assert h2 is not None
    assert h1.image_id == 1
    assert h2.image_id == 2


def test_next_id_increments_same_file_different_size(tmp_path: Path):
    (tmp_path / "test.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    mgr = SpriteManager(assets_dir=tmp_path)
    h1 = mgr.load_sprite("test.png", 16)
    h2 = mgr.load_sprite("test.png", 8)

    assert h1 is not None
    assert h2 is not None
    assert h1.image_id == 1
    assert h2.image_id == 2
    assert h1.width == 16
    assert h2.width == 8


def test_load_sprite_size_snapping(tmp_path: Path):
    (tmp_path / "test.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    mgr = SpriteManager(assets_dir=tmp_path)
    # Requesting size 32 should snap to 16
    handle = mgr.load_sprite("test.png", 32)
    assert handle is not None
    assert handle.width == 16

    # Requesting size 12 should snap to 8
    handle2 = mgr.load_sprite("test.png", 12)
    assert handle2 is not None
    assert handle2.width == 8


# --- Terrain / Structure / Agent sprites ---


def test_get_terrain_sprite_returns_none_when_missing(tmp_path: Path):
    mgr = SpriteManager(assets_dir=tmp_path)
    assert mgr.get_terrain_sprite("forest") is None


def test_get_terrain_sprite_naming(tmp_path: Path):
    (tmp_path / "terrain_forest_16.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    mgr = SpriteManager(assets_dir=tmp_path)
    handle = mgr.get_terrain_sprite("forest", size=16)
    assert handle is not None
    assert handle.image_id == 1


def test_get_structure_sprite_returns_none_when_missing(tmp_path: Path):
    mgr = SpriteManager(assets_dir=tmp_path)
    assert mgr.get_structure_sprite("house", stage=3) is None


def test_get_structure_sprite_naming(tmp_path: Path):
    (tmp_path / "structure_house_3_16.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    mgr = SpriteManager(assets_dir=tmp_path)
    handle = mgr.get_structure_sprite("house", stage=3, size=16)
    assert handle is not None


def test_get_agent_sprite_returns_none_when_missing(tmp_path: Path):
    mgr = SpriteManager(assets_dir=tmp_path)
    assert mgr.get_agent_sprite("coder", frame=0) is None


def test_get_agent_sprite_naming(tmp_path: Path):
    (tmp_path / "agent_coder_0_16.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    mgr = SpriteManager(assets_dir=tmp_path)
    handle = mgr.get_agent_sprite("coder", frame=0, size=16)
    assert handle is not None


# --- get_upload_sequence ---


def test_get_upload_sequence_calls_protocol(tmp_path: Path):
    (tmp_path / "test.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    mgr = SpriteManager(assets_dir=tmp_path)
    handle = mgr.load_sprite("test.png", 16)
    assert handle is not None

    with patch(
        "hamlet.gui.kitty.sprites.encode_image_upload",
        return_value="<escape>",
    ) as mock_upload:
        result = mgr.get_upload_sequence(handle)

    assert result == "<escape>"
    mock_upload.assert_called_once_with(
        b"\x89PNG\r\n\x1a\n", handle.image_id, 16, 16
    )


def test_get_upload_sequence_tracks_uploaded(tmp_path: Path):
    (tmp_path / "test.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    mgr = SpriteManager(assets_dir=tmp_path)
    handle = mgr.load_sprite("test.png", 16)
    assert handle is not None

    with patch("hamlet.gui.kitty.sprites.encode_image_upload", return_value=""):
        mgr.get_upload_sequence(handle)

    assert handle.image_id in mgr._uploaded_ids


# --- cleanup ---


def test_cleanup_returns_delete_all_sequence(tmp_path: Path):
    mgr = SpriteManager(assets_dir=tmp_path)

    with patch(
        "hamlet.gui.kitty.sprites.encode_delete_all",
        return_value="<delete_all>",
    ) as mock_del:
        result = mgr.cleanup()

    assert result == "<delete_all>"
    mock_del.assert_called_once()


def test_cleanup_clears_caches(tmp_path: Path):
    (tmp_path / "test.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    mgr = SpriteManager(assets_dir=tmp_path)
    mgr.load_sprite("test.png", 16)

    assert len(mgr._cache) == 1
    assert len(mgr._png_data) == 1

    with patch("hamlet.gui.kitty.sprites.encode_delete_all", return_value=""):
        mgr.cleanup()

    assert len(mgr._cache) == 0
    assert len(mgr._png_data) == 0
    assert len(mgr._uploaded_ids) == 0
