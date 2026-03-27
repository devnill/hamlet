"""Daemon command — run Hamlet backend without the TUI."""
from __future__ import annotations

import asyncio
import logging
import signal
import socket
import sys
import time
import urllib.request
from types import FrameType

from hamlet.config.settings import Settings

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown (set by signal handlers)
_shutdown_requested = False

# How often (in seconds) to re-read config.json at runtime
RELOAD_INTERVAL = 30


def _apply_config_changes(bundle, changes: dict, new_settings) -> None:
    """Apply changed settings to running components.

    Args:
        bundle: ComponentBundle with references to running components.
        changes: Dict of {field_name: (old_value, new_value)} from Settings.diff().
        new_settings: The newly loaded Settings instance.
    """
    for field_name, (old_val, new_val) in changes.items():
        logger.info("Config changed: %s = %r (was %r)", field_name, new_val, old_val)

    if "min_village_distance" in changes:
        bundle.world_state._min_village_distance = new_settings.min_village_distance

    if "zombie_threshold_seconds" in changes:
        bundle.agent_inference._zombie_threshold_seconds = new_settings.zombie_threshold_seconds

    if "tick_rate" in changes:
        bundle.simulation.set_tick_rate(new_settings.tick_rate)

    if "mcp_port" in changes:
        logger.warning(
            "mcp_port changed to %d — restart required for this to take effect",
            new_settings.mcp_port,
        )


def _check_port_conflict(port: int) -> str | None:
    """
    Returns None if the port is free.
    Returns "hamlet" if hamlet daemon is already running on this port.
    Returns "other" if something else is using the port.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        if s.connect_ex(("localhost", port)) != 0:
            return None  # port is free
    # Port is in use — check if it's hamlet
    try:
        with urllib.request.urlopen(
            f"http://localhost:{port}/hamlet/health", timeout=1
        ) as resp:
            if resp.status == 200:
                return "hamlet"
    except Exception:
        pass
    return "other"


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
    _shutdown_requested = False

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

        # Wait until a shutdown signal is received, reloading config every RELOAD_INTERVAL seconds
        last_reload = time.monotonic()
        current_settings = settings

        while not _shutdown_requested:
            await asyncio.sleep(0.5)
            now = time.monotonic()
            if now - last_reload >= RELOAD_INTERVAL:
                # Update before load so a broken config file does not cause tight-loop retries
                last_reload = now
                try:
                    new_settings = Settings.load()
                    changes = current_settings.diff(new_settings)
                    if changes:
                        _apply_config_changes(bundle, changes, new_settings)
                        current_settings = new_settings
                except Exception:
                    logger.exception("Config reload failed, keeping current settings")

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
    settings = Settings.load()
    port = getattr(args, "port", None) or settings.mcp_port

    conflict = _check_port_conflict(port)
    if conflict == "hamlet":
        print(
            f"Error: hamlet daemon is already running on port {port}.\n"
            f"  Check status:  hamlet service status\n"
            f"  Stop service:  hamlet service stop\n"
            f"  Or stop the foreground daemon with Ctrl+C if it is running in another terminal.",
            file=sys.stderr,
        )
        sys.exit(1)
    elif conflict == "other":
        print(
            f"Error: port {port} is already in use by another process.\n"
            f"  Check status:  hamlet service status\n"
            f"  Stop service:  hamlet service stop\n"
            f"  Or use --port to specify a different port.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        return asyncio.run(_run_daemon(port))
    except KeyboardInterrupt:
        print("\n\nGoodbye!", file=sys.stderr)
        return 0
    except Exception as exc:
        logger.exception("Fatal daemon error: %s", exc)
        print(f"\nFatal error: {exc}", file=sys.stderr)
        return 1
