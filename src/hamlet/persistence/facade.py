"""Persistence facade — main entry point for database operations."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from hamlet.event_processing.internal_event import InternalEvent
from hamlet.persistence.connection import DatabaseConnection
from hamlet.persistence.event_log import EventLogManager
from hamlet.persistence.loader import StateLoader
from hamlet.persistence.migrations import run_migrations
from hamlet.persistence.queue import WriteQueue
from hamlet.persistence.types import PersistenceConfig, WorldStateData, WriteOperation
from hamlet.persistence.writer import WriteExecutor
from hamlet.world_state.state import EventLogEntry

logger = logging.getLogger(__name__)

__all__ = ["PersistenceFacade"]


class PersistenceFacade:
    """Main entry point for persistence operations.

    Coordinates database connection, write queue, migrations, state loading,
    and event log management. Provides lifecycle methods (start/stop) and
    a checkpoint mechanism for durability.
    """

    def __init__(self, config: PersistenceConfig | None = None) -> None:
        """Initialize with optional config; components created lazily in start()."""
        self._config = config or PersistenceConfig()
        self._db: DatabaseConnection | None = None
        self._write_queue: WriteQueue | None = None
        self._write_executor: WriteExecutor | None = None
        self._state_loader: StateLoader | None = None
        self._event_log_manager: EventLogManager | None = None
        self._write_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Open database, run migrations, start write queue and background loop."""
        if self._running:
            return

        # Ensure parent directory exists for database file
        db_path = Path(self._config.db_path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Open database connection (WAL mode enabled in connection)
        self._db = DatabaseConnection(str(db_path))
        await self._db.__aenter__()

        try:
            # Run migrations
            await run_migrations(self._db)

            # Create write queue (no internal loop - facade manages draining)
            self._write_queue = WriteQueue(max_size=self._config.write_queue_size)

            # Create executor, loader, and event log manager
            self._write_executor = WriteExecutor(self._db)
            self._state_loader = StateLoader(self._db)
            self._event_log_manager = EventLogManager(
                self._db, max_entries=getattr(self._config, 'event_log_max_entries', 10000)
            )

            # Start background write loop
            self._running = True
            self._write_task = asyncio.create_task(
                self._write_loop(), name="persistence_write_loop"
            )

            logger.info("PersistenceFacade started with db_path=%s", db_path)
        except Exception:
            logger.exception("Failed to start PersistenceFacade")
            await self._cleanup_on_failure()
            raise

    async def _cleanup_on_failure(self) -> None:
        """Clean up resources after a failed start."""
        if self._db:
            try:
                await self._db.__aexit__(None, None, None)
            except Exception:
                pass
            self._db = None
        self._write_queue = None

    async def stop(self) -> None:
        """Stop background loop, flush queue, and close database connection."""
        if not self._running:
            return

        self._running = False

        # Cancel and await background write task
        if self._write_task:
            self._write_task.cancel()
            try:
                await self._write_task
            except asyncio.CancelledError:
                pass
            self._write_task = None

        # Close database connection
        if self._db:
            try:
                await self._db.__aexit__(None, None, None)
            except Exception:
                logger.exception("Error closing database connection")
            self._db = None

        self._write_queue = None
        self._write_executor = None
        self._state_loader = None
        self._event_log_manager = None

        logger.info("PersistenceFacade stopped")

    async def _write_loop(self) -> None:
        """Background task: continuously drain write queue and execute batches."""
        while self._running:
            try:
                batch = await self._write_queue.get_batch(max_items=100)
                if batch and self._write_executor:
                    await self._write_executor.execute_batch(batch)
                    # Mark all items as done using public method
                    for _ in batch:
                        self._write_queue.task_done()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error in persistence write loop")
                # Continue running despite errors (GP-7)

    async def checkpoint(self) -> None:
        """Drain all pending writes and run WAL checkpoint for durability."""
        if not self._running:
            raise RuntimeError("Cannot checkpoint: facade not running")
        if not self._write_queue:
            raise RuntimeError("Cannot checkpoint: write queue not initialized")

        try:
            # Wait for all pending items to be processed using public method
            await self._write_queue.join()

            # Run WAL checkpoint
            if self._db:
                await self._db.execute("PRAGMA wal_checkpoint")
                logger.debug("WAL checkpoint completed")
        except Exception:
            logger.exception("Error during checkpoint")
            raise

    def enqueue_write(self, operation: WriteOperation) -> None:
        """Enqueue a ``WriteOperation`` for the background write loop.

        Uses ``put_nowait`` so it can be called from synchronous code. If the
        queue is full the operation is silently dropped (acceptable data loss per
        GP-7).

        Args:
            operation: The write operation to enqueue.

        Raises:
            RuntimeError: If the facade is not running or the write queue is not
                initialised.
        """
        if not self._running or not self._write_queue:
            raise RuntimeError("Cannot enqueue write: facade not running")
        try:
            # Use put_nowait since this is a synchronous method
            self._write_queue.put_nowait(operation)
        except asyncio.QueueFull:
            # Drop silently per GP-7 (acceptable data loss)
            logger.debug("Write queue full, dropping operation")

    async def load_state(self) -> WorldStateData:
        """Load the persisted world state from the database for warm-start.

        Delegates to ``StateLoader`` to fetch all projects, villages, sessions,
        agents, structures, and world metadata rows.

        Returns:
            A ``WorldStateData`` instance populated from the database.

        Raises:
            RuntimeError: If the facade has not been started.
        """
        if not self._state_loader:
            raise RuntimeError("Cannot load state: facade not started")
        return await self._state_loader.load_state()

    async def log_event(self, event: InternalEvent) -> None:
        """Append an ``InternalEvent`` to the persistent event log.

        Constructs an ``EventLogEntry`` from the event's metadata and delegates
        to ``append_event_log``. Called by ``EventProcessor`` for every processed
        event.

        Args:
            event: The normalised event to record.

        Raises:
            RuntimeError: If the facade has not been started (propagated from
                ``append_event_log``).
        """
        tool_part = f": {event.tool_name}" if event.tool_name else ""
        entry = EventLogEntry(
            id=event.id,
            timestamp=event.received_at,
            session_id=event.session_id or "",
            project_id=event.project_id or "",
            hook_type=event.hook_type.value,
            tool_name=event.tool_name,
            summary=f"{event.hook_type.value}{tool_part}",
        )
        await self.append_event_log(entry)

    async def append_event_log(self, entry: EventLogEntry) -> None:
        """Append an ``EventLogEntry`` to the persistent event log.

        Delegates to ``EventLogManager.append``. Exceptions are logged and
        re-raised.

        Args:
            entry: The event log entry to persist.

        Raises:
            RuntimeError: If the facade has not been started.
            Exception: Any exception raised by the underlying event log manager.
        """
        if not self._event_log_manager:
            raise RuntimeError("Cannot append event log: facade not started")
        try:
            await self._event_log_manager.append(entry)
        except Exception:
            logger.exception("Failed to append event log entry")
            raise

    async def queue_write(self, entity_type: str, entity_id: str, data: Any) -> None:
        """Queue a write operation for an entity.

        This method is called by WorldStateManager to persist entity changes.
        It converts the data to a WriteOperation and enqueues it.

        Args:
            entity_type: Type of entity (project, session, agent, structure, village)
            entity_id: Unique identifier for the entity
            data: Entity data to persist (typically a dataclass instance)
        """
        from dataclasses import asdict, is_dataclass
        from enum import Enum

        if not self._running or not self._write_queue:
            raise RuntimeError("Cannot queue write: facade not running")

        def convert_value(obj: Any) -> Any:
            """Recursively convert enums and dataclasses to serializable values."""
            if isinstance(obj, Enum):
                return obj.value
            elif is_dataclass(obj) and not isinstance(obj, type):
                return asdict(obj)
            elif isinstance(obj, dict):
                return {k: convert_value(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_value(v) for v in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        def flatten_position(d: dict[str, Any]) -> dict[str, Any]:
            """Flatten position dataclass to position_x, position_y fields."""
            result = dict(d)
            if "position" in result and isinstance(result["position"], dict):
                pos = result.pop("position")
                result["position_x"] = pos.get("x", 0)
                result["position_y"] = pos.get("y", 0)
            if "center" in result and isinstance(result["center"], dict):
                center = result.pop("center")
                result["center_x"] = center.get("x", 0)
                result["center_y"] = center.get("y", 0)
            if "bounds" in result and isinstance(result["bounds"], dict):
                bounds = result.pop("bounds")
                result["bounds_min_x"] = bounds.get("min_x", 0)
                result["bounds_min_y"] = bounds.get("min_y", 0)
                result["bounds_max_x"] = bounds.get("max_x", 0)
                result["bounds_max_y"] = bounds.get("max_y", 0)
            return result

        try:
            # Convert dataclass to dict if needed
            if is_dataclass(data) and not isinstance(data, type):
                data_dict = asdict(data)
            elif hasattr(data, "__dict__"):
                data_dict = vars(data)
            else:
                data_dict = dict(data)

            # Convert enums and other non-serializable values
            data_dict = convert_value(data_dict)

            # Flatten nested dataclasses (position, center, bounds)
            data_dict = flatten_position(data_dict)

            operation = WriteOperation(
                entity_type=entity_type,  # type: ignore[arg-type]
                entity_id=entity_id,
                operation="insert",  # type: ignore[arg-type]
                data=data_dict,
            )
            self.enqueue_write(operation)
        except Exception:
            logger.exception("Failed to queue write for %s %s", entity_type, entity_id)
            raise
