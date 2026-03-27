"""Doctor command — diagnose renderer configuration."""
from __future__ import annotations

import os
from argparse import Namespace


def doctor_command(args: Namespace) -> int:
    """Print terminal info and recommended renderer."""

    print("hamlet doctor — environment diagnostic")
    print("=" * 40)

    # --- Kitty graphics protocol support ---
    try:
        from hamlet.gui.kitty import KITTY_AVAILABLE
    except Exception as exc:
        print(f"Kitty protocol: ERROR ({exc})")
        KITTY_AVAILABLE = False
    else:
        status = "available" if KITTY_AVAILABLE else "not available"
        print(f"Kitty protocol: {status}")

    # --- KITTY_WINDOW_ID ---
    kwid = os.environ.get("KITTY_WINDOW_ID", "(not set)")
    print(f"KITTY_WINDOW_ID: {kwid}")

    # --- Terminal type ---
    term = os.environ.get("TERM", "(not set)")
    print(f"TERM: {term}")

    # --- tmux detection ---
    tmux_val = os.environ.get("TMUX", "")
    if tmux_val:
        print("tmux: detected")
        print("WARNING: Kitty graphics protocol may not work inside tmux.")
    else:
        print("tmux: not detected")

    # --- Recommended renderer ---
    try:
        from hamlet.gui.detect import detect_renderer
        recommended = detect_renderer()
    except Exception as exc:
        recommended = f"unknown ({exc})"
    print(f"Recommended renderer: {recommended}")

    return 0
