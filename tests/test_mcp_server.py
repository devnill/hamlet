"""Tests for MCP server implementation."""
from __future__ import annotations

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from hamlet.mcp_server.server import MCPServer


class TestMCPServer:
    """Tests for the MCPServer class."""

    def test_init_creates_event_queue(self) -> None:
        """Test that MCPServer.__init__ creates an event queue."""
        server = MCPServer()
        queue = server.get_event_queue()
        assert queue is not None
        assert isinstance(queue, asyncio.Queue)
        assert server.is_running() is False

    @pytest.mark.asyncio
    async def test_start_creates_background_task(self) -> None:
        """Test that start() registers handlers and sets running state."""
        server = MCPServer()

        with patch('hamlet.mcp_server.server.Server') as mock_server_class, \
             patch('hamlet.mcp_server.server.register_handlers'), \
             patch('hamlet.mcp_server.server.aiohttp.web.AppRunner') as mock_runner_cls, \
             patch('hamlet.mcp_server.server.aiohttp.web.TCPSite') as mock_site_cls:

            mock_runner = AsyncMock()
            mock_runner_cls.return_value = mock_runner
            mock_runner.setup = AsyncMock()

            mock_site = AsyncMock()
            mock_site_cls.return_value = mock_site
            mock_site.start = AsyncMock()

            await server.start()

            assert server.is_running() is True

            await server.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self) -> None:
        """Test that stop() cleans up and sets is_running() to False."""
        server = MCPServer()

        with patch('hamlet.mcp_server.server.Server'), \
             patch('hamlet.mcp_server.server.register_handlers'), \
             patch('hamlet.mcp_server.server.aiohttp.web.AppRunner') as mock_runner_cls, \
             patch('hamlet.mcp_server.server.aiohttp.web.TCPSite') as mock_site_cls:

            mock_runner = AsyncMock()
            mock_runner_cls.return_value = mock_runner
            mock_runner.setup = AsyncMock()
            mock_runner.cleanup = AsyncMock()

            mock_site = AsyncMock()
            mock_site_cls.return_value = mock_site
            mock_site.start = AsyncMock()

            await server.start()
            assert server.is_running() is True

            await server.stop()

            assert server.is_running() is False

    @pytest.mark.asyncio
    async def test_health_endpoint(self) -> None:
        """Test that _handle_health returns HTTP 200 with {"status": "ok"}."""
        server = MCPServer()
        request = MagicMock()
        response = await server._handle_health(request)
        assert response.status == 200
        import json
        body = json.loads(response.body)
        assert body == {"status": "ok"}
