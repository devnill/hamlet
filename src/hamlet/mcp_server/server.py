"""MCP Server implementation for receiving hook events."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import aiohttp.web

if TYPE_CHECKING:
    from hamlet.protocols import WorldStateProtocol
from mcp.server import Server

from .handlers import register_handlers
from .serializers import serialize_events, serialize_state
from .validation import validate_event

logger = logging.getLogger("hamlet.mcp_server")


class MCPServer:
    """MCP Server that receives hook events from Claude Code.

    This server listens on an HTTP endpoint and maintains an event queue
    that other components can consume. Hook scripts deliver events via
    JSON-RPC POST to /hamlet/event.

    Attributes:
        _event_queue: asyncio.Queue for storing received events.
        _server: The underlying MCP Server instance (for handler registration).
        _running: Flag indicating if the server is currently running.
    """

    def __init__(self, world_state: "WorldStateProtocol | None" = None, port: int = 8080, animation_manager: Any = None) -> None:
        """Initialize the MCP server with an empty event queue."""
        self._event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._server: Server | None = None
        self._running: bool = False
        self._world_state = world_state
        self._port = port
        self._animation_manager = animation_manager
        self._http_runner: aiohttp.web.AppRunner | None = None

    async def start(self) -> None:
        """Start the MCP server and begin listening for HTTP connections.

        Initialises the underlying ``mcp.server.Server`` instance and registers
        MCP tool handlers, then starts an aiohttp HTTP server on the configured
        port with the following routes:

        - ``POST /hamlet/event`` — receives validated hook events and enqueues them.
        - ``GET  /hamlet/health`` — lightweight liveness check.
        - ``GET  /hamlet/state``  — serialised world state snapshot.
        - ``GET  /hamlet/events`` — recent event log.

        Per guiding principle 7 (graceful degradation), errors during MCP
        initialisation or HTTP binding are logged but do not crash the application.
        A second call while the server is already running is a no-op (logged as a
        warning).
        """
        if self._running:
            logger.warning("MCP server already running")
            return

        try:
            self._server = Server("hamlet")
            register_handlers(self._server, self._event_queue, self._world_state)
            self._running = True
            logger.info("MCP server 'hamlet' started")
        except Exception as e:
            logger.error("Failed to start MCP server: %s", e)
            self._running = False
            self._server = None
            # Per guiding principle 7, don't crash - just log and continue

        # Start HTTP event endpoint
        event_queue = self._event_queue

        async def handle_hamlet_event(request: aiohttp.web.Request) -> aiohttp.web.Response:
            if request.method != "POST":
                return aiohttp.web.json_response(
                    {"error": "method not allowed"}, status=405, headers={"Allow": "POST"}
                )
            try:
                body = await request.json()
            except Exception:
                logger.warning("Invalid JSON in HTTP event request")
                return aiohttp.web.json_response({"error": "invalid JSON"}, status=400)
            result = validate_event(body)
            if not result.valid:
                # validate_event logs internally; no duplicate warning here
                return aiohttp.web.json_response({"error": result.error}, status=400)
            await event_queue.put(result.payload["params"])
            return aiohttp.web.json_response({"status": "ok"})

        app = aiohttp.web.Application()
        app.router.add_route("*", "/hamlet/event", handle_hamlet_event)
        app.router.add_get("/hamlet/health", self._handle_health)
        app.router.add_get("/hamlet/state", self._handle_state)
        app.router.add_get("/hamlet/events", self._handle_events)

        try:
            runner = aiohttp.web.AppRunner(app)
            await runner.setup()
            # Assign before site.start() so stop() can always clean up on failure
            self._http_runner = runner
            site = aiohttp.web.TCPSite(runner, "localhost", self._port)
            await site.start()
            logger.info("HTTP event endpoint listening on http://localhost:%d/hamlet/event", self._port)
        except Exception as e:
            logger.error(
                "HTTP server failed to start: %s (continuing without HTTP endpoint)", e
            )
            if self._http_runner is not None:
                try:
                    await self._http_runner.cleanup()
                except Exception:
                    pass
                self._http_runner = None

    async def _handle_state(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Handle GET /hamlet/state — return serialised world state as JSON.

        Delegates to ``serialize_state`` and returns the result as a JSON
        response. Returns HTTP 500 with an error message on failure.

        Args:
            request: The incoming aiohttp request object.

        Returns:
            A JSON response containing the full serialised world state, or an
            error dict with HTTP 500 on serialisation failure.
        """
        try:
            data = await serialize_state(self._world_state, self._animation_manager)
            return aiohttp.web.json_response(data)
        except Exception as e:
            return aiohttp.web.json_response({"error": str(e)}, status=500)

    async def _handle_events(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Handle GET /hamlet/events — return the recent event log as JSON.

        Delegates to ``serialize_events`` and returns the result as a JSON
        response. Returns HTTP 500 with an error message on failure.

        Args:
            request: The incoming aiohttp request object.

        Returns:
            A JSON response containing the recent event log, or an error dict
            with HTTP 500 on serialisation failure.
        """
        try:
            data = await serialize_events(self._world_state)
            return aiohttp.web.json_response(data)
        except Exception as e:
            return aiohttp.web.json_response({"error": str(e)}, status=500)

    async def _handle_health(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Return a health check response.

        Always returns HTTP 200 with {"status": "ok"} per GP-7 (graceful degradation).
        """
        return aiohttp.web.json_response({"status": "ok"})

    async def stop(self) -> None:
        """Gracefully shut down the server.

        Tears down the aiohttp HTTP runner and marks the server as stopped.
        """
        if not self._running:
            return

        logger.info("Stopping MCP server")
        self._running = False
        self._server = None

        if self._http_runner:
            await self._http_runner.cleanup()
            self._http_runner = None

        logger.info("MCP server stopped")

    def get_event_queue(self) -> asyncio.Queue[dict[str, Any]]:
        """Return the event queue for consuming received events.

        The queue is unbounded to prevent blocking on high event throughput.
        Components can await queue.get() to receive events.

        Returns:
            The asyncio.Queue containing received hook events.
        """
        return self._event_queue

    def is_running(self) -> bool:
        """Check if the server is currently running.

        Returns:
            True if the server is running, False otherwise.
        """
        return self._running