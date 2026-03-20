"""Entry point for hamlet package."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path
from types import FrameType
from typing import Any

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
    global _shutdown_requested

    # Import components here to avoid issues if dependencies are missing
    from hamlet.config.settings import Settings
    from hamlet.tui.app import HamletApp
    from hamlet.world_state.manager import WorldStateManager
    from hamlet.viewport.manager import ViewportManager
    from hamlet.persistence.facade import PersistenceFacade
    from hamlet.persistence.types import PersistenceConfig
    from hamlet.event_processing.event_processor import EventProcessor
    from hamlet.inference.engine import AgentInferenceEngine
    from hamlet.inference.summarizer import ActivitySummarizer
    from hamlet.simulation.engine import SimulationEngine
    from hamlet.simulation.agent_updater import AgentUpdater
    from hamlet.simulation.structure_updater import StructureUpdater
    from hamlet.simulation.expansion import ExpansionManager
    from hamlet.simulation.animation import AnimationManager
    from hamlet.simulation.config import SimulationConfig
    from hamlet.mcp_server.server import MCPServer

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Load configuration
    logger.debug("Loading settings...")
    settings = Settings.load()

    # Component references for cleanup
    persistence: PersistenceFacade | None = None
    world_state: WorldStateManager | None = None
    agent_inference: AgentInferenceEngine | None = None
    event_processor: EventProcessor | None = None
    simulation: SimulationEngine | None = None
    mcp_server: MCPServer | None = None
    viewport: ViewportManager | None = None
    app: HamletApp | None = None

    try:
        # 1. Initialize persistence
        logger.debug("Initializing PersistenceFacade...")
        persistence = PersistenceFacade(PersistenceConfig(db_path=settings.db_path))
        await persistence.start()

        # 2. Initialize world state
        logger.debug("Initializing WorldStateManager...")
        world_state = WorldStateManager(persistence)
        await world_state.load_from_persistence()

        # 2a. Initialize agent inference engine
        logger.debug("Initializing AgentInferenceEngine...")
        summarizer = ActivitySummarizer(model=settings.activity_model)
        agent_inference = AgentInferenceEngine(world_state, summarizer=summarizer)

        # 2b. Initialize simulation subsystems
        logger.debug("Initializing simulation subsystems...")
        sim_config = SimulationConfig(tick_rate=settings.tick_rate)
        agent_updater = AgentUpdater(config=sim_config)
        structure_updater = StructureUpdater(config=sim_config)
        expansion_manager = ExpansionManager(config=sim_config)
        animation_manager = AnimationManager()

        # 3. Initialize MCP server (creates event queue)
        logger.debug("Initializing MCPServer...")
        mcp_server = MCPServer(world_state=world_state, port=settings.mcp_port, animation_manager=animation_manager)
        await mcp_server.start()

        # 4. Initialize event processor with queue from MCP server
        logger.debug("Initializing EventProcessor...")
        event_queue = mcp_server.get_event_queue()
        event_processor = EventProcessor(
            event_queue=event_queue,
            world_state=world_state,
            agent_inference=agent_inference,
            persistence=persistence,
        )
        await event_processor.start()

        # 5. Initialize simulation engine
        logger.debug("Initializing SimulationEngine...")
        simulation = SimulationEngine(
            world_state=world_state,
            config=sim_config,
            agent_updater=agent_updater,
            structure_updater=structure_updater,
            expansion_manager=expansion_manager,
            animation_manager=animation_manager,
            agent_inference=agent_inference,
        )
        await simulation.start()

        # 6. Initialize viewport
        logger.debug("Initializing ViewportManager...")
        viewport = ViewportManager(world_state)
        await viewport.initialize()

        # 7. Create TUI application
        logger.debug("Starting HamletApp...")
        app = HamletApp(world_state, viewport, event_processor)

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
        # Shutdown in reverse order (graceful degradation per GP-7)
        logger.debug("Shutting down components...")

        # Stop simulation (before event processor — reverse of startup order)
        if simulation is not None:
            try:
                await simulation.stop()
            except Exception as exc:
                logger.warning("Error stopping SimulationEngine: %s", exc)

        # Stop event processor
        if event_processor is not None:
            try:
                await event_processor.stop()
            except Exception as exc:
                logger.warning("Error stopping EventProcessor: %s", exc)

        # Stop MCP server
        if mcp_server is not None:
            try:
                await mcp_server.stop()
            except Exception as exc:
                logger.warning("Error stopping MCPServer: %s", exc)

        # Stop persistence
        if persistence is not None:
            try:
                await persistence.stop()
            except Exception as exc:
                logger.warning("Error stopping PersistenceFacade: %s", exc)

    return 0


async def _run_viewer(base_url: str = "http://localhost:8080") -> int:
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
                "       Start the daemon first with: hamlet",
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


def main() -> None:
    """Main entry point for the Hamlet TUI application."""
    args = sys.argv[1:]

    if not args:
        # No subcommand: launch viewer mode (backward compatible)
        from hamlet.config.settings import Settings
        settings = Settings.load()
        exit_code = asyncio.run(_run_viewer(f"http://localhost:{settings.mcp_port}"))
        sys.exit(exit_code if exit_code is not None else 0)
        return

    # Delegate to CLI for subcommand dispatch (daemon, init, install, view, etc.)
    from hamlet.cli import main as cli_main
    sys.exit(cli_main(args))


if __name__ == "__main__":
    sys.exit(main())
