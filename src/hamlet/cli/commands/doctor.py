"""Doctor command — diagnose renderer and hook configuration."""
from __future__ import annotations

import os
import urllib.error
import urllib.request
from argparse import Namespace


def _check_hook_connectivity() -> tuple[bool, str]:
    """Check if hook scripts can reach the daemon's health endpoint.

    Returns:
        Tuple of (success, message).
    """
    try:
        from hamlet.config.settings import Settings
        settings = Settings.load()
        port = settings.mcp_port
    except Exception:
        port = 8080

    health_url = f"http://localhost:{port}/hamlet/health"
    try:
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                return True, f"Daemon is running on port {port}"
            return False, f"Daemon returned status {response.status}"
    except urllib.error.URLError as e:
        return False, f"Daemon not running (could not connect to port {port})"
    except Exception as e:
        return False, f"Connection error: {e}"


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

    # --- Hook connectivity check ---
    if getattr(args, "check_hooks", False):
        print()
        print("Hook connectivity check")
        print("-" * 40)
        success, message = _check_hook_connectivity()
        if success:
            print(f"PASS: {message}")
            print("Hooks can send events to the daemon.")
        else:
            print(f"FAIL: {message}")
            print("To fix:")
            print("  1. Start the daemon: hamlet daemon")
            print("  2. Or check if the port is correct in ~/.hamlet/config.json")
            print("  3. Verify no firewall is blocking localhost connections")

    return 0
