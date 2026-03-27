"""Tests for the Kitty graphics protocol layer."""

from __future__ import annotations

import base64
import os
from unittest.mock import patch

from hamlet.gui.kitty.protocol import (
    detect_kitty_support,
    encode_delete_all,
    encode_image_delete,
    encode_image_display,
    encode_image_upload,
)


# ---------------------------------------------------------------------------
# detect_kitty_support
# ---------------------------------------------------------------------------


class TestDetectKittySupport:
    def test_returns_true_when_env_var_set(self):
        with patch.dict(os.environ, {"KITTY_WINDOW_ID": "1"}):
            assert detect_kitty_support() is True

    def test_returns_false_when_env_var_missing(self):
        env = os.environ.copy()
        env.pop("KITTY_WINDOW_ID", None)
        with patch.dict(os.environ, env, clear=True):
            assert detect_kitty_support() is False

    def test_returns_false_when_env_var_empty(self):
        with patch.dict(os.environ, {"KITTY_WINDOW_ID": ""}):
            assert detect_kitty_support() is False


# ---------------------------------------------------------------------------
# encode_image_upload
# ---------------------------------------------------------------------------


class TestEncodeImageUpload:
    def test_small_image_single_chunk(self):
        """A payload that fits in one chunk produces a single APC sequence."""
        data = b"\x89PNG\r\n\x1a\ntest"
        result = encode_image_upload(data, image_id=1, width=16, height=16)

        b64 = base64.standard_b64encode(data).decode("ascii")
        expected = f"\x1b_Ga=t,f=100,i=1,s=16,v=16,m=0;{b64}\x1b\\"
        assert result == expected

    def test_return_type_is_str(self):
        result = encode_image_upload(b"x", image_id=1, width=1, height=1)
        assert isinstance(result, str)

    def test_empty_payload(self):
        result = encode_image_upload(b"", image_id=5, width=0, height=0)
        expected = "\x1b_Ga=t,f=100,i=5,s=0,v=0,m=0;\x1b\\"
        assert result == expected

    def test_chunking_large_payload(self):
        """Payload exceeding 4096 base64 bytes is split into multiple chunks."""
        # 4096 base64 chars encode 3072 raw bytes; use more than that
        raw = bytes(range(256)) * 15  # 3840 bytes -> >4096 b64 chars
        b64 = base64.standard_b64encode(raw).decode("ascii")
        assert len(b64) > 4096, "test precondition: b64 must exceed chunk size"

        result = encode_image_upload(raw, image_id=42, width=64, height=64)

        # Split expected chunks
        chunks = [b64[i : i + 4096] for i in range(0, len(b64), 4096)]
        assert len(chunks) >= 2

        # Build expected output
        parts = []
        for idx, chunk in enumerate(chunks):
            is_last = idx == len(chunks) - 1
            if idx == 0:
                header = f"a=t,f=100,i=42,s=64,v=64,m={'0' if is_last else '1'}"
            else:
                header = f"m={'0' if is_last else '1'}"
            parts.append(f"\x1b_G{header};{chunk}\x1b\\")
        expected = "".join(parts)
        assert result == expected

    def test_first_chunk_has_full_header(self):
        raw = bytes(range(256)) * 15
        result = encode_image_upload(raw, image_id=7, width=32, height=32)
        # First APC must contain the full header keys
        first_seq = result.split("\x1b\\")[0] + "\x1b\\"
        assert "a=t" in first_seq
        assert "f=100" in first_seq
        assert "i=7" in first_seq
        assert "s=32" in first_seq
        assert "v=32" in first_seq

    def test_continuation_chunks_have_only_m_flag(self):
        raw = bytes(range(256)) * 15
        result = encode_image_upload(raw, image_id=7, width=32, height=32)
        sequences = result.split("\x1b\\")
        # sequences[-1] is empty after final split
        # Second sequence onward should only have m= in header
        for seq in sequences[1:-1]:
            # Each starts with \x1b_G
            header_part = seq.split(";")[0]
            # Remove the \x1b_G prefix
            header = header_part.replace("\x1b_G", "")
            assert header.startswith("m=")
            # Should not contain other keys
            assert "a=" not in header
            assert "f=" not in header
            assert "i=" not in header

    def test_last_chunk_m_is_zero(self):
        raw = bytes(range(256)) * 15
        result = encode_image_upload(raw, image_id=1, width=1, height=1)
        # The last non-empty sequence should have m=0
        sequences = [s for s in result.split("\x1b\\") if s]
        last = sequences[-1]
        header = last.split(";")[0]
        assert "m=0" in header


# ---------------------------------------------------------------------------
# encode_image_display
# ---------------------------------------------------------------------------


class TestEncodeImageDisplay:
    def test_basic_display(self):
        result = encode_image_display(image_id=1, x=10, y=20, z_index=0)
        expected = "\x1b_Ga=p,i=1,p=1,X=10,Y=20,z=0;\x1b\\"
        assert result == expected

    def test_return_type_is_str(self):
        assert isinstance(encode_image_display(1, 0, 0), str)

    def test_custom_z_index(self):
        result = encode_image_display(image_id=99, x=5, y=3, z_index=-1)
        expected = "\x1b_Ga=p,i=99,p=1,X=5,Y=3,z=-1;\x1b\\"
        assert result == expected

    def test_default_z_index(self):
        result = encode_image_display(image_id=1, x=0, y=0)
        assert "z=0" in result


# ---------------------------------------------------------------------------
# encode_image_delete
# ---------------------------------------------------------------------------


class TestEncodeImageDelete:
    def test_delete_specific_image(self):
        result = encode_image_delete(image_id=42)
        expected = "\x1b_Ga=d,d=i,i=42;\x1b\\"
        assert result == expected

    def test_return_type_is_str(self):
        assert isinstance(encode_image_delete(1), str)


# ---------------------------------------------------------------------------
# encode_delete_all
# ---------------------------------------------------------------------------


class TestEncodeDeleteAll:
    def test_delete_all(self):
        result = encode_delete_all()
        expected = "\x1b_Ga=d,d=a;\x1b\\"
        assert result == expected

    def test_return_type_is_str(self):
        assert isinstance(encode_delete_all(), str)


# ---------------------------------------------------------------------------
# KITTY_AVAILABLE flag
# ---------------------------------------------------------------------------


class TestKittyAvailableFlag:
    def test_flag_is_bool(self):
        from hamlet.gui.kitty import KITTY_AVAILABLE

        assert isinstance(KITTY_AVAILABLE, bool)
