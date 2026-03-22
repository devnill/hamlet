"""Agent inference engine — infers agent lifecycle from hook events."""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from hamlet.event_processing.internal_event import HookType, InternalEvent

if TYPE_CHECKING:
    from hamlet.protocols import WorldStateProtocol
from hamlet.inference.rules import TYPE_RULES
from hamlet.inference.summarizer import ActivitySummarizer
from hamlet.world_state.rules import TOOL_TO_STRUCTURE
from hamlet.inference.types import (
    AgentType,
    InferenceAction,
    InferenceResult,
    InferenceState,
    PendingTool,
    SessionState,
    ToolWindow,
    TYPE_COLORS,
)
from hamlet.simulation.config import SimulationConfig
from hamlet.world_state.types import AgentState, StructureType

logger = logging.getLogger(__name__)

__all__ = ["AgentInferenceEngine"]


class AgentInferenceEngine:
    """Infers agent spawn, type, and lifecycle from hook events."""

    ZOMBIE_THRESHOLD_SECONDS: int = 300

    def __init__(
        self,
        world_state: "WorldStateProtocol",
        summarizer: ActivitySummarizer | None = None,
        config: SimulationConfig | None = None,
    ) -> None:
        self._world_state = world_state
        self._summarizer = summarizer
        self._config = config if config is not None else SimulationConfig()
        self._state = InferenceState()

    async def process_event(self, event: InternalEvent) -> None:
        """Route an event to the appropriate hook-type handler.

        Dispatches on ``event.hook_type``:

        - **PreToolUse**: runs spawn detection, materialises any newly-inferred
          agent into world state, increments the session's active-tool counter,
          and records a ``PendingTool`` entry for later correlation.
        - **PostToolUse**: updates the session's ``ToolWindow``, infers
          ``AgentType`` from recent tool history, awards work units to structures,
          and evicts the matching ``PendingTool`` entry.
        - **Notification**: refreshes ``last_seen`` timestamps for session agents.
        - **Stop**: refreshes ``last_seen`` and logs the stop reason.
        - All other hook types: logged as a warning; no state is mutated.

        Per guiding principle 7 (graceful degradation), handler exceptions are
        caught and logged — inference failures are non-fatal.

        Args:
            event: The normalised internal event delivered by ``EventProcessor``.
        """
        try:
            if event.hook_type == HookType.PreToolUse:
                await self._handle_pre_tool_use(event)
            elif event.hook_type == HookType.PostToolUse:
                await self._handle_post_tool_use(event)
            elif event.hook_type == HookType.Notification:
                await self._handle_notification(event)
            elif event.hook_type == HookType.Stop:
                await self._handle_stop(event)
            else:
                logger.warning("process_event: unhandled hook_type %s", event.hook_type)
        except Exception:
            logger.exception("Error processing event %s", event.id)

    async def _handle_pre_tool_use(self, event: InternalEvent) -> None:
        """Handle PreToolUse events.

        Runs spawn detection first (before adding the session to state so that
        _detect_spawn can observe the missing-session condition), then
        materialises any newly-spawned agent via the world state, increments
        the session's active tool counter, and records a PendingTool entry for
        later correlation with PostToolUse.
        """
        state = self._state

        # Run spawn detection BEFORE inserting the session so _detect_spawn
        # can observe the missing-session condition for new sessions.
        result = await self._detect_spawn(event, state)

        # Add session to state if this is the first event from this session.
        if event.session_id not in state.sessions:
            state.sessions[event.session_id] = SessionState(
                session_id=event.session_id,
                project_id=event.project_id,
            )

        if result is not None:
            # Materialise the project entity first (P-5: project must exist before sessions).
            await self._world_state.get_or_create_project(event.project_id, event.project_name)
            # Materialise the session and agent in persistent world state.
            await self._world_state.get_or_create_session(
                event.session_id, event.project_id
            )
            agent = await self._world_state.get_or_create_agent(
                event.session_id, result.parent_id
            )
            # Keep the agent_ids list on the session in sync.
            session = state.sessions[event.session_id]
            if agent.id not in session.agent_ids:
                session.agent_ids.append(agent.id)
            logger.debug(
                "_handle_pre_tool_use: spawned agent %s (parent=%s) for session %s",
                agent.id,
                result.parent_id,
                event.session_id,
            )

        # Update last_seen for all agents in this session
        session = state.sessions[event.session_id]
        for agent_id in session.agent_ids:
            state.last_seen[agent_id] = event.received_at

        # Increment active tool count before recording the pending tool so
        # that subsequent concurrent events for the same session can see it.
        session.active_tools += 1

        # Record the pending tool using the event id as key.
        state.pending_tools[event.id] = PendingTool(
            session_id=event.session_id,
            tool_name=event.tool_name or "",
            tool_input=event.tool_input or {},
        )

    async def _detect_spawn(
        self, event: InternalEvent, state: InferenceState
    ) -> InferenceResult | None:
        """Determine whether *event* represents a new agent being spawned.

        Returns an :class:`InferenceResult` with ``action=SPAWN`` when a
        spawn is detected, or ``None`` when no spawn inference is possible.

        Two cases trigger a spawn:

        1. **New session** — the session has not been seen before.  There is
           no parent agent yet, so ``parent_id`` is ``None``.
        2. **Concurrent PreToolUse** — the session already has at least one
           active (in-flight) tool when this PreToolUse arrives, which
           indicates that a sub-agent is being launched.
        """
        session = state.sessions.get(event.session_id)
        if not session:
            # New session — first agent for this session.
            return InferenceResult(
                action=InferenceAction.SPAWN,
                parent_id=None,
            )

        # Concurrent PreToolUse while the session already has active tools
        # suggests a child agent spawning alongside its parent.
        if session.active_tools > 0 and event.hook_type == HookType.PreToolUse:
            parent_agent = await self._get_primary_agent(event.session_id)
            return InferenceResult(
                action=InferenceAction.SPAWN,
                parent_id=parent_agent.id if parent_agent else None,
            )

        return None

    async def _get_primary_agent(self, session_id: str) -> Any | None:
        """Return the most-recently-active agent for *session_id*, or None.

        The primary agent is used as the parent when a concurrent spawn is
        detected.  If the world state returns no agents for the session the
        method returns ``None``.
        """
        agents = await self._world_state.get_agents_by_session(session_id)
        if not agents:
            return None
        return max(agents, key=lambda a: a.last_seen)

    def _update_tool_window(self, event: InternalEvent) -> None:
        """Add *event* to the session's ToolWindow and prune stale entries.

        Creates a new ToolWindow for the session if one does not already exist.
        Events older than ``window_size`` relative to *now* are discarded so
        the window reflects only recent activity.
        """
        state = self._state
        session_id = event.session_id
        if session_id not in state.tool_windows:
            state.tool_windows[session_id] = ToolWindow(session_id=session_id)

        window = state.tool_windows[session_id]
        now = datetime.now(UTC)
        tool_name = event.tool_name or ""
        window.events.append((tool_name, now))
        # Extract meaningful input string for keyword-based inference rules.
        # For Bash events, tool_input["command"] is the shell command; for others,
        # stringify the whole dict. This avoids matching Python repr artifacts.
        if isinstance(event.tool_input, dict):
            tool_input_str = event.tool_input.get("command", str(event.tool_input))
        else:
            tool_input_str = str(event.tool_input or "")
        window.input_log.append((tool_name, tool_input_str, now))

        # Prune events that have aged out of the sliding window.
        cutoff = now - window.window_size
        window.events = [(name, ts) for name, ts in window.events if ts >= cutoff]
        window.input_log = [
            (name, inp, ts) for name, inp, ts in window.input_log if ts >= cutoff
        ]

    def _infer_type(self, session_id: str) -> AgentType:
        """Infer the AgentType for *session_id* from its ToolWindow.

        Returns ``AgentType.GENERAL`` when:
        - the window contains fewer than 10 events, or
        - no TYPE_RULE threshold is met.

        Otherwise returns the type of the first rule whose tool-frequency
        ratio meets or exceeds the rule's minimum_ratio.
        """
        state = self._state
        if session_id not in state.tool_windows:
            return AgentType.GENERAL

        window = state.tool_windows[session_id]
        total = len(window.events)
        if total < 10:
            return AgentType.GENERAL

        tool_names = [name for name, _ in window.events]

        inferred_type = AgentType.GENERAL
        for patterns, minimum_ratio, agent_type in TYPE_RULES:
            matching = sum(1 for name in tool_names if name in patterns)
            if matching / total >= minimum_ratio:
                inferred_type = agent_type
                break

        # Post-rule refinement: if EXECUTOR, check for test-running Bash commands
        # GP-4: Modular, iterable classification — TESTER refines EXECUTOR when bash is test-focused
        if inferred_type == AgentType.EXECUTOR:
            bash_events = [
                (name, inp) for name, inp, _ in window.input_log
                if name == "Bash"
            ]
            test_keywords = ("pytest", "unittest", "test_")
            if bash_events:
                test_count = sum(
                    1 for _, inp in bash_events
                    if any(kw in inp for kw in test_keywords)
                )
                if test_count / len(bash_events) >= 0.5:
                    inferred_type = AgentType.TESTER

        return inferred_type

    async def _handle_post_tool_use(self, event: InternalEvent) -> None:
        """Handle PostToolUse events — update tool window and infer agent type."""
        self._update_tool_window(event)
        inferred = self._infer_type(event.session_id)

        # Update the agent's type in world state if we can identify the agent.
        # Also update last_seen so a long-running tool call does not trigger zombie detection.
        session = self._state.sessions.get(event.session_id)
        if session and session.agent_ids:
            agent_id = session.agent_ids[0]  # primary agent for this session
            try:
                await self._world_state.update_agent(
                    agent_id,
                    inferred_type=inferred,
                    color=TYPE_COLORS.get(inferred, "white"),
                )
            except Exception:
                logger.exception(
                    "_handle_post_tool_use: failed to update agent %s type to %s",
                    agent_id,
                    inferred,
                )
            structure_type = TOOL_TO_STRUCTURE.get(event.tool_name or "")
            if structure_type is not None:
                if event.duration_ms is None:
                    units = 1  # minimum contribution for any completed tool call
                else:
                    units = max(1, int(event.duration_ms * self._config.work_unit_scale))
                try:
                    await self._world_state.add_work_units(agent_id, structure_type, units)
                except Exception:
                    logger.exception("Failed to add work units for agent %s", agent_id)
            if self._summarizer and event.tool_name:
                # Fire-and-forget: summarizer may take up to 5s — must not block event pipeline.
                asyncio.create_task(
                    self._summarize_and_update(agent_id, event.tool_name, event.tool_input or {})
                )
        if session:
            for agent_id in session.agent_ids:
                self._state.last_seen[agent_id] = event.received_at

        # Evict the matching pending tool entry (oldest match by started_at for this
        # tool_name) and decrement active_tools only when eviction succeeds.  This
        # keeps the two counters in sync: if no matching PendingTool exists the
        # active_tools count is left unchanged rather than diverging.
        tool_name = event.tool_name or ""
        matching_key = None
        oldest_started_at = None
        for key, pending in self._state.pending_tools.items():
            if pending.session_id == event.session_id and pending.tool_name == tool_name:
                if oldest_started_at is None or pending.started_at < oldest_started_at:
                    oldest_started_at = pending.started_at
                    matching_key = key
        if matching_key is not None:
            del self._state.pending_tools[matching_key]
            if session is not None:
                session.active_tools = max(0, session.active_tools - 1)
        else:
            logger.debug(
                "_handle_post_tool_use: no matching pending tool found for session=%s tool=%s",
                event.session_id,
                tool_name,
            )

        logger.debug(
            "_handle_post_tool_use: session=%s inferred_type=%s",
            event.session_id,
            inferred,
        )

    async def _handle_notification(self, event: InternalEvent) -> None:
        """Handle Notification events — update agent last_seen and log message."""
        session = self._state.sessions.get(event.session_id)
        if session:
            for agent_id in session.agent_ids:
                self._state.last_seen[agent_id] = event.received_at
        if event.notification_message:
            logger.debug("Notification [session=%s]: %s", event.session_id, event.notification_message)

    async def _handle_stop(self, event: InternalEvent) -> None:
        session = self._state.sessions.get(event.session_id)
        if session:
            for agent_id in session.agent_ids:
                self._state.last_seen[agent_id] = event.received_at

        if event.stop_reason == "tool":
            keys_to_evict = [
                k
                for k, pt in self._state.pending_tools.items()
                if pt.session_id == event.session_id
            ]
            for key in keys_to_evict:
                del self._state.pending_tools[key]
            if session is not None:
                session.active_tools = max(0, session.active_tools - len(keys_to_evict))
            if session:
                for agent_id in list(session.agent_ids):
                    try:
                        await self._world_state.update_agent(agent_id, state=AgentState.ZOMBIE)
                        self._state.zombie_since[agent_id] = datetime.now(UTC)
                    except Exception:
                        logger.exception("_handle_stop: failed to zombie agent %s", agent_id)

        elif event.stop_reason in ("stop", "end_turn"):
            if session:
                for agent_id in list(session.agent_ids):
                    try:
                        await self._world_state.despawn_agent(agent_id)
                        self._state.last_seen.pop(agent_id, None)
                        self._state.zombie_since.pop(agent_id, None)
                    except Exception:
                        logger.exception("_handle_stop: failed to despawn agent %s", agent_id)

        if event.stop_reason:
            logger.debug("Stop [session=%s, reason=%s]", event.session_id, event.stop_reason)

    def _check_zombie(self, agent_id: str) -> bool:
        """Return True if the agent has not been seen within ZOMBIE_THRESHOLD_SECONDS."""
        last_seen = self._state.last_seen.get(agent_id)
        if last_seen is None:
            return False
        elapsed = (datetime.now(UTC) - last_seen).total_seconds()
        return elapsed >= self.ZOMBIE_THRESHOLD_SECONDS

    async def _summarize_and_update(self, agent_id: str, tool_name: str, tool_input: dict) -> None:
        """Background helper: call summarizer and update agent current_activity.

        Runs as a fire-and-forget task so it never blocks the event pipeline.
        Errors are caught and logged at ERROR level (GP-7).
        """
        try:
            summary = await self._summarizer.summarize(tool_name, tool_input)
            await self._world_state.update_agent(agent_id, current_activity=summary)
        except Exception:
            logger.exception("Failed to update activity summary for agent %s", agent_id)

    async def tick(self) -> None:
        """Perform a periodic inference maintenance pass.

        Called by ``SimulationEngine`` on each simulation step. Currently runs
        zombie detection: agents whose ``last_seen`` timestamp is older than
        ``ZOMBIE_THRESHOLD_SECONDS`` are marked ``AgentState.ZOMBIE`` in world
        state. Stale ``PendingTool`` entries (PreToolUse with no matching
        PostToolUse within the threshold window) are also evicted and the
        corresponding session's ``active_tools`` counter is decremented.

        Errors are caught and logged internally — this method never raises.
        """
        await self._update_zombie_states()

    async def _update_zombie_states(self) -> None:
        """Iterate all known agents and mark stale ones as zombie via world state.

        Called periodically by the simulation engine.

        Only agents registered via ``_handle_pre_tool_use`` are evaluated —
        those are the only agents that populate ``_state.last_seen``.

        Also evicts pending_tools entries older than ZOMBIE_THRESHOLD_SECONDS
        (tool calls that started in PreToolUse but never received a PostToolUse),
        decrementing the corresponding session's active_tools count so the two
        stay in sync.
        """
        for agent_id in list(self._state.last_seen.keys()):
            if self._check_zombie(agent_id):
                try:
                    await self._world_state.update_agent(agent_id, state=AgentState.ZOMBIE)
                except Exception:
                    logger.exception(
                        "_update_zombie_states: failed to update agent %s", agent_id
                    )

        # Evict stale pending_tools entries whose PreToolUse was never matched
        # by a PostToolUse within the zombie threshold window.
        cutoff = datetime.now(UTC) - timedelta(seconds=self.ZOMBIE_THRESHOLD_SECONDS)
        stale_keys = [
            k for k, p in self._state.pending_tools.items() if p.started_at < cutoff
        ]
        for k in stale_keys:
            pending = self._state.pending_tools.pop(k)
            session = self._state.sessions.get(pending.session_id)
            if session is not None:
                session.active_tools = max(0, session.active_tools - 1)
            logger.debug(
                "_update_zombie_states: evicted stale pending tool session=%s tool=%s started_at=%s",
                pending.session_id,
                pending.tool_name,
                pending.started_at,
            )

    def get_inference_state(self) -> InferenceState:
        """Return the live inference state for debugging.

        The returned object is the engine's internal state — callers must
        not mutate it.
        """
        return self._state
