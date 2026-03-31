"""Doctor command — diagnose renderer and hook configuration."""
from __future__ import annotations

import glob
import os
import re
import urllib.error
import urllib.request
from argparse import Namespace
from pathlib import Path

_VERSION_RE = re.compile(r"""^HOOK_VERSION\s*=\s*['"]([^'"]+)['"]""")


def _extract_hook_version(path: Path) -> str | None:
    """Extract HOOK_VERSION from a hamlet_hook_utils.py file."""
    for line in path.read_text().splitlines():
        m = _VERSION_RE.match(line)
        if m:
            return m.group(1)
    return None


def _find_hook_utils() -> Path | None:
    """Locate installed hamlet_hook_utils.py — plugin cache or package hooks dir."""
    # Try marketplace plugin cache first (sort by mtime for correct ordering)
    cache_pattern = os.path.expanduser(
        "~/.claude/plugins/cache/marketplace/hamlet/*/hooks/hamlet_hook_utils.py"
    )
    matches = glob.glob(cache_pattern)
    if matches:
        return Path(sorted(matches, key=os.path.getmtime)[-1])

    # Fallback: package's own hooks directory (hamlet install path)
    try:
        from hamlet.cli.commands.install import get_hooks_dir
        hooks_dir = get_hooks_dir()
        candidate = hooks_dir / "hamlet_hook_utils.py"
        if candidate.exists():
            return candidate
    except Exception:
        pass

    return None


def _check_hook_version() -> tuple[bool, str]:
    """Check if installed hooks match the current package version.

    Returns:
        Tuple of (success, message).
    """
    try:
        from hamlet import __version__ as package_version
    except ImportError:
        return False, "Could not determine package version"

    hook_utils_path = _find_hook_utils()
    if hook_utils_path is None:
        return False, "No installed hooks found in plugin cache or package hooks directory"

    try:
        hook_version = _extract_hook_version(hook_utils_path)

        if hook_version is None:
            return False, (
                f"Installed hooks at {hook_utils_path.parent} have no HOOK_VERSION. "
                "Update the plugin to get versioned hooks."
            )

        if hook_version == package_version:
            return True, f"Hook version {hook_version} matches package version"

        return False, (
            f"Hook version {hook_version} != package version {package_version}. "
            "Hooks are stale."
        )
    except Exception as e:
        return False, f"Could not read installed hooks: {e}"


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

    # --- Hook checks ---
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

        print()
        print("Hook version check")
        print("-" * 40)
        success, message = _check_hook_version()
        if success:
            print(f"PASS: {message}")
        else:
            print(f"FAIL: {message}")
            print("To fix:")
            print("  1. Update the hamlet plugin in Claude Code (Extensions > Marketplace)")
            print("  2. Or reinstall hooks: pipx install --force hamlet && hamlet install")

    return 0
