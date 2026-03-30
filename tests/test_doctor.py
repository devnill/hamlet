"""Tests for the hamlet doctor command."""
from __future__ import annotations

import sys
from argparse import Namespace
from unittest.mock import patch, MagicMock


def test_doctor_command_returns_zero():
    """doctor_command always returns 0."""
    from hamlet.cli.commands.doctor import doctor_command

    args = Namespace()
    result = doctor_command(args)
    assert result == 0


def test_doctor_command_prints_renderer(capsys):
    """doctor_command output includes renderer information."""
    from hamlet.cli.commands.doctor import doctor_command

    args = Namespace()
    doctor_command(args)
    captured = capsys.readouterr()
    assert "renderer" in captured.out.lower()


def test_doctor_command_prints_kitty(capsys):
    """doctor_command output mentions Kitty protocol."""
    from hamlet.cli.commands.doctor import doctor_command

    args = Namespace()
    doctor_command(args)
    captured = capsys.readouterr()
    assert "kitty" in captured.out.lower()


def test_doctor_command_prints_kitty_window_id(capsys):
    """doctor_command reports KITTY_WINDOW_ID value."""
    from hamlet.cli.commands.doctor import doctor_command

    args = Namespace()
    with patch.dict("os.environ", {"KITTY_WINDOW_ID": "42"}, clear=False):
        doctor_command(args)
    captured = capsys.readouterr()
    assert "KITTY_WINDOW_ID" in captured.out
    assert "42" in captured.out


def test_doctor_command_prints_term(capsys):
    """doctor_command reports TERM value."""
    from hamlet.cli.commands.doctor import doctor_command

    args = Namespace()
    with patch.dict("os.environ", {"TERM": "xterm-256color"}, clear=False):
        doctor_command(args)
    captured = capsys.readouterr()
    assert "TERM" in captured.out
    assert "xterm-256color" in captured.out


def test_doctor_command_warns_in_tmux(capsys):
    """doctor_command warns when TMUX env var is set."""
    from hamlet.cli.commands.doctor import doctor_command

    args = Namespace()
    with patch.dict("os.environ", {"TMUX": "/tmp/tmux-1000/default,12345,0"}, clear=False):
        doctor_command(args)
    captured = capsys.readouterr()
    assert "WARNING" in captured.out
    assert "tmux" in captured.out.lower()
    assert "Kitty" in captured.out or "kitty" in captured.out.lower()


def test_doctor_command_no_tmux_warning_outside_tmux(capsys):
    """doctor_command does not warn when TMUX env var is absent."""
    from hamlet.cli.commands.doctor import doctor_command

    args = Namespace()
    env_without_tmux = {k: v for k, v in __import__("os").environ.items() if k != "TMUX"}
    with patch.dict("os.environ", env_without_tmux, clear=True):
        doctor_command(args)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out


def test_doctor_subcommand_registered():
    """doctor subcommand is registered in create_parser()."""
    from hamlet.cli import create_parser

    parser = create_parser()
    # Parse with 'doctor' — should not raise and should set func
    args = parser.parse_args(["doctor"])
    assert args.command == "doctor"
    assert callable(args.func)


def test_doctor_via_cli_returns_zero():
    """Running doctor through the main CLI entry point returns 0."""
    from hamlet.cli import main

    result = main(["doctor"])
    assert result == 0


# --- Hook connectivity check tests ---

def test_doctor_check_hooks_flag_registered():
    """doctor --check-hooks flag is registered in the parser."""
    from hamlet.cli import create_parser

    parser = create_parser()
    args = parser.parse_args(["doctor", "--check-hooks"])
    assert args.check_hooks is True


def test_doctor_check_hooks_default_false():
    """doctor command defaults check_hooks to False."""
    from hamlet.cli import create_parser

    parser = create_parser()
    args = parser.parse_args(["doctor"])
    assert args.check_hooks is False


def test_doctor_check_hooks_success(capsys):
    """doctor --check-hooks reports success when daemon is reachable."""
    from hamlet.cli.commands.doctor import doctor_command

    args = Namespace(check_hooks=True)

    # Mock Settings to return port 8080
    mock_settings = MagicMock()
    mock_settings.mcp_port = 8080

    # Mock urlopen to return successful response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("hamlet.config.settings.Settings.load", return_value=mock_settings):
        with patch("hamlet.cli.commands.doctor.urllib.request.urlopen", return_value=mock_response):
            result = doctor_command(args)

    captured = capsys.readouterr()
    assert result == 0
    assert "Hook connectivity check" in captured.out
    assert "PASS" in captured.out
    assert "Daemon is running on port 8080" in captured.out


def test_doctor_check_hooks_daemon_not_running(capsys):
    """doctor --check-hooks reports failure when daemon is not running."""
    from hamlet.cli.commands.doctor import doctor_command
    import urllib.error

    args = Namespace(check_hooks=True)

    mock_settings = MagicMock()
    mock_settings.mcp_port = 8080

    with patch("hamlet.config.settings.Settings.load", return_value=mock_settings):
        with patch("hamlet.cli.commands.doctor.urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            result = doctor_command(args)

    captured = capsys.readouterr()
    assert result == 0  # doctor always returns 0
    assert "Hook connectivity check" in captured.out
    assert "FAIL" in captured.out
    assert "Daemon not running" in captured.out
    assert "hamlet daemon" in captured.out  # actionable fix message


def test_doctor_check_hooks_non_200_status(capsys):
    """doctor --check-hooks reports failure when daemon returns non-200 status."""
    from hamlet.cli.commands.doctor import doctor_command

    args = Namespace(check_hooks=True)

    mock_settings = MagicMock()
    mock_settings.mcp_port = 9090

    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("hamlet.config.settings.Settings.load", return_value=mock_settings):
        with patch("hamlet.cli.commands.doctor.urllib.request.urlopen", return_value=mock_response):
            result = doctor_command(args)

    captured = capsys.readouterr()
    assert result == 0
    assert "FAIL" in captured.out
    assert "Daemon returned status 500" in captured.out


def test_doctor_check_hooks_fallback_port_on_settings_error(capsys):
    """doctor --check-hooks uses default port 8080 if settings fail to load."""
    from hamlet.cli.commands.doctor import doctor_command

    args = Namespace(check_hooks=True)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("hamlet.config.settings.Settings.load", side_effect=Exception("Config error")):
        with patch("hamlet.cli.commands.doctor.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            result = doctor_command(args)

    captured = capsys.readouterr()
    # Verify it used port 8080 (the fallback)
    mock_urlopen.assert_called_once()
    assert "http://localhost:8080/hamlet/health" in mock_urlopen.call_args[0][0].full_url
    assert result == 0
    assert "PASS" in captured.out


def test_doctor_no_check_hooks_skips_connectivity_test(capsys):
    """doctor without --check-hooks does not run connectivity check."""
    from hamlet.cli.commands.doctor import doctor_command

    args = Namespace(check_hooks=False)

    with patch("hamlet.cli.commands.doctor._check_hook_connectivity") as mock_check:
        result = doctor_command(args)

    # Should not call the connectivity check
    mock_check.assert_not_called()
    captured = capsys.readouterr()
    assert "Hook connectivity check" not in captured.out


def test_check_hook_connectivity_returns_tuple():
    """_check_hook_connectivity returns (bool, str) tuple."""
    from hamlet.cli.commands.doctor import _check_hook_connectivity

    mock_settings = MagicMock()
    mock_settings.mcp_port = 8080

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("hamlet.config.settings.Settings.load", return_value=mock_settings):
        with patch("hamlet.cli.commands.doctor.urllib.request.urlopen", return_value=mock_response):
            result = _check_hook_connectivity()

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert isinstance(result[1], str)
    assert result[0] is True
    assert "8080" in result[1]
