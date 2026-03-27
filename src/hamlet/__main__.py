"""Entry point for hamlet package."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from types import FrameType

# Configure logging before anything else
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
_shutdown_requested = False


def _signal_handler(signum: int, frame: FrameType | None) -> None:
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    logger.info("Received signal %s, initiating graceful shutdown...", signum)
    _shutdown_requested = True


async def _run_app() -> int:
    """Initialize and run the Hamlet TUI application.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    from hamlet.config.settings import Settings
    from hamlet.tui.app import HamletApp
    from hamlet.viewport.manager import ViewportManager
    from hamlet.app_factory import build_components, shutdown_components

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Load configuration
    logger.debug("Loading settings...")
    settings = Settings.load()

    bundle = None
    viewport = None
    app = None

    try:
        bundle = await build_components(settings)

        # 6. Initialize viewport
        logger.debug("Initializing ViewportManager...")
        viewport = ViewportManager(bundle.world_state)
        await viewport.initialize()

        # 7. Create TUI application
        logger.debug("Starting HamletApp...")
        app = HamletApp(bundle.world_state, viewport, bundle.event_processor)

        # Run the TUI application
        await app.run_async()

    except OSError as exc:
        # Handle common OS-level errors with helpful messages
        err_msg = str(exc).lower()
        if "address already in use" in err_msg or "port" in err_msg:
            logger.exception("Port conflict: %s", exc)
            print("\nError: Port already in use", file=sys.stderr)
            print("       Another process is using the required port.", file=sys.stderr)
            print("       Change mcp_port in ~/.hamlet/config.json or stop the other process.", file=sys.stderr)
        elif "permission denied" in err_msg:
            logger.exception("Permission error: %s", exc)
            print("\nError: Permission denied", file=sys.stderr)
            print("       Check file permissions for ~/.hamlet/ directory.", file=sys.stderr)
        else:
            logger.exception("OS error: %s", exc)
            print(f"\nError: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("Application error: %s", exc)
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    finally:
        if bundle is not None:
            await shutdown_components(bundle)

    return 0


async def _run_viewer(base_url: str) -> int:
    """Run the Hamlet TUI in viewer mode, connecting to a running daemon.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    from hamlet.tui.remote_state import RemoteStateProvider
    from hamlet.tui.remote_world_state import RemoteWorldState
    from hamlet.tui.app import HamletApp
    from hamlet.viewport.manager import ViewportManager

    provider = RemoteStateProvider(base_url)
    await provider.start()

    try:
        healthy = await provider.check_health()
        if not healthy:
            print(
                f"Error: Hamlet daemon is not running at {base_url}",
                file=sys.stderr,
            )
            print(
                "       Start the daemon first with: hamlet daemon",
                file=sys.stderr,
            )
            return 1

        remote_state = RemoteWorldState(provider)

        # Perform an initial refresh so the viewport can initialise correctly
        await remote_state.refresh()

        viewport = ViewportManager(remote_state)
        await viewport.initialize()

        app = HamletApp(remote_state, viewport, remote_provider=provider)
        await app.run_async()

    except Exception as exc:
        logger.exception("Viewer error: %s", exc)
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    finally:
        await provider.stop()

    return 0


def _run_viewer_kitty(base_url: str) -> int:
    """Run the Hamlet Kitty graphics viewer, connecting to a running daemon.

    No subprocess isolation needed — pure Python.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    from hamlet.gui.kitty.app import KittyApp
    return KittyApp(base_url).run()


def main() -> None:
    """Main entry point for the Hamlet TUI application."""
    args = sys.argv[1:]

    # Handle --map-viewer flag
    if "--map-viewer" in args:
        from hamlet.tui.map_app import MapApp
        app = MapApp()
        exit_code = asyncio.run(app.run_async())
        sys.exit(exit_code if exit_code is not None else 0)
        return

    if not args:
        # No subcommand: launch viewer mode (backward compatible)
        from hamlet.config.settings import Settings
        from hamlet.gui.detect import resolve_renderer

        settings = Settings.load()
        url = f"http://localhost:{settings.mcp_port}"
        renderer = resolve_renderer(None, settings.renderer)

        if renderer == "kitty":
            exit_code = _run_viewer_kitty(url)
            sys.exit(exit_code if exit_code is not None else 0)
            return

        exit_code = asyncio.run(_run_viewer(url))
        sys.exit(exit_code if exit_code is not None else 0)
        return

    # Delegate to CLI for subcommand dispatch (daemon, init, install, view, etc.)
    from hamlet.cli import main as cli_main
    sys.exit(cli_main(args))


if __name__ == "__main__":
    sys.exit(main())
