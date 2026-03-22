"""Shared component initialization for hamlet application modes."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from hamlet.persistence.facade import PersistenceFacade
from hamlet.persistence.types import PersistenceConfig
from hamlet.world_state.manager import WorldStateManager
from hamlet.world_state.terrain import TerrainConfig
from hamlet.inference.engine import AgentInferenceEngine
from hamlet.inference.summarizer import ActivitySummarizer
from hamlet.simulation.engine import SimulationEngine
from hamlet.simulation.agent_updater import AgentUpdater
from hamlet.simulation.structure_updater import StructureUpdater
from hamlet.simulation.expansion import ExpansionManager
from hamlet.simulation.animation import AnimationManager
from hamlet.simulation.config import SimulationConfig
from hamlet.mcp_server.server import MCPServer
from hamlet.event_processing.event_processor import EventProcessor

if TYPE_CHECKING:
    from hamlet.config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class ComponentBundle:
    """Holds references to all running application components."""

    persistence: PersistenceFacade
    world_state: WorldStateManager
    agent_inference: AgentInferenceEngine
    simulation: SimulationEngine
    mcp_server: MCPServer
    event_processor: EventProcessor
    animation_manager: AnimationManager


async def build_components(settings: Settings, port: int | None = None) -> ComponentBundle:
    """Create and start all application components.

    Initialization order mirrors the original _run_app / _run_daemon sequence.
    The caller is responsible for shutting down the bundle on exit (see
    shutdown_components).

    Args:
        settings: Loaded HamletSettings / Settings instance.
        port: Override for the MCP server port. Defaults to settings.mcp_port.

    Returns:
        A ComponentBundle with all components started.
    """
    mcp_port = port if port is not None else settings.mcp_port

    started = []
    try:
        # 1. Initialize persistence
        logger.debug("Initializing PersistenceFacade...")
        persistence = PersistenceFacade(PersistenceConfig(db_path=settings.db_path))
        await persistence.start()
        started.append(persistence)

        # 2. Initialize world state
        logger.debug("Initializing WorldStateManager...")
        # Build TerrainConfig from settings.terrain dict if present
        terrain_config = None
        if hasattr(settings, 'terrain') and settings.terrain:
            terrain_config = TerrainConfig(**settings.terrain)
        world_state = WorldStateManager(persistence, terrain_config=terrain_config)
        await world_state.load_from_persistence()

        # 2a. Initialize agent inference engine
        logger.debug("Initializing AgentInferenceEngine...")
        summarizer = ActivitySummarizer(model=settings.activity_model)
        agent_inference = AgentInferenceEngine(
            world_state,
            summarizer=summarizer,
            despawn_threshold_seconds=settings.zombie_despawn_seconds,
            zombie_threshold_seconds=settings.zombie_threshold_seconds,
        )
        await agent_inference.startup()

        # 2b. Initialize simulation subsystems
        logger.debug("Initializing simulation subsystems...")
        sim_config = SimulationConfig(tick_rate=settings.tick_rate)
        agent_updater = AgentUpdater(config=sim_config)
        structure_updater = StructureUpdater(config=sim_config)
        expansion_manager = ExpansionManager(config=sim_config)
        animation_manager = AnimationManager()

        # 3. Initialize MCP server (creates event queue)
        logger.debug("Initializing MCPServer...")
        mcp_server = MCPServer(
            world_state=world_state,
            port=mcp_port,
            animation_manager=animation_manager,
        )
        await mcp_server.start()
        started.append(mcp_server)

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
        started.append(event_processor)

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
        started.append(simulation)

        return ComponentBundle(
            persistence=persistence,
            world_state=world_state,
            agent_inference=agent_inference,
            simulation=simulation,
            mcp_server=mcp_server,
            event_processor=event_processor,
            animation_manager=animation_manager,
        )
    except Exception:
        for component in reversed(started):
            try:
                await component.stop()
            except Exception:
                pass
        raise


async def shutdown_components(bundle: ComponentBundle) -> None:
    """Stop all components in reverse startup order (per GP-7).

    Args:
        bundle: The ComponentBundle returned by build_components.
    """
    logger.debug("Shutting down components...")

    try:
        await bundle.simulation.stop()
    except Exception as exc:
        logger.warning("Error stopping SimulationEngine: %s", exc)

    try:
        await bundle.event_processor.stop()
    except Exception as exc:
        logger.warning("Error stopping EventProcessor: %s", exc)

    try:
        await bundle.mcp_server.stop()
    except Exception as exc:
        logger.warning("Error stopping MCPServer: %s", exc)

    try:
        await bundle.persistence.stop()
    except Exception as exc:
        logger.warning("Error stopping PersistenceFacade: %s", exc)
