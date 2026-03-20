"""Install command for configuring Hamlet hooks in Claude Code settings."""
from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from typing import Any


# Default Claude Code settings paths
DEFAULT_CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

# Hook scripts that need to be configured
HOOK_SCRIPTS = {
    "PreToolUse": "pre_tool_use.py",
    "PostToolUse": "post_tool_use.py",
    "Notification": "notification.py",
    "Stop": "stop.py",
}


def get_settings_path(args: Namespace) -> Path:
    """Get the Claude Code settings.json path.

    Priority:
    1. Command-line argument (--settings-path)
    2. CLAUDE_SETTINGS_PATH environment variable
    3. Default path (~/.claude/settings.json)

    Args:
        args: Parsed command-line arguments.

    Returns:
        Path to the settings.json file.
    """
    if args.settings_path:
        return Path(args.settings_path).expanduser().resolve()

    env_path = os.environ.get("CLAUDE_SETTINGS_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    return DEFAULT_CLAUDE_SETTINGS_PATH


def get_hooks_dir() -> Path | None:
    """Get the path to the Hamlet hooks directory.

    Returns:
        Path to the hooks directory, or None if not found.
    """
    # Try to find hooks relative to this file
    # src/hamlet/cli/commands/install.py -> hooks/
    # .parent x5: commands/ -> cli/ -> hamlet/ -> src/ -> project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    if project_root.name == "hamlet" and (project_root / "hooks").exists():
        return (project_root / "hooks").resolve()

    # Try relative to package installation
    try:
        import hamlet
        pkg_dir = Path(hamlet.__file__).parent.parent.parent
        hooks_dir = pkg_dir / "hooks"
        if hooks_dir.exists():
            return hooks_dir.resolve()
    except (ImportError, AttributeError):
        pass

    return None


def validate_mcp_server_running() -> tuple[bool, str]:
    """Check if the Hamlet MCP server is running.

    Returns:
        Tuple of (is_running, message).
    """
    try:
        from hamlet.config.settings import Settings
        settings = Settings.load()
        health_url = f"http://localhost:{settings.mcp_port}/hamlet/health"
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "Could not load Hamlet settings; falling back to default port 8080 for MCP server health check."
        )
        health_url = "http://localhost:8080/hamlet/health"  # fallback
    try:
        req = urllib.request.Request(
            health_url,
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                return True, "MCP server is running"
            return False, f"MCP server returned status {response.status}"
    except urllib.error.URLError as e:
        return False, f"MCP server not reachable: {e.reason}"
    except Exception as e:
        return False, f"Could not connect to MCP server: {e}"


def load_settings(settings_path: Path) -> dict[str, Any]:
    """Load settings from the Claude Code settings.json file.

    Args:
        settings_path: Path to the settings file.

    Returns:
        Dictionary containing the settings, or empty dict if file doesn't exist.

    Raises:
        SystemExit: If the file exists but contains invalid JSON.
    """
    if not settings_path.exists():
        return {}

    try:
        content = settings_path.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError as e:
        backup_suggestion = settings_path.with_suffix(".json.backup")
        print(
            f"Error: Claude Code settings.json is corrupted.",
            file=sys.stderr
        )
        print(
            f"       JSON parse error: {e}",
            file=sys.stderr
        )
        print(
            f"       Fix the file or delete it and try again.",
            file=sys.stderr
        )
        print(
            f"       A backup may exist at: {backup_suggestion}",
            file=sys.stderr
        )
        sys.exit(1)


def save_settings(settings_path: Path, settings: dict[str, Any]) -> None:
    """Save settings to the Claude Code settings.json file.

    Args:
        settings_path: Path to the settings file.
        settings: Dictionary containing the settings.

    Raises:
        SystemExit: If the file cannot be written.
    """
    try:
        # Ensure parent directory exists
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Write with proper formatting
        content = json.dumps(settings, indent=2, sort_keys=True)
        settings_path.write_text(content + "\n", encoding="utf-8")
    except PermissionError:
        print(
            f"Error: Permission denied writing to {settings_path}",
            file=sys.stderr
        )
        sys.exit(1)
    except OSError as e:
        print(
            f"Error: Could not write settings to {settings_path}: {e}",
            file=sys.stderr
        )
        sys.exit(1)


def create_backup(settings_path: Path, settings: dict[str, Any]) -> Path | None:
    """Create a backup of the existing settings file.

    Args:
        settings_path: Path to the settings file.
        settings: Current settings dictionary.

    Returns:
        Path to the backup file, or None if no backup was created.
    """
    if not settings:
        return None

    # Create backup with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = settings_path.with_suffix(f".backup.{timestamp}.json")

    try:
        shutil.copy2(settings_path, backup_path)
        return backup_path
    except Exception:
        # If copy fails, try writing the parsed content
        try:
            backup_path.write_text(
                json.dumps(settings, indent=2, sort_keys=True) + "\n",
                encoding="utf-8"
            )
            return backup_path
        except Exception:
            return None


def get_hook_paths(hooks_dir: Path) -> dict[str, str]:
    """Get absolute paths to all hook scripts.

    Args:
        hooks_dir: Path to the hooks directory.

    Returns:
        Dictionary mapping hook names to absolute paths.
    """
    return {
        hook_name: str(hooks_dir / filename)
        for hook_name, filename in HOOK_SCRIPTS.items()
    }


def install_hooks_to_settings(
    settings: dict[str, Any],
    hook_paths: dict[str, str]
) -> dict[str, Any]:
    """Add Hamlet hooks to the settings dictionary.

    Args:
        settings: Current settings dictionary.
        hook_paths: Dictionary mapping hook names to paths.

    Returns:
        Updated settings dictionary.
    """
    # Initialize hooks section if not present
    if "hooks" not in settings:
        settings["hooks"] = {}

    # Add each hook in the nested array format Claude Code expects:
    # { "HookName": [{"hooks": [{"type": "command", "command": "/path/to/script"}]}] }
    for hook_name, hook_path in hook_paths.items():
        settings["hooks"][hook_name] = [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_path,
                    }
                ]
            }
        ]

    return settings


def remove_hooks_from_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Remove Hamlet hooks from the settings dictionary.

    Args:
        settings: Current settings dictionary.

    Returns:
        Updated settings dictionary.
    """
    if "hooks" not in settings:
        return settings

    # Remove only the hooks we manage
    for hook_name in HOOK_SCRIPTS.keys():
        settings["hooks"].pop(hook_name, None)

    # Clean up empty hooks section
    if not settings["hooks"]:
        del settings["hooks"]

    return settings


def install_command(args: Namespace) -> int:
    """Install Hamlet hooks to Claude Code settings.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    print("Installing Hamlet hooks...")
    print()

    # Get settings path
    settings_path = get_settings_path(args)
    print(f"Settings path: {settings_path}")

    # Check if Claude Code directory exists
    claude_dir = settings_path.parent
    if not claude_dir.exists():
        print()
        print("Error: Claude Code not found.", file=sys.stderr)
        print()
        print("Claude Code does not appear to be installed.")
        print("Install Claude Code from: https://claude.ai/download")
        print("Then run 'hamlet install' again.")
        print()
        return 1

    # Find hooks directory
    hooks_dir = get_hooks_dir()
    if hooks_dir is None:
        print()
        print("Error: Hamlet hooks not found.", file=sys.stderr)
        print()
        print("Hamlet does not appear to be properly installed.")
        print("Reinstall with: pip install hamlet")
        print()
        return 1

    print(f"Hooks directory: {hooks_dir}")
    print()

    # Load hamlet settings to get mcp_port
    try:
        from hamlet.config.settings import Settings
        hamlet_settings = Settings.load()
    except Exception:
        hamlet_settings = None

    # Validate MCP server is running
    print("Checking MCP server...")
    is_running, message = validate_mcp_server_running()
    if not is_running:
        print(f"  Warning: {message}")
        print()
        print("The Hamlet MCP server must be running for hooks to work.")
        print("Start the server with: hamlet")
        print("Then run 'hamlet install' again in another terminal.")
        print()
        print("Continue anyway? (y/N): ", end="")
        try:
            response = input().strip().lower()
            if response not in ("y", "yes"):
                print("Installation cancelled.")
                return 1
        except EOFError:
            print("Installation cancelled (non-interactive).")
            return 1
    else:
        print(f"  ✓ {message}")

    # Write server_url to global hamlet config
    hamlet_config_path = Path.home() / ".hamlet" / "config.json"
    try:
        existing = {}
        if hamlet_config_path.exists():
            existing = json.loads(hamlet_config_path.read_text())
    except Exception:
        existing = {}
    mcp_port = hamlet_settings.mcp_port if hamlet_settings is not None else 8080
    existing["server_url"] = f"http://localhost:{mcp_port}/hamlet/event"
    hamlet_config_path.parent.mkdir(parents=True, exist_ok=True)
    hamlet_config_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    print()

    # Load existing settings
    claude_settings = load_settings(settings_path)

    # Create backup if requested and settings exist
    if not args.no_backup and claude_settings:
        backup_path = create_backup(settings_path, claude_settings)
        if backup_path:
            print(f"Backup created: {backup_path}")
        else:
            print("Warning: Could not create backup", file=sys.stderr)

    # Get hook paths
    hook_paths = get_hook_paths(hooks_dir)

    # Verify all hook scripts exist
    missing_hooks = []
    for hook_name, hook_path in hook_paths.items():
        if not Path(hook_path).exists():
            missing_hooks.append(hook_name)

    if missing_hooks:
        print()
        print(f"Error: Missing hook scripts: {', '.join(missing_hooks)}", file=sys.stderr)
        print()
        print("Hamlet installation appears to be corrupted.")
        print("Reinstall with: pip install --force-reinstall hamlet")
        print()
        return 1

    # Install hooks
    claude_settings = install_hooks_to_settings(claude_settings, hook_paths)

    # Save settings
    save_settings(settings_path, claude_settings)

    print()
    print("✓ Hooks installed successfully!")
    print()
    print("Configured hooks:")
    for hook_name, hook_path in hook_paths.items():
        print(f"  • {hook_name}: {hook_path}")
    print()
    print("Next steps:")
    print("  1. Restart Claude Code to apply changes")
    print("  2. Run 'hamlet uninstall' to remove hooks")
    print()

    return 0


def uninstall_command(args: Namespace) -> int:
    """Remove Hamlet hooks from Claude Code settings.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    print("Uninstalling Hamlet hooks...")
    print()

    # Get settings path
    settings_path = get_settings_path(args)
    print(f"Settings path: {settings_path}")
    print()

    # Check if settings file exists
    if not settings_path.exists():
        print("No settings file found. Nothing to uninstall.")
        return 0

    # Load existing settings
    settings = load_settings(settings_path)

    # Check if hooks are configured
    if "hooks" not in settings or not any(
        hook in settings["hooks"] for hook in HOOK_SCRIPTS.keys()
    ):
        print("No Hamlet hooks found in settings. Nothing to uninstall.")
        return 0

    # Restore from backup if requested
    if args.restore_backup:
        # Find the most recent backup
        backup_files = sorted(
            settings_path.parent.glob(f"{settings_path.stem}.backup.*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if backup_files:
            backup_path = backup_files[0]
            try:
                backup_content = backup_path.read_text(encoding="utf-8")
                backup_settings = json.loads(backup_content)

                # Only restore if it doesn't have our hooks (or has older version)
                print(f"Restoring from backup: {backup_path}")
                settings = backup_settings
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Could not restore from backup: {e}", file=sys.stderr)
                # Continue with normal removal
                settings = remove_hooks_from_settings(settings)
        else:
            print("No backup file found. Removing hooks from current settings.")
            settings = remove_hooks_from_settings(settings)
    else:
        # Remove hooks from settings
        settings = remove_hooks_from_settings(settings)

    # Save settings
    save_settings(settings_path, settings)

    print()
    print("✓ Hooks removed successfully!")
    print()
    print("Next steps:")
    print("  1. Restart Claude Code to apply changes")
    print()

    return 0
