"""Tests for hamlet daemon CLI registration."""
from __future__ import annotations

from hamlet.cli import create_parser


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
