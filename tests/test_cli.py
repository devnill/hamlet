"""Tests for hamlet CLI view command and related behaviour."""
from __future__ import annotations

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from hamlet.cli import create_parser, _view_command
import hamlet.cli


def test_view_subcommand_registered():
    parser = create_parser()
    ns, _ = parser.parse_known_args(["view"])
    assert getattr(ns, "command", None) == "view"


def test_view_url_default_is_none():
    """The --url default must be None so _view_command can derive it from Settings."""
    parser = create_parser()
    ns, _ = parser.parse_known_args(["view"])
    assert ns.url is None


def test_view_uses_settings_mcp_port_when_no_url():
    """hamlet view (no --url) must pass a URL built from settings.mcp_port to _run_viewer."""
    parser = create_parser()
    ns, _ = parser.parse_known_args(["view"])
    # ns.url is None here

    captured_url = []

    async def _fake_viewer(url):
        captured_url.append(url)
        return 0

    mock_settings = MagicMock()
    mock_settings.mcp_port = 9999

    def _run_sync(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with patch("hamlet.config.settings.Settings.load", return_value=mock_settings), \
         patch("hamlet.__main__._run_viewer", side_effect=_fake_viewer), \
         patch("asyncio.run", side_effect=_run_sync):
        _view_command(ns)

    assert captured_url == ["http://localhost:9999"]


def test_view_uses_explicit_url_when_provided():
    """hamlet view --url http://remote:1234 must pass that URL unchanged."""
    parser = create_parser()
    ns, _ = parser.parse_known_args(["view", "--url", "http://remote:1234"])
    assert ns.url == "http://remote:1234"

    captured_url = []

    async def _fake_viewer(url):
        captured_url.append(url)
        return 0

    def _run_sync(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    mock_settings = MagicMock()
    mock_settings.mcp_port = 8080
    mock_settings.renderer = "auto"

    with patch("hamlet.config.settings.Settings.load", return_value=mock_settings), \
         patch("hamlet.gui.detect.resolve_renderer", return_value="textual"), \
         patch("hamlet.__main__._run_viewer", side_effect=_fake_viewer), \
         patch("asyncio.run", side_effect=_run_sync):
        _view_command(ns)

    assert captured_url == ["http://remote:1234"]


def test_main_no_subcommand_uses_settings_mcp_port():
    """hamlet.cli.main([]) (no subcommand) must build the viewer URL from settings.mcp_port."""
    captured_url = []

    async def _fake_viewer(url):
        captured_url.append(url)
        return 0

    mock_settings = MagicMock()
    mock_settings.mcp_port = 7777
    mock_settings.renderer = "auto"

    with patch("hamlet.config.settings.Settings") as mock_settings_cls, \
         patch("hamlet.gui.detect.resolve_renderer", return_value="textual"), \
         patch("hamlet.__main__._run_viewer", side_effect=_fake_viewer):
        mock_settings_cls.load.return_value = mock_settings
        result = hamlet.cli.main([])

    assert captured_url == ["http://localhost:7777"]


def test_view_renderer_argument_choices():
    """The view --renderer flag must accept auto, textual, and kitty."""
    parser = create_parser()
    for choice in ("auto", "textual", "kitty"):
        ns, _ = parser.parse_known_args(["view", "--renderer", choice])
        assert ns.renderer == choice


def test_view_command_kitty_renderer_calls_launch_kitty_viewer():
    """When resolve_renderer returns 'kitty', _view_command must call _launch_kitty_viewer."""
    parser = create_parser()
    ns, _ = parser.parse_known_args(["view", "--url", "http://localhost:9999"])

    mock_settings = MagicMock()
    mock_settings.mcp_port = 9999
    mock_settings.renderer = "auto"

    kitty_calls = []

    def _fake_launch_kitty(url):
        kitty_calls.append(url)
        return 0

    with patch("hamlet.config.settings.Settings.load", return_value=mock_settings), \
         patch("hamlet.gui.detect.resolve_renderer", return_value="kitty"), \
         patch("hamlet.cli._launch_kitty_viewer", side_effect=_fake_launch_kitty):
        result = _view_command(ns)

    assert kitty_calls == ["http://localhost:9999"]
    assert result == 0


def test_main_no_subcommand_kitty_renderer_calls_launch_kitty_viewer():
    """When resolve_renderer returns 'kitty', main([]) must call _launch_kitty_viewer."""
    mock_settings = MagicMock()
    mock_settings.mcp_port = 8888
    mock_settings.renderer = "auto"

    kitty_calls = []

    def _fake_launch_kitty(url):
        kitty_calls.append(url)
        return 0

    with patch("hamlet.config.settings.Settings") as mock_settings_cls, \
         patch("hamlet.gui.detect.resolve_renderer", return_value="kitty"), \
         patch("hamlet.cli._launch_kitty_viewer", side_effect=_fake_launch_kitty):
        mock_settings_cls.load.return_value = mock_settings
        result = hamlet.cli.main([])

    assert kitty_calls == ["http://localhost:8888"]
    assert result == 0


def test_view_renderer_default_is_none():
    """--renderer default must be None so resolve_renderer uses settings."""
    parser = create_parser()
    ns, _ = parser.parse_known_args(["view"])
    assert ns.renderer is None
