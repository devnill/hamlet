"""Tests for hamlet daemon CLI registration and config reload."""
from __future__ import annotations

import logging
import pytest
from unittest.mock import patch, MagicMock

from hamlet.cli import create_parser
from hamlet.cli.commands.daemon import _check_port_conflict, _apply_config_changes
from hamlet.config.settings import Settings


def test_daemon_subcommand_registered():
    parser = create_parser()
    # parse_known_args returns (namespace, remaining)
    ns, _ = parser.parse_known_args(["daemon"])
    assert getattr(ns, "command", None) == "daemon"


def test_daemon_port_flag():
    parser = create_parser()
    ns, _ = parser.parse_known_args(["daemon", "--port", "9090"])
    assert ns.port == 9090


def test_daemon_port_default_is_none():
    parser = create_parser()
    ns, _ = parser.parse_known_args(["daemon"])
    assert ns.port is None


def test_daemon_has_func_set():
    parser = create_parser()
    ns, _ = parser.parse_known_args(["daemon"])
    assert hasattr(ns, "func")
    assert callable(ns.func)


def test_daemon_port_conflict_hamlet_exits():
    """daemon_command exits with code 1 when hamlet is already on the port."""
    from hamlet.cli.commands.daemon import daemon_command

    args = MagicMock()
    args.port = 8080

    with patch("hamlet.cli.commands.daemon.Settings") as mock_settings_class, \
         patch("hamlet.cli.commands.daemon._check_port_conflict", return_value="hamlet"):
        mock_settings_class.load.return_value = MagicMock(mcp_port=8080)
        with pytest.raises(SystemExit) as exc_info:
            daemon_command(args)

    assert exc_info.value.code == 1


def test_daemon_port_conflict_other_exits():
    """daemon_command exits with code 1 when another process is using the port."""
    from hamlet.cli.commands.daemon import daemon_command

    args = MagicMock()
    args.port = 8080

    with patch("hamlet.cli.commands.daemon.Settings") as mock_settings_class, \
         patch("hamlet.cli.commands.daemon._check_port_conflict", return_value="other"):
        mock_settings_class.load.return_value = MagicMock(mcp_port=8080)
        with pytest.raises(SystemExit) as exc_info:
            daemon_command(args)

    assert exc_info.value.code == 1


def test_daemon_port_free_proceeds():
    """daemon_command calls asyncio.run (starting the daemon) when the port is free."""
    from hamlet.cli.commands.daemon import daemon_command

    args = MagicMock()
    args.port = 8080

    def _close_coro_and_return(coro):
        coro.close()
        return 0

    with patch("hamlet.cli.commands.daemon.Settings") as mock_settings_class, \
         patch("hamlet.cli.commands.daemon._check_port_conflict", return_value=None), \
         patch("hamlet.cli.commands.daemon.asyncio.run", side_effect=_close_coro_and_return) as mock_run:
        mock_settings_class.load.return_value = MagicMock(mcp_port=8080)
        result = daemon_command(args)

    mock_run.assert_called_once()
    assert result == 0


def test_check_port_conflict_port_free():
    """Port is free — connect_ex returns non-zero."""
    with patch("socket.socket") as mock_sock_class:
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: mock_sock
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.connect_ex.return_value = 1  # non-zero = port free
        mock_sock_class.return_value = mock_sock
        result = _check_port_conflict(8080)
    assert result is None


def test_check_port_conflict_hamlet_running():
    """Port in use and /hamlet/health returns 200."""
    with patch("socket.socket") as mock_sock_class, \
         patch("urllib.request.urlopen") as mock_urlopen:
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: mock_sock
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.connect_ex.return_value = 0  # port in use
        mock_sock_class.return_value = mock_sock
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = _check_port_conflict(8080)
    assert result == "hamlet"


def test_check_port_conflict_other_process():
    """Port in use but /hamlet/health raises (not hamlet)."""
    with patch("socket.socket") as mock_sock_class, \
         patch("urllib.request.urlopen") as mock_urlopen:
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: mock_sock
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.connect_ex.return_value = 0  # port in use
        mock_sock_class.return_value = mock_sock
        mock_urlopen.side_effect = OSError("connection refused")
        result = _check_port_conflict(8080)
    assert result == "other"


class TestApplyConfigChanges:
    """Tests for _apply_config_changes config reload propagation."""

    def _make_bundle(self):
        bundle = MagicMock()
        bundle.world_state._min_village_distance = 15
        bundle.agent_inference._zombie_threshold_seconds = 300
        bundle.simulation.set_tick_rate = MagicMock()
        return bundle

    def test_propagates_min_village_distance(self):
        bundle = self._make_bundle()
        new_settings = Settings(min_village_distance=25)
        changes = {"min_village_distance": (15, 25)}
        _apply_config_changes(bundle, changes, new_settings)
        assert bundle.world_state._min_village_distance == 25

    def test_propagates_zombie_threshold(self):
        bundle = self._make_bundle()
        new_settings = Settings(zombie_threshold_seconds=600)
        changes = {"zombie_threshold_seconds": (300, 600)}
        _apply_config_changes(bundle, changes, new_settings)
        assert bundle.agent_inference._zombie_threshold_seconds == 600

    def test_propagates_tick_rate(self):
        bundle = self._make_bundle()
        new_settings = Settings(tick_rate=60.0)
        changes = {"tick_rate": (30.0, 60.0)}
        _apply_config_changes(bundle, changes, new_settings)
        bundle.simulation.set_tick_rate.assert_called_once_with(60.0)

    def test_mcp_port_logs_warning(self, caplog):
        bundle = self._make_bundle()
        new_settings = Settings(mcp_port=9090)
        changes = {"mcp_port": (8080, 9090)}
        with caplog.at_level(logging.WARNING):
            _apply_config_changes(bundle, changes, new_settings)
        assert any("restart required" in r.message for r in caplog.records)

    def test_logs_all_changes_at_info(self, caplog):
        bundle = self._make_bundle()
        new_settings = Settings(min_village_distance=20, tick_rate=60.0)
        changes = {"min_village_distance": (15, 20), "tick_rate": (30.0, 60.0)}
        with caplog.at_level(logging.INFO):
            _apply_config_changes(bundle, changes, new_settings)
        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_messages) >= 2
