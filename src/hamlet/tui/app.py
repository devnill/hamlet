"""Hamlet TUI application entry point."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding

if TYPE_CHECKING:
    from hamlet.world_state import WorldStateManager  # type: ignore[import]
    from hamlet.viewport import ViewportManager  # type: ignore[import]
    from hamlet.event_processing import EventProcessor  # type: ignore[import]
    from hamlet.tui.remote_state import RemoteStateProvider  # type: ignore[import]
    from hamlet.tui.remote_world_state import RemoteWorldState  # type: ignore[import]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stub widget classes for widgets defined in later work items (063-065).
# These will be replaced by the real implementations when those items land.
# ---------------------------------------------------------------------------

try:
    from textual.widget import Widget as _Widget
except ImportError:
    _Widget = object  # type: ignore[assignment,misc]

try:
    from hamlet.tui.status_bar import StatusBar  # type: ignore[import]
except ImportError:
    class StatusBar(_Widget):  # type: ignore[no-redef,misc]
        """Placeholder StatusBar — implemented in work item 063."""

        DEFAULT_CSS = """
        StatusBar {
            height: 1fr;
        }
        """


try:
    from hamlet.tui.world_view import WorldView  # type: ignore[import]
except ImportError:
    class WorldView(_Widget):  # type: ignore[no-redef,misc]
        """Placeholder WorldView — implemented in work item 064."""

        DEFAULT_CSS = """
        WorldView {
            height: 20fr;
        }
        """


try:
    from hamlet.tui.event_log import EventLog  # type: ignore[import]
except ImportError:
    class EventLog(_Widget):  # type: ignore[no-redef,misc]
        """Placeholder EventLog — implemented in work item 065."""

        DEFAULT_CSS = """
        EventLog {
            height: 5fr;
        }
        """


try:
    from hamlet.tui.legend import LegendOverlay  # type: ignore[import]
except ImportError:
    class LegendOverlay(_Widget):  # type: ignore[no-redef,misc]
        """Placeholder LegendOverlay — implemented in work item 066."""


try:
    from hamlet.tui.help_overlay import HelpOverlay  # type: ignore[import]
except ImportError:
    from textual.widgets import Static as _Static  # type: ignore[assignment]

    class HelpOverlay(_Static):  # type: ignore[no-redef,misc]
        """Placeholder HelpOverlay."""


# ---------------------------------------------------------------------------
# HamletApp
# ---------------------------------------------------------------------------

class HamletApp(App):
    """Main Textual application for the Hamlet world simulator TUI."""

    LAYERS = ("default", "overlay")

    CSS = """
    Screen {
        layout: grid;
        grid-rows: 1fr 20fr 5fr;
        grid-columns: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("h", "scroll_left", "Scroll Left", show=False),
        Binding("left", "scroll_left", "Scroll Left", show=False),
        Binding("l", "scroll_right", "Scroll Right", show=False),
        Binding("right", "scroll_right", "Scroll Right", show=False),
        Binding("j", "scroll_down", "Scroll Down", show=False),
        Binding("down", "scroll_down", "Scroll Down", show=False),
        Binding("k", "scroll_up", "Scroll Up", show=False),
        Binding("up", "scroll_up", "Scroll Up", show=False),
        Binding("/", "toggle_legend", "Legend", show=True),
        Binding("?", "toggle_help", "Help", show=True),
        Binding("f", "toggle_follow", "Follow", show=True),
    ]

    def __init__(
        self,
        world_state: "WorldStateManager",  # type: ignore[name-defined]
        viewport: "ViewportManager",  # type: ignore[name-defined]
        event_processor: "EventProcessor | None" = None,  # type: ignore[name-defined]
        remote_provider: "RemoteStateProvider | None" = None,  # type: ignore[name-defined]
    ) -> None:
        super().__init__()
        self._world_state = world_state
        self._viewport = viewport
        self._event_processor = event_processor
        self._remote_provider = remote_provider

    def compose(self) -> ComposeResult:
        """Yield the main widgets and the legend overlay."""
        terrain_grid = getattr(self._world_state, "terrain_grid", None)
        yield StatusBar()
        yield WorldView(self._world_state, self._viewport, terrain_grid)
        yield EventLog()
        yield LegendOverlay()
        yield HelpOverlay()

    def on_mount(self) -> None:
        """Set up a 30 FPS refresh interval and a 10 Hz state polling interval after the app mounts."""
        self.set_interval(1 / 30, self._refresh_world)
        if self._remote_provider is not None:
            # Kick off the async refresh task
            self._kickoff_refresh_remote_state()

    def _kickoff_refresh_remote_state(self) -> None:
        """Kick off the periodic terrain refresh."""
        import asyncio
        async def _periodic_refresh():
            while True:
                try:
                    await self._refresh_remote_state()
                except Exception as e:
                    logger.debug("_periodic_refresh error: %s", e)
                await asyncio.sleep(0.5)
        asyncio.create_task(_periodic_refresh())

    async def _refresh_remote_state(self) -> None:
        """Refresh remote world state from the daemon (viewer mode only)."""
        try:
            if hasattr(self._world_state, "refresh"):
                await self._world_state.refresh()

            # Prefetch terrain for visible viewport
            terrain_grid = getattr(self._world_state, "terrain_grid", None)
            if terrain_grid is not None:
                bounds = self._viewport.get_visible_bounds()
                await terrain_grid.prefetch_bounds(
                    bounds.min_x, bounds.min_y, bounds.max_x, bounds.max_y
                )
        except Exception as exc:
            logger.debug("_refresh_remote_state: failed: %s", exc)

    def _refresh_world(self) -> None:
        """Refresh world state — stub, implemented in a later work item."""
        pass

    async def _update_state(self) -> None:
        """Poll world state at 10 Hz and update reactive widget properties."""
        try:
            # Update viewport center for follow mode first, then read current state
            await self._viewport.update()
            viewport_state = self._viewport.get_viewport_state()
            bounds = self._viewport.get_visible_bounds()

            agents_list = await self._world_state.get_agents_in_view(bounds)

            # Update StatusBar
            try:
                status_bar = self.query_one(StatusBar)
                structures_list = await self._world_state.get_structures_in_view(bounds)
                status_bar.agent_count = len(agents_list)
                status_bar.structure_count = len(structures_list)
                status_bar.viewport_pos = (viewport_state.center.x, viewport_state.center.y)
                # Get village nearest to viewport center
                village = await self._world_state.get_nearest_village_to(
                    viewport_state.center.x, viewport_state.center.y
                )
                status_bar.village_name = village.name if village else ""
                # Display current_activity of the globally most recently active agent.
                # Use all agents, not just viewport-visible ones, so activity is
                # always shown regardless of viewport position.
                all_agents = await self._world_state.get_all_agents()
                if all_agents:
                    most_recent = max(all_agents, key=lambda a: a.last_seen)
                    status_bar.current_activity = most_recent.current_activity or ""
                else:
                    status_bar.current_activity = ""
            except Exception as exc:
                logger.debug("_update_state: StatusBar update failed: %s", exc)

            # Update EventLog
            try:
                event_log_widget = self.query_one(EventLog)
                events = await self._world_state.get_event_log(limit=100)
                event_log_widget.events = events
            except Exception as exc:
                logger.debug("_update_state: EventLog update failed: %s", exc)

        except Exception as exc:
            logger.debug("_update_state: failed: %s", exc)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_scroll_left(self) -> None:
        """Scroll the viewport left by one cell."""
        self._viewport.scroll(-1, 0)

    def action_scroll_right(self) -> None:
        """Scroll the viewport right by one cell."""
        self._viewport.scroll(1, 0)

    def action_scroll_up(self) -> None:
        """Scroll the viewport up by one cell."""
        self._viewport.scroll(0, -1)

    def action_scroll_down(self) -> None:
        """Scroll the viewport down by one cell."""
        self._viewport.scroll(0, 1)

    def action_toggle_legend(self) -> None:
        """Toggle the key-bindings legend overlay visibility."""
        try:
            overlay = self.query_one(LegendOverlay)
            overlay.display = not overlay.display
        except Exception as exc:
            logger.debug("toggle_legend: %s", exc)

    def action_toggle_help(self) -> None:
        """Toggle the help overlay visibility."""
        try:
            overlay = self.query_one(HelpOverlay)
            overlay.display = not overlay.display
        except Exception as exc:
            logger.debug("toggle_help: %s", exc)

    async def action_toggle_follow(self) -> None:
        """Toggle follow mode: follow most recently active agent, or revert to free mode."""
        state = self._viewport.get_viewport_state()
        if state.follow_mode == "center" and state.follow_target is not None:
            # Currently following — revert to free mode at current center
            self._viewport.set_center(state.center)
        else:
            # Enable follow on most recently seen active agent
            agents = await self._world_state.get_all_agents()
            if agents:
                target = max(agents, key=lambda a: a.last_seen)
                self._viewport.auto_follow(target.id)

    def action_quit(self) -> None:
        """Exit the application."""
        self.exit()

    async def run_async(self, **kwargs: object) -> None:  # type: ignore[override]
        """Start the Hamlet TUI application asynchronously."""
        await super().run_async(**kwargs)
