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
            f"{self._base_url}/hamlet/state",
            timeout=aiohttp.ClientTimeout(total=5),
        ) as r:
            return await r.json()

    async def fetch_events(self) -> list[dict]:
        """Fetch the recent event log from the daemon."""
        if self._session is None:
            return []
        async with self._session.get(
            f"{self._base_url}/hamlet/events",
            timeout=aiohttp.ClientTimeout(total=5),
        ) as r:
            data = await r.json()
            return data.get("events", [])

    async def fetch_terrain(self, x: int, y: int) -> dict:
        """Fetch terrain data for position (x, y) from the daemon.

        Returns:
            dict with "terrain" (str) and "passable" (bool) fields.
        """
        if self._session is None:
            return {"terrain": "plain", "passable": True}
        async with self._session.get(
            f"{self._base_url}/hamlet/terrain/{x}/{y}",
            timeout=aiohttp.ClientTimeout(total=5),
        ) as r:
            return await r.json()


class RemoteTerrainGrid:
    """Terrain grid that fetches terrain from a remote daemon.

    Provides the same interface as TerrainGrid but uses HTTP calls
    to fetch terrain on demand. Caches results to avoid repeated requests.
    """

    def __init__(self, provider: RemoteStateProvider):
        self._provider = provider
        self._cache: dict[tuple[int, int], str] = {}

    async def get_terrain_at(self, x: int, y: int) -> str:
        """Return terrain type string at position (x, y)."""
        key = (x, y)
        if key in self._cache:
            return self._cache[key]

        data = await self._provider.fetch_terrain(x, y)
        terrain = data.get("terrain", "plain")
        self._cache[key] = terrain
        return terrain

    def get_terrain_in_bounds(
        self, bounds: "tuple[int, int, int, int]"
    ) -> dict[tuple[int, int], str]:
        """Synchronously return cached terrain for positions in bounds.

        Note: This only returns already-cached terrain. The WorldView
        should call get_terrain_at() for positions it needs before
        calling this method.

        Args:
            bounds: (min_x, min_y, max_x, max_y) bounds

        Returns:
            Dict mapping (x, y) to terrain type string for cached positions.
        """
        min_x, min_y, max_x, max_y = bounds
        result: dict[tuple[int, int], str] = {}
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                key = (x, y)
                if key in self._cache:
                    result[key] = self._cache[key]
        return result

    async def prefetch_bounds(
        self, min_x: int, min_y: int, max_x: int, max_y: int
    ) -> None:
        """Pre-fetch terrain for all positions in bounds.

        This should be called before get_terrain_in_bounds() to ensure
        terrain data is available for rendering.
        """
        import asyncio

        async def fetch_one(x: int, y: int) -> None:
            if (x, y) not in self._cache:
                await self.get_terrain_at(x, y)

        tasks = [
            fetch_one(x, y)
            for y in range(min_y, max_y + 1)
            for x in range(min_x, max_x + 1)
        ]
        if tasks:
            await asyncio.gather(*tasks)
