"""Kitty graphics protocol escape sequence encoding.

Implements the Kitty terminal graphics protocol for image upload,
display, and deletion via APC escape sequences.

Kitty APC format: \\x1b_G<key>=<value>,<key>=<value>;<payload>\\x1b\\\\
"""

from __future__ import annotations

import base64
import os

_CHUNK_SIZE = 4096


def detect_kitty_support() -> bool:
    """Check whether the terminal supports Kitty graphics protocol.

    Returns True when the KITTY_WINDOW_ID environment variable is set
    and non-empty. Does NOT use escape-sequence queries (fragile in
    non-interactive / test contexts).
    """
    val = os.environ.get("KITTY_WINDOW_ID", "")
    return bool(val)


def encode_image_upload(
    image_data: bytes,
    image_id: int,
    width: int,
    height: int,
) -> str:
    """Generate Kitty APC escape sequence(s) to transmit a PNG image.

    The base64-encoded payload is chunked into 4096-byte segments.
    The first chunk carries the full header; continuation chunks carry
    only the ``m`` (more-data) flag.

    Parameters
    ----------
    image_data:
        Raw PNG bytes to transmit.
    image_id:
        Unsigned 32-bit image identifier.
    width:
        Image width in pixels.
    height:
        Image height in pixels.

    Returns
    -------
    str
        One or more concatenated APC escape sequences.
    """
    b64 = base64.standard_b64encode(image_data).decode("ascii")
    chunks = [b64[i : i + _CHUNK_SIZE] for i in range(0, len(b64), _CHUNK_SIZE)]
    if not chunks:
        chunks = [""]

    parts: list[str] = []
    for idx, chunk in enumerate(chunks):
        is_last = idx == len(chunks) - 1
        if idx == 0:
            header = (
                f"a=t,f=100,i={image_id},s={width},v={height},"
                f"m={'0' if is_last else '1'}"
            )
        else:
            header = f"m={'0' if is_last else '1'}"
        parts.append(f"\x1b_G{header};{chunk}\x1b\\")
    return "".join(parts)


def encode_image_display(
    image_id: int,
    x: int,
    y: int,
    z_index: int = 0,
) -> str:
    """Generate Kitty APC escape sequence to display a previously uploaded image.

    Parameters
    ----------
    image_id:
        The image identifier used during upload.
    x:
        Horizontal pixel offset for placement.
    y:
        Vertical pixel offset for placement.
    z_index:
        Stacking order (default 0).

    Returns
    -------
    str
        A single APC escape sequence.
    """
    return f"\x1b_Ga=p,i={image_id},p=1,X={x},Y={y},z={z_index};\x1b\\"


def encode_image_delete(image_id: int) -> str:
    """Generate Kitty APC escape sequence to delete a specific image.

    Parameters
    ----------
    image_id:
        The image identifier to delete.

    Returns
    -------
    str
        A single APC escape sequence.
    """
    return f"\x1b_Ga=d,d=i,i={image_id};\x1b\\"


def encode_delete_all() -> str:
    """Generate Kitty APC escape sequence to delete all images.

    Returns
    -------
    str
        A single APC escape sequence.
    """
    return "\x1b_Ga=d,d=a;\x1b\\"
