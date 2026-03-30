"""Kitty sprite system for loading, caching, and managing image sprites.

Provides SpriteHandle (frozen dataclass) and SpriteManager for loading
PNG sprites, caching them by (filename, size), and generating Kitty
graphics protocol escape sequences for upload and cleanup.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hamlet.gui.kitty.protocol import encode_delete_all, encode_image_upload

_SUPPORTED_SIZES = (16, 8)


def _snap_size(requested: int) -> int:
    """Snap to the largest supported size <= requested. Minimum is 8."""
    for size in _SUPPORTED_SIZES:
        if requested >= size:
            return size
    return _SUPPORTED_SIZES[-1]


@dataclass(frozen=True)
class SpriteHandle:
    """Immutable handle to a loaded sprite image.

    Attributes
    ----------
    image_id:
        Unique, monotonically increasing identifier.
    width:
        Image width in pixels.
    height:
        Image height in pixels.
    """

    image_id: int
    width: int
    height: int


class SpriteManager:
    """Manages sprite loading, caching, and Kitty protocol interactions.

    Parameters
    ----------
    assets_dir:
        Directory containing sprite PNG files. Defaults to an ``assets``
        subdirectory next to this module.
    """

    def __init__(self, assets_dir: Path | None = None) -> None:
        if assets_dir is None:
            assets_dir = Path(__file__).parent / "assets"
        self._assets_dir = assets_dir
        self._next_id: int = 1
        self._cache: dict[tuple[str, int], SpriteHandle] = {}
        self._png_data: dict[int, bytes] = {}
        self._uploaded_ids: set[int] = set()

    def load_sprite(self, filename: str, size: int) -> SpriteHandle | None:
        """Load a sprite from the assets directory.

        Returns a cached handle if the same (filename, size) was loaded
        before. Returns ``None`` if the file does not exist.

        Parameters
        ----------
        filename:
            PNG filename relative to the assets directory.
        size:
            Requested pixel size; snapped to the nearest supported size.
        """
        snapped = _snap_size(size)
        cache_key = (filename, snapped)

        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self._assets_dir / filename
        if not path.is_file():
            return None

        png_bytes = path.read_bytes()
        image_id = self._next_id
        self._next_id += 1

        handle = SpriteHandle(
            image_id=image_id,
            width=snapped,
            height=snapped,
        )
        self._cache[cache_key] = handle
        self._png_data[image_id] = png_bytes
        return handle

    def get_terrain_sprite(
        self, terrain_type: str, size: int = 16
    ) -> SpriteHandle | None:
        """Load a terrain sprite following the naming convention.

        Filename pattern: ``terrain_{type}_{size}.png``
        """
        snapped = _snap_size(size)
        filename = f"terrain_{terrain_type}_{snapped}.png"
        return self.load_sprite(filename, snapped)

    def get_structure_sprite(
        self, structure_type: str, stage: int, size: int = 16
    ) -> SpriteHandle | None:
        """Load a structure sprite following the naming convention.

        Filename pattern: ``structure_{type}_{stage}_{size}.png``
        """
        snapped = _snap_size(size)
        filename = f"structure_{structure_type}_{stage}_{snapped}.png"
        return self.load_sprite(filename, snapped)

    def get_agent_sprite(
        self, agent_type: str, frame: int, size: int = 16
    ) -> SpriteHandle | None:
        """Load an agent sprite following the naming convention.

        Filename pattern: ``agent_{type}_{frame}_{size}.png``
        """
        snapped = _snap_size(size)
        filename = f"agent_{agent_type}_{frame}_{snapped}.png"
        return self.load_sprite(filename, snapped)

    def is_uploaded(self, image_id: int) -> bool:
        """Check whether an image has been uploaded to the terminal."""
        return image_id in self._uploaded_ids

    def get_upload_sequence(self, handle: SpriteHandle) -> str:
        """Generate the Kitty escape sequence to upload a sprite.

        Looks up the raw PNG bytes and delegates to
        :func:`protocol.encode_image_upload`. Tracks the image as
        uploaded in an internal set.

        Parameters
        ----------
        handle:
            A :class:`SpriteHandle` previously returned by one of the
            load methods.

        Returns
        -------
        str
            One or more concatenated APC escape sequences.
            Returns an empty string if the handle is stale (image data
            was cleared by a prior ``cleanup()`` call).
        """
        if handle.image_id not in self._png_data:
            # Stale handle - cleanup() was called after this handle was created
            return ""
        data = self._png_data[handle.image_id]
        self._uploaded_ids.add(handle.image_id)
        return encode_image_upload(data, handle.image_id, handle.width, handle.height)

    def cleanup(self) -> str:
        """Delete all images from the terminal and clear internal caches.

        Existing :class:`SpriteHandle` objects held by callers are not
        mutated (they are frozen dataclasses).

        Returns
        -------
        str
            The APC escape sequence that deletes all images.
        """
        self._cache.clear()
        self._png_data.clear()
        self._uploaded_ids.clear()
        return encode_delete_all()
