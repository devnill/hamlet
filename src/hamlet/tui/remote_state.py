"""RemoteStateProvider — HTTP client for polling a running Hamlet daemon."""
from __future__ import annotations

import aiohttp


class RemoteStateProvider:
    """HTTP polling client that fetches world state from a running daemon."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self._base_url = base_url
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """Open the underlying HTTP session."""
        self._session = aiohttp.ClientSession()

    async def stop(self) -> None:
        """Close the underlying HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def check_health(self) -> bool:
        """Return True if the daemon is reachable and healthy."""
        if self._session is None:
            return False
        try:
            async with self._session.get(
                f"{self._base_url}/hamlet/health",
                timeout=aiohttp.ClientTimeout(total=2),
            ) as r:
                return r.status == 200
        except Exception:
            return False

    async def fetch_state(self) -> dict:
        """Fetch the full world state snapshot from the daemon."""
        if self._session is None:
            return {}
        async with self._session.get(
            f"{self._base_url}/hamlet/state"
        ) as r:
            return await r.json()

    async def fetch_events(self) -> list[dict]:
        """Fetch the recent event log from the daemon."""
        if self._session is None:
            return []
        async with self._session.get(
            f"{self._base_url}/hamlet/events"
        ) as r:
            data = await r.json()
            return data.get("events", [])
