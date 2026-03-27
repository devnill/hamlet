"""State fetcher for the Kitty viewer app.

Uses urllib.request (stdlib) to fetch world state, events, and terrain
data from the hamlet daemon HTTP API.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field

from hamlet.world_state.parsers import (
    parse_agent,
    parse_structure,
    parse_village,
    try_parse,
)


@dataclass
class StateSnapshot:
    """A point-in-time snapshot of the daemon's world state."""

    agents: list = field(default_factory=list)
    structures: list = field(default_factory=list)
    villages: list = field(default_factory=list)
    terrain_data: dict = field(default_factory=dict)
    event_log: list = field(default_factory=list)


class StateFetcher:
    """Fetches state from the hamlet daemon over HTTP.

    Parameters
    ----------
    base_url:
        Base URL of the daemon HTTP server, e.g. ``http://localhost:8080``.
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def check_health(self) -> bool:
        """Return True if the daemon health endpoint responds 200."""
        try:
            with urllib.request.urlopen(f"{self._base_url}/hamlet/health", timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    def fetch_snapshot(
        self, center_x: int, center_y: int, half_w: int, half_h: int
    ) -> StateSnapshot:
        """Fetch a full state snapshot from the daemon.

        Parameters
        ----------
        center_x, center_y:
            Current viewport center in world coordinates.
        half_w, half_h:
            Half-width and half-height of the visible area, used to
            request the correct terrain bounds.
        """
        snap = StateSnapshot()

        # Fetch state (agents, structures, villages)
        try:
            with urllib.request.urlopen(
                f"{self._base_url}/hamlet/state", timeout=2
            ) as r:
                state = json.loads(r.read())
            snap.agents = [
                a for d in state.get("agents", [])
                if (a := try_parse(parse_agent, d)) is not None
            ]
            snap.structures = [
                s for d in state.get("structures", [])
                if (s := try_parse(parse_structure, d)) is not None
            ]
            snap.villages = [
                v for d in state.get("villages", [])
                if (v := try_parse(parse_village, d)) is not None
            ]
        except Exception:
            pass

        # Fetch events
        try:
            with urllib.request.urlopen(
                f"{self._base_url}/hamlet/events", timeout=2
            ) as r:
                data = json.loads(r.read())
            snap.event_log = [
                e.get("summary", "")
                for e in data.get("events", [])
                if "summary" in e
            ]
        except Exception:
            pass

        # Fetch terrain (Q-11 fix: uses /hamlet/terrain/bounds/...)
        try:
            min_x = center_x - half_w
            max_x = center_x + half_w
            min_y = center_y - half_h
            max_y = center_y + half_h
            url = (
                f"{self._base_url}/hamlet/terrain/bounds"
                f"/{min_x}/{min_y}/{max_x}/{max_y}"
            )
            with urllib.request.urlopen(url, timeout=5) as r:
                raw = json.loads(r.read())
            for k, v in raw.items():
                parts = k.split(",")
                if len(parts) == 2:
                    try:
                        snap.terrain_data[(int(parts[0]), int(parts[1]))] = v
                    except ValueError:
                        continue
        except Exception:
            pass

        return snap


__all__ = ["StateSnapshot", "StateFetcher"]
