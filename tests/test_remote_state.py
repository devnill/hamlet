"""Tests for RemoteStateProvider."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from hamlet.tui.remote_state import RemoteStateProvider


async def test_fetch_state_passes_timeout():
    """fetch_state passes timeout=ClientTimeout(total=5) to session.get."""
    provider = RemoteStateProvider()
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"agents": []})
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_session.get = MagicMock(return_value=mock_cm)
    provider._session = mock_session

    await provider.fetch_state()

    mock_session.get.assert_called_once()
    _, kwargs = mock_session.get.call_args
    timeout = kwargs.get("timeout")
    assert isinstance(timeout, aiohttp.ClientTimeout)
    assert timeout.total == 5


async def test_fetch_events_passes_timeout():
    """fetch_events passes timeout=ClientTimeout(total=5) to session.get."""
    provider = RemoteStateProvider()
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"events": []})
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_session.get = MagicMock(return_value=mock_cm)
    provider._session = mock_session

    await provider.fetch_events()

    mock_session.get.assert_called_once()
    _, kwargs = mock_session.get.call_args
    timeout = kwargs.get("timeout")
    assert isinstance(timeout, aiohttp.ClientTimeout)
    assert timeout.total == 5


async def test_fetch_state_propagates_timeout_error():
    """fetch_state propagates aiohttp.ServerTimeoutError when a ClientTimeout fires."""
    provider = RemoteStateProvider()
    mock_session = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ServerTimeoutError())
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_session.get = MagicMock(return_value=mock_cm)
    provider._session = mock_session

    with pytest.raises(aiohttp.ServerTimeoutError):
        await provider.fetch_state()


async def test_fetch_events_propagates_timeout_error():
    """fetch_events propagates aiohttp.ServerTimeoutError when a ClientTimeout fires."""
    provider = RemoteStateProvider()
    mock_session = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ServerTimeoutError())
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_session.get = MagicMock(return_value=mock_cm)
    provider._session = mock_session

    with pytest.raises(aiohttp.ServerTimeoutError):
        await provider.fetch_events()


async def test_fetch_state_returns_empty_when_no_session():
    """fetch_state returns {} when the session has not been started."""
    provider = RemoteStateProvider()
    result = await provider.fetch_state()
    assert result == {}


async def test_fetch_events_returns_empty_when_no_session():
    """fetch_events returns [] when the session has not been started."""
    provider = RemoteStateProvider()
    result = await provider.fetch_events()
    assert result == []


async def test_fetch_terrain_passes_timeout():
    """fetch_terrain passes timeout=ClientTimeout(total=5) to session.get."""
    provider = RemoteStateProvider()
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"terrain": "plain", "passable": True})
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_session.get = MagicMock(return_value=mock_cm)
    provider._session = mock_session

    await provider.fetch_terrain(10, 20)

    mock_session.get.assert_called_once()
    args, kwargs = mock_session.get.call_args
    assert args[0] == "http://localhost:8080/hamlet/terrain/10/20"
    timeout = kwargs.get("timeout")
    assert isinstance(timeout, aiohttp.ClientTimeout)
    assert timeout.total == 5


async def test_fetch_terrain_propagates_timeout_error():
    """fetch_terrain propagates aiohttp.ServerTimeoutError when a ClientTimeout fires."""
    provider = RemoteStateProvider()
    mock_session = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ServerTimeoutError())
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_session.get = MagicMock(return_value=mock_cm)
    provider._session = mock_session

    with pytest.raises(aiohttp.ServerTimeoutError):
        await provider.fetch_terrain(0, 0)


async def test_fetch_terrain_returns_default_when_no_session():
    """fetch_terrain returns default values when the session has not been started."""
    provider = RemoteStateProvider()
    result = await provider.fetch_terrain(0, 0)
    assert result == {"terrain": "plain", "passable": True}
