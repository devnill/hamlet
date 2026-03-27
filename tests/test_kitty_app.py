"""Tests for the Kitty viewer app and state fetcher."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

from hamlet.gui.kitty.app import KittyApp
from hamlet.gui.kitty.state_fetcher import StateFetcher, StateSnapshot


class TestStateSnapshotDefaults:
    """StateSnapshot default values."""

    def test_default_agents_empty_list(self):
        snap = StateSnapshot()
        assert snap.agents == []

    def test_default_structures_empty_list(self):
        snap = StateSnapshot()
        assert snap.structures == []

    def test_default_villages_empty_list(self):
        snap = StateSnapshot()
        assert snap.villages == []

    def test_default_terrain_data_empty_dict(self):
        snap = StateSnapshot()
        assert snap.terrain_data == {}

    def test_default_event_log_empty_list(self):
        snap = StateSnapshot()
        assert snap.event_log == []

    def test_independent_defaults(self):
        """Each instance gets its own mutable containers."""
        s1 = StateSnapshot()
        s2 = StateSnapshot()
        s1.agents.append("x")
        assert s2.agents == []


class TestStateFetcherHealthCheck:
    """StateFetcher.check_health() behaviour."""

    def test_returns_false_on_connection_refused(self):
        fetcher = StateFetcher("http://localhost:99999")
        with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError):
            assert fetcher.check_health() is False

    def test_returns_false_on_timeout(self):
        fetcher = StateFetcher("http://localhost:8080")
        with patch("urllib.request.urlopen", side_effect=TimeoutError):
            assert fetcher.check_health() is False

    def test_returns_true_on_200(self):
        fetcher = StateFetcher("http://localhost:8080")
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None
        mock_resp.status = 200
        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert fetcher.check_health() is True

    def test_returns_false_on_non_200(self):
        fetcher = StateFetcher("http://localhost:8080")
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None
        mock_resp.status = 500
        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert fetcher.check_health() is False


class TestStateFetcherTerrainParsing:
    """StateFetcher terrain data parsing: string keys -> (int, int) tuples."""

    def test_parses_terrain_keys_to_int_tuples(self):
        fetcher = StateFetcher("http://localhost:8080")
        raw_terrain = {"0,0": "forest", "1,0": "water", "-3,5": "mountain"}

        def mock_urlopen(url, timeout=None):
            ctx = MagicMock()
            if "terrain/bounds" in url:
                ctx.__enter__ = lambda s: MagicMock(
                    read=lambda: json.dumps(raw_terrain).encode()
                )
            elif "/hamlet/state" in url:
                ctx.__enter__ = lambda s: MagicMock(
                    read=lambda: json.dumps(
                        {"agents": [], "structures": [], "villages": []}
                    ).encode()
                )
            elif "/hamlet/events" in url:
                ctx.__enter__ = lambda s: MagicMock(
                    read=lambda: json.dumps({"events": []}).encode()
                )
            else:
                ctx.__enter__ = lambda s: MagicMock(
                    read=lambda: b"{}"
                )
            ctx.__exit__ = lambda s, *a: None
            return ctx

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            snap = fetcher.fetch_snapshot(0, 0, 10, 10)

        assert (0, 0) in snap.terrain_data
        assert snap.terrain_data[(0, 0)] == "forest"
        assert (1, 0) in snap.terrain_data
        assert snap.terrain_data[(1, 0)] == "water"
        assert (-3, 5) in snap.terrain_data
        assert snap.terrain_data[(-3, 5)] == "mountain"

    def test_skips_malformed_keys(self):
        fetcher = StateFetcher("http://localhost:8080")
        raw_terrain = {"bad_key": "forest", "0,0": "water"}

        def mock_urlopen(url, timeout=None):
            ctx = MagicMock()
            if "terrain/bounds" in url:
                ctx.__enter__ = lambda s: MagicMock(
                    read=lambda: json.dumps(raw_terrain).encode()
                )
            elif "/hamlet/state" in url:
                ctx.__enter__ = lambda s: MagicMock(
                    read=lambda: json.dumps(
                        {"agents": [], "structures": [], "villages": []}
                    ).encode()
                )
            elif "/hamlet/events" in url:
                ctx.__enter__ = lambda s: MagicMock(
                    read=lambda: json.dumps({"events": []}).encode()
                )
            else:
                ctx.__enter__ = lambda s: MagicMock(read=lambda: b"{}")
            ctx.__exit__ = lambda s, *a: None
            return ctx

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            snap = fetcher.fetch_snapshot(0, 0, 10, 10)

        # "bad_key" should be skipped (not 2-element comma-separated)
        assert (0, 0) in snap.terrain_data
        assert len(snap.terrain_data) == 1


class TestKittyAppConstructor:
    """KittyApp.__init__ stores configuration correctly."""

    def test_default_base_url(self):
        app = KittyApp()
        assert app._base_url == "http://localhost:8080"

    def test_custom_base_url(self):
        app = KittyApp(base_url="http://example.com:9090")
        assert app._base_url == "http://example.com:9090"

    def test_initial_state(self):
        app = KittyApp()
        assert app._running is False
        assert app._show_legend is False
        assert app._follow_target is None
        assert app._frame_count == 0


class TestKittyAppHealthCheckFailure:
    """KittyApp.run() returns 1 when daemon is unreachable."""

    def test_run_returns_1_on_health_failure(self):
        app = KittyApp()
        with patch.object(app._fetcher, "check_health", return_value=False):
            # Capture stderr
            import io

            captured = io.StringIO()
            with patch("sys.stderr", captured):
                result = app.run()
            assert result == 1
            output = captured.getvalue()
            assert "not running" in output.lower() or "Error" in output

    def test_run_prints_daemon_advice_on_failure(self):
        app = KittyApp()
        with patch.object(app._fetcher, "check_health", return_value=False):
            import io

            captured = io.StringIO()
            with patch("sys.stderr", captured):
                app.run()
            assert "hamlet daemon" in captured.getvalue()


class TestKittyAppLegendOverlay:
    """KittyApp._render_legend() output."""

    def test_render_legend_contains_expected_content(self):
        app = KittyApp()
        app._cols = 80
        app._rows = 24

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            app._render_legend()

        output = captured.getvalue()
        # Box drawing characters
        assert "┌" in output
        assert "┐" in output
        assert "└" in output
        assert "┘" in output
        # Heading
        assert "Key Bindings" in output
        # Terrain symbols from default_config
        assert "~" in output  # water
        assert "^" in output  # mountain
        # Agent symbol
        assert "@" in output
