"""Daemon command — run Hamlet backend without the TUI."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from types import FrameType

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown (set by signal handlers)
_shutdown_requested = False


def _signal_handler(signum: int, frame: FrameType | None) -> None:
    """Handle SIGINT and SIGTERM by requesting a clean shutdown."""
    global _shutdown_requested
    logger.info("Received signal %s, initiating graceful shutdown...", signum)
    _shutdown_requested = True


async def _run_daemon(port: int) -> int:
    """Initialize and run the Hamlet backend components without a TUI.

    Components are started in the same order as _run_app() in __main__.py and
    stopped in reverse order on exit (per GP-7).

    Args:
        port: TCP port for the MCP / HTTP event endpoint.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    global _shutdown_requested

    from hamlet.config.settings import Settings
    from hamlet.config.paths import HAMLET_DIR, ensure_hamlet_dir
    from hamlet.app_factory import build_components, shutdown_components

    # Register signal handlers
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Ensure ~/.hamlet/ exists and set up file logging
    ensure_hamlet_dir()
    log_path = HAMLET_DIR / "hamlet.log"
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logging.getLogger().addHandler(file_handler)
    logger.info("Daemon starting — logging to %s", log_path)

    # Load settings (port override already resolved by caller)
    settings = Settings.load()

    bundle = None

    try:
        bundle = await build_components(settings, port=port)

        logger.info(
            "Hamlet daemon running on port %d — press Ctrl-C or send SIGTERM to stop", port
        )

        # Wait until a shutdown signal is received
        while not _shutdown_requested:
            await asyncio.sleep(0.5)

        logger.info("Shutdown requested, stopping components...")

    except OSError as exc:
        err_msg = str(exc).lower()
        if "address already in use" in err_msg or "port" in err_msg:
            logger.exception("Port conflict: %s", exc)
            print("\nError: Port already in use", file=sys.stderr)
            print(
                "       Another process is using the required port.", file=sys.stderr
            )
            print(
                "       Change mcp_port in ~/.hamlet/config.json or stop the other process.",
                file=sys.stderr,
            )
        elif "permission denied" in err_msg:
            logger.exception("Permission error: %s", exc)
            print("\nError: Permission denied", file=sys.stderr)
            print(
                "       Check file permissions for ~/.hamlet/ directory.", file=sys.stderr
            )
        else:
            logger.exception("OS error: %s", exc)
            print(f"\nError: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("Daemon error: %s", exc)
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    finally:
        if bundle is not None:
            await shutdown_components(bundle)
        logger.info("Hamlet daemon stopped.")

    return 0


def daemon_command(args) -> int:
    """Entry point for the `hamlet daemon` CLI subcommand.

    Args:
        args: Parsed argparse Namespace.  May contain an optional ``port``
              attribute that overrides the port in Settings.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    from hamlet.config.settings import Settings

    settings = Settings.load()
    port = getattr(args, "port", None) or settings.mcp_port

    try:
        return asyncio.run(_run_daemon(port))
    except KeyboardInterrupt:
        print("\n\nGoodbye!", file=sys.stderr)
        return 0
    except Exception as exc:
        logger.exception("Fatal daemon error: %s", exc)
        print(f"\nFatal error: {exc}", file=sys.stderr)
        return 1
