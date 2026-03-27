"""Functional integration tests for the Kitty viewer pipeline.

These tests feed real daemon API responses (captured as JSON fixtures) through
the full parse → render pipeline.  Only the HTTP transport layer is mocked.
If the daemon response schema changes, or if dataclass attribute access breaks,
these tests will catch it.
"""
from __future__ import annotations

import io
import json
import os
import unittest.mock as mock
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> bytes:
    """Return fixture file contents as bytes."""
    return (FIXTURES_DIR / name).read_bytes()


# ---------------------------------------------------------------------------
# Helpers to build a mock urlopen that returns fixture JSON
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Minimal file-like object returned by urllib.request.urlopen mock."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self.status = 200

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def _make_urlopen(routes: dict[str, str]):
    """Return a mock urlopen that serves fixture data based on URL patterns."""

    def _urlopen(url, timeout=None):
        for pattern, fixture_name in routes.items():
            if pattern in url:
                return _FakeResponse(_load_fixture(fixture_name))
        raise ValueError(f"No fixture route for URL: {url}")

    return _urlopen


# ---------------------------------------------------------------------------
# WI-285 — StateFetcher parses real API responses into dataclasses
# ---------------------------------------------------------------------------

class TestStateFetcherParsesRealAPIResponse:
    """Feed real daemon JSON through the parse pipeline; verify dataclass output."""

    @pytest.fixture()
    def snapshot(self):
        from hamlet.gui.kitty.state_fetcher import StateFetcher

        routes = {
            "/hamlet/state": "daemon_state_response.json",
            "/hamlet/events": "daemon_events_response.json",
            "/hamlet/terrain/bounds": "daemon_terrain_response.json",
        }
        with mock.patch(
            "hamlet.gui.kitty.state_fetcher.urllib.request.urlopen",
            side_effect=_make_urlopen(routes),
        ):
            fetcher = StateFetcher("http://localhost:8080")
            return fetcher.fetch_snapshot(0, 0, 40, 20)

    def test_agents_are_dataclass_objects(self, snapshot):
        from hamlet.world_state.types import Agent

        assert len(snapshot.agents) > 0, "fixture must have at least one agent"
        for agent in snapshot.agents:
            assert isinstance(agent, Agent), (
                f"Expected Agent dataclass, got {type(agent)}"
            )
            # Attribute access must not raise AttributeError
            _ = agent.id
            _ = agent.position.x
            _ = agent.position.y
            _ = agent.inferred_type

    def test_structures_are_dataclass_objects(self, snapshot):
        from hamlet.world_state.types import Structure

        assert len(snapshot.structures) > 0
        for struct in snapshot.structures:
            assert isinstance(struct, Structure), (
                f"Expected Structure dataclass, got {type(struct)}"
            )
            _ = struct.id
            _ = struct.position.x
            _ = struct.position.y
            _ = struct.type

    def test_villages_are_dataclass_objects(self, snapshot):
        from hamlet.world_state.types import Village

        assert len(snapshot.villages) > 0
        for village in snapshot.villages:
            assert isinstance(village, Village), (
                f"Expected Village dataclass, got {type(village)}"
            )
            _ = village.id
            _ = village.center.x
            _ = village.center.y

    def test_event_log_is_strings(self, snapshot):
        # Event log entries are summary strings extracted from raw dicts
        for entry in snapshot.event_log:
            assert isinstance(entry, str)

    def test_terrain_data_has_tuple_keys(self, snapshot):
        # Terrain dict must use (x, y) tuple keys, not string keys
        assert len(snapshot.terrain_data) > 0
        for key in snapshot.terrain_data:
            assert isinstance(key, tuple) and len(key) == 2, (
                f"Expected (x, y) tuple key, got {key!r}"
            )
            x, y = key
            assert isinstance(x, int) and isinstance(y, int)

    def test_malformed_agent_is_skipped(self):
        """_try_parse must skip malformed entries rather than crash."""
        from hamlet.gui.kitty.state_fetcher import StateFetcher

        bad_state = json.dumps({
            "agents": [
                {"id": "good", "position": {"x": 1, "y": 2}},
                {"inferred_type": "NOT_A_VALID_TYPE_XYZ"},  # will fail enum
                {"id": "good2", "position": {"x": 3, "y": 4}},
            ],
            "structures": [],
            "villages": [],
        }).encode()

        routes = {
            "/hamlet/state": None,
            "/hamlet/events": None,
            "/hamlet/terrain/bounds": None,
        }

        def _urlopen(url, timeout=None):
            if "/hamlet/state" in url:
                return _FakeResponse(bad_state)
            return _FakeResponse(b'{"events":[]}')

        with mock.patch(
            "hamlet.gui.kitty.state_fetcher.urllib.request.urlopen",
            side_effect=_urlopen,
        ):
            fetcher = StateFetcher("http://localhost:8080")
            snap = fetcher.fetch_snapshot(0, 0, 10, 10)

        # Bad entry skipped; 2 good entries remain (invalid enum causes skip)
        assert len(snap.agents) == 2


# ---------------------------------------------------------------------------
# WI-285 — Full render pipeline: parse fixtures → ViewportState → render_frame
# ---------------------------------------------------------------------------

class TestFullRenderPipeline:
    """Parse fixtures → build ViewportState → render_frame → verify output."""

    @pytest.fixture()
    def parsed(self):
        from hamlet.gui.kitty.state_fetcher import StateFetcher

        routes = {
            "/hamlet/state": "daemon_state_response.json",
            "/hamlet/events": "daemon_events_response.json",
            "/hamlet/terrain/bounds": "daemon_terrain_response.json",
        }
        with mock.patch(
            "hamlet.gui.kitty.state_fetcher.urllib.request.urlopen",
            side_effect=_make_urlopen(routes),
        ):
            fetcher = StateFetcher("http://localhost:8080")
            snap = fetcher.fetch_snapshot(0, 0, 40, 20)
        return snap

    def test_render_frame_with_parsed_state(self, parsed):
        from hamlet.gui.kitty.renderer import KittyRenderer
        from hamlet.viewport.coordinates import Position, Size
        from hamlet.viewport.state import ViewportState

        out = io.StringIO()
        renderer = KittyRenderer(out, cols=80, rows=24)

        # Center on first village
        village = parsed.villages[0]
        viewport = ViewportState(
            center=Position(village.center.x, village.center.y),
            size=Size(80, 24),
            follow_mode="free",
        )

        # Must not raise
        renderer.render_frame(
            viewport,
            parsed.agents,
            parsed.structures,
            parsed.terrain_data,
            parsed.event_log,
        )

        output = out.getvalue()
        assert len(output) > 0, "render_frame produced no output"

    def test_render_frame_produces_terrain_symbols(self, parsed):
        """FAR zoom renders terrain as ASCII symbols."""
        from hamlet.gui.kitty.renderer import KittyRenderer
        from hamlet.gui.kitty.zoom import ZoomLevel
        from hamlet.viewport.coordinates import Position, Size
        from hamlet.viewport.state import ViewportState

        out = io.StringIO()
        renderer = KittyRenderer(out, cols=80, rows=24)
        renderer.set_zoom(ZoomLevel.FAR)

        village = parsed.villages[0]
        viewport = ViewportState(
            center=Position(village.center.x, village.center.y),
            size=Size(80, 24),
            follow_mode="free",
        )
        renderer.render_frame(
            viewport, parsed.agents, parsed.structures,
            parsed.terrain_data, parsed.event_log,
        )

        output = out.getvalue()
        # At least one terrain symbol must appear
        terrain_symbols = {"~", "^", "♣", '"', ".", "#"}
        found = any(sym in output for sym in terrain_symbols)
        assert found, (
            f"No terrain symbol found in render output. "
            f"Got (first 200 chars): {output[:200]!r}"
        )

    def test_follow_mode_attribute_access(self, parsed):
        """Agent .id and .position.x/.y must be accessible without error."""
        assert len(parsed.agents) > 0
        for agent in parsed.agents:
            agent_id = agent.id
            x = agent.position.x
            y = agent.position.y
            assert isinstance(agent_id, str)
            assert isinstance(x, int)
            assert isinstance(y, int)

    def test_initial_viewport_from_parsed_villages(self, parsed):
        """Village .center.x/.y must be accessible without error."""
        assert len(parsed.villages) > 0
        v = parsed.villages[0]
        x = v.center.x
        y = v.center.y
        assert isinstance(x, int)
        assert isinstance(y, int)

    def test_structure_type_is_enum(self, parsed):
        """Structure.type must be a StructureType enum, not a raw string."""
        from hamlet.world_state.types import StructureType

        assert len(parsed.structures) > 0
        for struct in parsed.structures:
            assert isinstance(struct.type, StructureType), (
                f"Expected StructureType enum, got {type(struct.type)}"
            )

    def test_agent_type_is_enum(self, parsed):
        """Agent.inferred_type must be an AgentType enum, not a raw string."""
        from hamlet.world_state.types import AgentType

        for agent in parsed.agents:
            assert isinstance(agent.inferred_type, AgentType), (
                f"Expected AgentType enum, got {type(agent.inferred_type)}"
            )

    def test_render_frame_produces_agent_symbol(self, parsed):
        """Viewport centered on agent position must produce @ in render output."""
        from hamlet.gui.kitty.renderer import KittyRenderer
        from hamlet.gui.kitty.zoom import ZoomLevel
        from hamlet.viewport.coordinates import Position, Size
        from hamlet.viewport.state import ViewportState

        assert len(parsed.agents) > 0, "fixture must have at least one agent"

        # Use the first agent in the fixture
        agent = parsed.agents[0]
        agent_x = agent.position.x
        agent_y = agent.position.y

        out = io.StringIO()
        renderer = KittyRenderer(out, cols=80, rows=24)
        renderer.set_zoom(ZoomLevel.FAR)

        viewport = ViewportState(
            center=Position(agent_x, agent_y),
            size=Size(80, 24),
            follow_mode="free",
        )
        renderer.render_frame(
            viewport, parsed.agents, parsed.structures,
            parsed.terrain_data, parsed.event_log,
        )

        output = out.getvalue()
        assert "@" in output, (
            f"Agent symbol '@' not found in render output when viewport is "
            f"centered on agent at ({agent_x}, {agent_y}). "
            f"Got (first 200 chars): {output[:200]!r}"
        )


# ---------------------------------------------------------------------------
# WI-290 — Empty-state integration: fresh daemon (no agents/structures/villages)
# ---------------------------------------------------------------------------

class TestEmptyStatePipeline:
    """Verify the full parse→render pipeline handles a fresh daemon with no entities.

    A fresh daemon installation has no agents, structures, or villages.  This
    is a distinct code path from the populated-fixture tests above: every list
    is empty and the renderer must still produce terrain output without crashing.
    """

    @pytest.fixture()
    def empty_snapshot(self):
        from hamlet.gui.kitty.state_fetcher import StateFetcher

        routes = {
            "/hamlet/state": "daemon_state_empty.json",
            "/hamlet/events": "daemon_events_empty.json",
            "/hamlet/terrain/bounds": "daemon_terrain_response.json",
        }
        with mock.patch(
            "hamlet.gui.kitty.state_fetcher.urllib.request.urlopen",
            side_effect=_make_urlopen(routes),
        ):
            fetcher = StateFetcher("http://localhost:8080")
            return fetcher.fetch_snapshot(0, 0, 40, 20)

    def test_fetch_snapshot_agents_empty(self, empty_snapshot):
        """fetch_snapshot returns an empty agents list for a fresh daemon."""
        assert empty_snapshot.agents == [], (
            f"Expected empty agents list, got {empty_snapshot.agents!r}"
        )

    def test_fetch_snapshot_structures_empty(self, empty_snapshot):
        """fetch_snapshot returns an empty structures list for a fresh daemon."""
        assert empty_snapshot.structures == [], (
            f"Expected empty structures list, got {empty_snapshot.structures!r}"
        )

    def test_fetch_snapshot_villages_empty(self, empty_snapshot):
        """fetch_snapshot returns an empty villages list for a fresh daemon."""
        assert empty_snapshot.villages == [], (
            f"Expected empty villages list, got {empty_snapshot.villages!r}"
        )

    def test_render_frame_empty_state_does_not_crash(self, empty_snapshot):
        """render_frame must not raise when agents, structures, and villages are all empty."""
        from hamlet.gui.kitty.renderer import KittyRenderer
        from hamlet.viewport.coordinates import Position, Size
        from hamlet.viewport.state import ViewportState

        out = io.StringIO()
        renderer = KittyRenderer(out, cols=80, rows=24)

        viewport = ViewportState(
            center=Position(0, 0),
            size=Size(80, 24),
            follow_mode="free",
        )

        # Must not raise even with completely empty entity lists
        renderer.render_frame(
            viewport,
            empty_snapshot.agents,
            empty_snapshot.structures,
            empty_snapshot.terrain_data,
            empty_snapshot.event_log,
        )

        output = out.getvalue()
        assert len(output) > 0, "render_frame produced no output for empty state"

    def test_render_frame_empty_state_produces_terrain(self, empty_snapshot):
        """render_frame with empty entities still renders terrain symbols (FAR zoom)."""
        from hamlet.gui.kitty.renderer import KittyRenderer
        from hamlet.gui.kitty.zoom import ZoomLevel
        from hamlet.viewport.coordinates import Position, Size
        from hamlet.viewport.state import ViewportState

        out = io.StringIO()
        renderer = KittyRenderer(out, cols=80, rows=24)
        renderer.set_zoom(ZoomLevel.FAR)

        viewport = ViewportState(
            center=Position(0, 0),
            size=Size(80, 24),
            follow_mode="free",
        )
        renderer.render_frame(
            viewport,
            empty_snapshot.agents,
            empty_snapshot.structures,
            empty_snapshot.terrain_data,
            empty_snapshot.event_log,
        )

        output = out.getvalue()
        terrain_symbols = {"~", "^", "♣", '"', ".", "#"}
        found = any(sym in output for sym in terrain_symbols)
        assert found, (
            f"No terrain symbol found in render output for empty-state snapshot. "
            f"Got (first 200 chars): {output[:200]!r}"
        )
