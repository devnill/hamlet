"""Tests for the hamlet doctor command."""
from __future__ import annotations

import sys
from argparse import Namespace
from unittest.mock import patch


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
