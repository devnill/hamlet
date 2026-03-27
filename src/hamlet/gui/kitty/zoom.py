from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum


class ZoomLevel(IntEnum):
    CLOSE = 0
    MEDIUM = 1
    FAR = 2


@dataclass(frozen=True)
class ZoomConfig:
    level: ZoomLevel
    tile_pixels: int
    render_mode: str  # "sprite" or "character"


_ZOOM_CONFIGS = {
    ZoomLevel.CLOSE: ZoomConfig(ZoomLevel.CLOSE, 16, "sprite"),
    ZoomLevel.MEDIUM: ZoomConfig(ZoomLevel.MEDIUM, 8, "sprite"),
    ZoomLevel.FAR: ZoomConfig(ZoomLevel.FAR, 1, "character"),
}

_NUM_LEVELS = len(ZoomLevel)


def get_zoom_config(level: ZoomLevel) -> ZoomConfig:
    return _ZOOM_CONFIGS[level]


def next_zoom(level: ZoomLevel) -> ZoomLevel:
    return ZoomLevel((int(level) + 1) % _NUM_LEVELS)


def prev_zoom(level: ZoomLevel) -> ZoomLevel:
    return ZoomLevel((int(level) - 1) % _NUM_LEVELS)


__all__ = ["ZoomLevel", "ZoomConfig", "get_zoom_config", "next_zoom", "prev_zoom"]
