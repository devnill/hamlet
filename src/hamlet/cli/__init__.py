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
  hamlet --help         Show this help message

For more information, visit: https://github.com/dan/hamlet
        """
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.5.0"
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
        default="http://localhost:8080",
        help="Daemon URL"
    )
    view_parser.set_defaults(func=_view_command)

    return parser


def _init_command(args) -> int:
    """Thin shim so the init import is deferred until the command is actually invoked."""
    from hamlet.cli.commands.init import init_command
    return init_command(args)


def _daemon_command(args) -> int:
    """Thin shim so the daemon import is deferred until the command is actually invoked."""
    from hamlet.cli.commands.daemon import daemon_command
    return daemon_command(args)


def _view_command(args) -> int:
    """Thin shim that launches the TUI viewer connecting to a running daemon."""
    import asyncio
    from hamlet.__main__ import _run_viewer
    url = getattr(args, "url", "http://localhost:8080")
    return asyncio.run(_run_viewer(url))


def main(args: list[str] | None = None) -> int:
    """Main entry point for the Hamlet CLI.

    Args:
        args: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        import asyncio
        from hamlet.__main__ import _run_viewer
        return asyncio.run(_run_viewer("http://localhost:8080"))

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
