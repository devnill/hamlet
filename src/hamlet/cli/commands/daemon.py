"""Daemon command — run Hamlet backend without the TUI."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path
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
    from hamlet.persistence.facade import PersistenceFacade
    from hamlet.persistence.types import PersistenceConfig
    from hamlet.world_state.manager import WorldStateManager
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

    # Component references for cleanup
    persistence: PersistenceFacade | None = None
    world_state: WorldStateManager | None = None
    agent_inference: AgentInferenceEngine | None = None
    event_processor: EventProcessor | None = None
    simulation: SimulationEngine | None = None
    mcp_server: MCPServer | None = None

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
        mcp_server = MCPServer(world_state=world_state, port=port, animation_manager=animation_manager)
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
        # Shutdown in reverse order (graceful degradation per GP-7)
        logger.debug("Shutting down components...")

        if simulation is not None:
            try:
                await simulation.stop()
            except Exception as exc:
                logger.warning("Error stopping SimulationEngine: %s", exc)

        if event_processor is not None:
            try:
                await event_processor.stop()
            except Exception as exc:
                logger.warning("Error stopping EventProcessor: %s", exc)

        if mcp_server is not None:
            try:
                await mcp_server.stop()
            except Exception as exc:
                logger.warning("Error stopping MCPServer: %s", exc)

        if persistence is not None:
            try:
                await persistence.stop()
            except Exception as exc:
                logger.warning("Error stopping PersistenceFacade: %s", exc)

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
