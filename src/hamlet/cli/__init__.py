"""Hamlet CLI - Command-line interface for managing Hamlet installation."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .commands import install


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser for the Hamlet CLI."""
    parser = argparse.ArgumentParser(
        prog="hamlet",
        description="Hamlet - Terminal-based idle game for Claude Code agent activity visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  hamlet install        Install hooks to Claude Code settings
  hamlet uninstall      Remove hooks from Claude Code settings
  hamlet map-viewer     Open terrain viewer with parameter adjustment
  hamlet --help         Show this help message

For more information, visit: https://github.com/dan/hamlet
        """
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.5.1"
    )
    parser.add_argument(
        "--map-viewer",
        action="store_true",
        help="Launch map viewer mode for terrain exploration and parameter adjustment"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Install command
    install_parser = subparsers.add_parser(
        "install",
        help="Install Hamlet hooks to Claude Code settings",
        description="Configure Claude Code to use Hamlet hooks for agent activity visualization."
    )
    install_parser.add_argument(
        "--settings-path",
        type=str,
        default=None,
        help="Path to Claude Code settings.json (default: auto-detect)"
    )
    install_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a backup of existing settings"
    )
    install_parser.set_defaults(func=install.install_command)

    # Uninstall command
    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="Remove Hamlet hooks from Claude Code settings",
        description="Remove Hamlet hook configuration from Claude Code settings."
    )
    uninstall_parser.add_argument(
        "--settings-path",
        type=str,
        default=None,
        help="Path to Claude Code settings.json (default: auto-detect)"
    )
    uninstall_parser.add_argument(
        "--restore-backup",
        action="store_true",
        help="Restore settings from backup if available"
    )
    uninstall_parser.set_defaults(func=install.uninstall_command)

    # Init command
    init_parser = subparsers.add_parser(
        "init",
        help="Create .hamlet/config.json in the current directory",
        description="Initialize a per-project Hamlet configuration file in the current working directory."
    )
    init_parser.set_defaults(func=_init_command)

    # Daemon command
    daemon_parser = subparsers.add_parser(
        "daemon",
        help="Run hamlet backend daemon (HTTP server, event processing, simulation) without TUI",
        description="Start all Hamlet backend components without launching the Textual TUI."
    )
    daemon_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Override MCP port (default: value from ~/.hamlet/config.json)"
    )
    daemon_parser.set_defaults(func=_daemon_command)

    # View command
    view_parser = subparsers.add_parser(
        "view",
        help="Open hamlet TUI viewer (daemon must be running)",
        description="Connect to a running Hamlet daemon and open the TUI viewer."
    )
    view_parser.add_argument(
        "--url",
        default=None,
        help="Daemon URL"
    )
    view_parser.add_argument(
        "--renderer",
        choices=["auto", "textual", "kitty"],
        default=None,
        help="Renderer backend (default: from settings or auto-detect)"
    )
    view_parser.set_defaults(func=_view_command)

    # Map viewer command
    map_viewer_parser = subparsers.add_parser(
        "map-viewer",
        help="Open terrain viewer with parameter adjustment",
        description="Launch the map viewer for terrain exploration and parameter tuning. Shows terrain without agents/structures."
    )
    map_viewer_parser.set_defaults(func=_map_viewer_command)

    # Settings command
    settings_parser = subparsers.add_parser(
        "settings",
        help="View and modify hamlet configuration",
        description=(
            "View and modify hamlet configuration settings.\n\n"
            "Commonly changed settings:\n"
            "  mcp_port                  Daemon HTTP port\n"
            "  tick_rate                 Simulation ticks per second\n"
            "  zombie_threshold_seconds  Seconds before idle agents turn zombie\n"
            "  terrain.*                 Terrain generation parameters\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    settings_subparsers = settings_parser.add_subparsers(
        dest="settings_subcommand",
        help="Settings sub-commands"
    )
    settings_subparsers.add_parser(
        "get",
        help="Print the value for a single key",
        description="Print the current value for a single settings key. Use dot notation for terrain sub-keys (e.g. terrain.seed).",
    ).add_argument("key", help="Setting key (e.g. mcp_port or terrain.seed)")
    settings_set_parser = settings_subparsers.add_parser(
        "set",
        help="Update a setting and save to config file",
        description="Update a settings key and persist to ~/.hamlet/config.json. Use dot notation for terrain sub-keys (e.g. terrain.seed).",
    )
    settings_set_parser.add_argument("key", help="Setting key (e.g. mcp_port or terrain.seed)")
    settings_set_parser.add_argument("value", help="New value")
    settings_parser.set_defaults(func=_settings_command)

    # Doctor command
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Diagnose renderer configuration",
        description="Print terminal type, tmux detection, and recommended renderer."
    )
    doctor_parser.set_defaults(func=_doctor_command)

    # Service command (macOS launchd integration)
    service_parser = subparsers.add_parser(
        "service",
        help="Manage the hamlet daemon as a macOS launchd service",
        description="Install, start, stop, and manage the hamlet daemon via launchd (macOS only)."
    )
    service_subparsers = service_parser.add_subparsers(
        dest="service_subcommand",
        help="Service sub-commands"
    )
    service_subparsers.required = True
    service_subparsers.add_parser("install", help="Install and load the launchd service")
    service_subparsers.add_parser("uninstall", help="Unload and remove the launchd service")
    service_subparsers.add_parser("start", help="Start (load) the launchd service")
    service_subparsers.add_parser("stop", help="Stop (unload) the launchd service")
    service_subparsers.add_parser("restart", help="Restart the launchd service")
    service_subparsers.add_parser("status", help="Show service installation and running status")
    service_parser.set_defaults(func=_service_command)

    return parser


def _init_command(args) -> int:
    """Thin shim so the init import is deferred until the command is actually invoked."""
    from hamlet.cli.commands.init import init_command
    return init_command(args)


def _daemon_command(args) -> int:
    """Thin shim so the daemon import is deferred until the command is actually invoked."""
    from hamlet.cli.commands.daemon import daemon_command
    return daemon_command(args)


def _launch_kitty_viewer(url: str) -> int:
    """Import and run the KittyApp viewer directly (no subprocess isolation)."""
    from hamlet.__main__ import _run_viewer_kitty
    return _run_viewer_kitty(url)


def _view_command(args) -> int:
    """Thin shim that launches the TUI viewer connecting to a running daemon."""
    import asyncio
    from hamlet.config.settings import Settings
    from hamlet.gui.detect import resolve_renderer

    settings = Settings.load()
    url = getattr(args, "url", None)
    if not url:
        url = f"http://localhost:{settings.mcp_port}"

    cli_renderer = getattr(args, "renderer", None)
    renderer = resolve_renderer(cli_renderer, settings.renderer)

    if renderer == "kitty":
        return _launch_kitty_viewer(url)

    from hamlet.__main__ import _run_viewer
    return asyncio.run(_run_viewer(url))


def _map_viewer_command(args) -> int:
    """Launch the map viewer TUI for terrain exploration and parameter adjustment."""
    import asyncio
    from hamlet.tui.map_app import MapApp
    app = MapApp()
    return asyncio.run(app.run_async())


def _settings_command(args) -> int:
    """Thin shim so the settings import is deferred until the command is actually invoked."""
    from hamlet.cli.commands.settings_cmd import settings_command
    return settings_command(args)


def _service_command(args) -> int:
    """Thin shim so the service import is deferred until the command is actually invoked."""
    from hamlet.cli.commands.service import service_command
    return service_command(args)


def _doctor_command(args) -> int:
    """Thin shim so the doctor import is deferred until the command is actually invoked."""
    from hamlet.cli.commands.doctor import doctor_command
    return doctor_command(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point for the Hamlet CLI.

    Args:
        args: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    # Handle --map-viewer flag
    if getattr(parsed_args, 'map_viewer', False):
        import asyncio
        from hamlet.tui.map_app import MapApp
        app = MapApp()
        return asyncio.run(app.run_async())

    if not parsed_args.command:
        import asyncio
        from hamlet.config.settings import Settings
        from hamlet.gui.detect import resolve_renderer

        settings = Settings.load()
        url = f"http://localhost:{settings.mcp_port}"
        renderer = resolve_renderer(None, settings.renderer)

        if renderer == "kitty":
            return _launch_kitty_viewer(url)

        from hamlet.__main__ import _run_viewer
        return asyncio.run(_run_viewer(url))

    try:
        return parsed_args.func(parsed_args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
