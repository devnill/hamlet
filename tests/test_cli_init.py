"""Tests for hamlet init command."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch
from argparse import Namespace

from hamlet.cli.commands.init import init_command


def test_init_creates_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = init_command(Namespace())

    assert result == 0
    config_path = tmp_path / ".hamlet" / "config.json"
    assert config_path.exists()
    config = json.loads(config_path.read_text())
    assert "project_id" in config
    assert config["project_name"] == tmp_path.name
    assert "server_url" in config


def test_init_does_not_overwrite_on_cancel(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / ".hamlet"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    original = {
        "project_id": "original-id",
        "project_name": "test",
        "server_url": "http://localhost:8080/hamlet/event",
    }
    config_path.write_text(json.dumps(original))

    with patch("builtins.input", return_value="n"):
        result = init_command(Namespace())

    assert result == 0
    assert json.loads(config_path.read_text())["project_id"] == "original-id"


def test_init_overwrites_on_confirm(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / ".hamlet"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps({"project_id": "original-id", "project_name": "test", "server_url": "x"})
    )

    with patch("builtins.input", return_value="y"):
        result = init_command(Namespace())

    assert result == 0
    new_config = json.loads(config_path.read_text())
    assert new_config["project_id"] != "original-id"


def test_init_eoferror_cancels(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / ".hamlet"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    original_id = "original-id"
    config_path.write_text(
        json.dumps({"project_id": original_id, "project_name": "test", "server_url": "x"})
    )

    with patch("builtins.input", side_effect=EOFError):
        result = init_command(Namespace())

    assert result == 0
    assert json.loads(config_path.read_text())["project_id"] == original_id


def test_init_config_contains_valid_uuid(tmp_path, monkeypatch):
    import uuid
    monkeypatch.chdir(tmp_path)

    init_command(Namespace())

    config_path = tmp_path / ".hamlet" / "config.json"
    config = json.loads(config_path.read_text())
    # Should parse without error
    parsed = uuid.UUID(config["project_id"])
    assert str(parsed) == config["project_id"]


def test_init_server_url_contains_port(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    init_command(Namespace())

    config_path = tmp_path / ".hamlet" / "config.json"
    config = json.loads(config_path.read_text())
    assert "localhost" in config["server_url"]
    assert "/hamlet/event" in config["server_url"]
