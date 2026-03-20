"""EventProcessor: consumes raw events from the queue, normalizes them, and routes them."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from .event_router import EventCallback, EventRouter
from .internal_event import HookType, InternalEvent
from .sequence_generator import SequenceGenerator

logger = logging.getLogger(__name__)

# Required fields in a raw event dict
_REQUIRED_FIELDS = ("session_id", "project_id", "hook_type")


class EventProcessor(EventRouter):
    """Consumes raw event dicts from an asyncio.Queue, validates and normalises
    them into InternalEvent objects, then routes them concurrently to
    world_state, agent_inference, persistence, and any registered subscribers.
    """

    def __init__(
        self,
        event_queue: asyncio.Queue[dict[str, Any]],
        world_state: Any | None = None,
        agent_inference: Any | None = None,
        persistence: Any | None = None,
    ) -> None:
        self._queue = event_queue
        self._world_state = world_state
        self._agent_inference = agent_inference
        self._persistence = persistence

        self._sequence = SequenceGenerator()
        self._subscribers: list[EventCallback] = []
        self._subscriber_lock = asyncio.Lock()

        self._running = False
        self._task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # EventRouter interface
    # ------------------------------------------------------------------

    async def subscribe(self, callback: EventCallback) -> None:
        """Register a callback to receive all processed events."""
        async with self._subscriber_lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    async def unsubscribe(self, callback: EventCallback) -> None:
        """Remove a previously registered callback."""
        async with self._subscriber_lock:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Begin consuming events from the queue in the background."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(
            self._consume_loop(), name="event_processor"
        )
        logger.info("EventProcessor started")

    async def stop(self) -> None:
        """Gracefully stop the consume loop and wait for it to finish."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("EventProcessor stopped")

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------

    async def process_event(self, raw: dict[str, Any]) -> InternalEvent:
        """Validate and normalise a raw event dict into an InternalEvent.

        Args:
            raw: Dictionary from the event queue.

        Returns:
            A fully populated InternalEvent.

        Raises:
            ValueError: If required fields are absent or empty.
        """
        # Validate required fields
        for field in _REQUIRED_FIELDS:
            value = raw.get(field)
            if not value:
                raise ValueError(
                    f"Raw event is missing required field '{field}' or it is empty"
                )

        # Parse hook_type
        hook_type_str: str = raw["hook_type"]
        try:
            hook_type = HookType(hook_type_str)
        except ValueError:
            raise ValueError(
                f"Unknown hook_type '{hook_type_str}'. "
                f"Valid values: {[h.value for h in HookType]}"
            )

        event_id = str(uuid.uuid4())
        sequence = await self._sequence.next()

        project_id: str = raw["project_id"]
        project_name: str = raw.get("project_name") or project_id

        return InternalEvent(
            id=event_id,
            sequence=sequence,
            received_at=datetime.now(UTC),
            session_id=raw["session_id"],
            project_id=project_id,
            project_name=project_name,
            hook_type=hook_type,
            tool_name=raw.get("tool_name"),
            tool_input=raw.get("tool_input"),
            tool_output=raw.get("tool_output"),
            success=raw.get("success"),
            duration_ms=raw.get("duration_ms"),
            notification_message=raw.get("notification_message"),
            stop_reason=raw.get("stop_reason"),
            raw_payload=dict(raw),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _route_event(self, event: InternalEvent) -> None:
        """Send event concurrently to all routing destinations."""
        tasks: list[Any] = []

        if self._world_state is not None:
            tasks.append(self._world_state.handle_event(event))

        if self._agent_inference is not None:
            tasks.append(self._agent_inference.process_event(event))

        if self._persistence is not None:
            tasks.append(self._persistence.log_event(event))

        async with self._subscriber_lock:
            subscriber_snapshot = list(self._subscribers)

        for callback in subscriber_snapshot:
            tasks.append(callback(event))

        if not tasks:
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error("Error routing event %s: %s", event.id, result)

    async def _consume_loop(self) -> None:
        """Main loop: pull events from the queue and process them."""
        logger.debug("EventProcessor consume loop running")
        while self._running:
            try:
                raw = await self._queue.get()
            except asyncio.CancelledError:
                break

            try:
                event = await self.process_event(raw)
                await self._route_event(event)
            except Exception as exc:
                logger.error("Failed to process event: %s — %s", raw, exc)
            finally:
                self._queue.task_done()

        logger.debug("EventProcessor consume loop exited")


__all__ = ["EventProcessor"]
