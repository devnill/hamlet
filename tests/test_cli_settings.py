"""Tests for hamlet settings CLI command."""
from __future__ import annotations

import json
from unittest.mock import patch

from hamlet.cli.commands.settings_cmd import (
    settings_command,
    settings_get,
    settings_list,
    settings_set,
    _coerce_value,
)


class TestCoerceValue:
    def test_null_returns_none(self):
        assert _coerce_value(42, "null") is None
        assert _coerce_value("x", "None") is None

    def test_true_false(self):
        assert _coerce_value(None, "true") is True
        assert _coerce_value(None, "False") is False

    def test_int_coercion(self):
        assert _coerce_value(8080, "9090") == 9090

    def test_int_invalid(self):
        import pytest
        with pytest.raises(ValueError, match="Expected integer"):
            _coerce_value(8080, "abc")

    def test_float_coercion(self):
        assert _coerce_value(30.0, "60.5") == 60.5

    def test_float_invalid(self):
        import pytest
        with pytest.raises(ValueError, match="Expected float"):
            _coerce_value(1.0, "xyz")

    def test_bool_existing_rejects_non_bool_string(self):
        import pytest
        with pytest.raises(ValueError, match="Expected 'true' or 'false'"):
            _coerce_value(True, "yes")

    def test_string_passthrough(self):
        assert _coerce_value("default", "dark") == "dark"

    def test_none_existing_string(self):
        assert _coerce_value(None, "hello") == "hello"


class TestSettingsList:
    def test_prints_all_keys(self, tmp_path, capsys):
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"mcp_port": 8080, "terrain": {}}))
        with patch("hamlet.config.settings.CONFIG_PATH", config), \
             patch("hamlet.config.paths.CONFIG_PATH", config), \
             patch("hamlet.config.settings.ensure_hamlet_dir"):
            result = settings_list()
        assert result == 0
        out = capsys.readouterr().out
        assert "mcp_port = 8080" in out
        assert "db_path" in out


class TestSettingsGet:
    def test_get_existing_key(self, tmp_path, capsys):
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"mcp_port": 9090, "terrain": {}}))
        with patch("hamlet.config.settings.CONFIG_PATH", config), \
             patch("hamlet.config.paths.CONFIG_PATH", config), \
             patch("hamlet.config.settings.ensure_hamlet_dir"):
            result = settings_get("mcp_port")
        assert result == 0
        assert "9090" in capsys.readouterr().out

    def test_get_invalid_key(self, tmp_path, capsys):
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"terrain": {}}))
        with patch("hamlet.config.settings.CONFIG_PATH", config), \
             patch("hamlet.config.paths.CONFIG_PATH", config), \
             patch("hamlet.config.settings.ensure_hamlet_dir"):
            result = settings_get("nonexistent")
        assert result == 1
        assert "unknown key" in capsys.readouterr().err.lower()

    def test_get_terrain_dot_notation(self, tmp_path, capsys):
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"terrain": {"seed": 42}}))
        with patch("hamlet.config.settings.CONFIG_PATH", config), \
             patch("hamlet.config.paths.CONFIG_PATH", config), \
             patch("hamlet.config.settings.ensure_hamlet_dir"):
            result = settings_get("terrain.seed")
        assert result == 0
        assert "42" in capsys.readouterr().out


class TestSettingsSet:
    def test_set_mcp_port(self, tmp_path, capsys):
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"mcp_port": 8080, "terrain": {}}))
        with patch("hamlet.config.settings.CONFIG_PATH", config), \
             patch("hamlet.config.paths.CONFIG_PATH", config), \
             patch("hamlet.config.settings.ensure_hamlet_dir"):
            result = settings_set("mcp_port", "9090")
        assert result == 0
        out = capsys.readouterr().out
        assert "9090" in out
        # Verify persisted
        saved = json.loads(config.read_text())
        assert saved["mcp_port"] == 9090

    def test_set_invalid_type(self, tmp_path, capsys):
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"mcp_port": 8080, "terrain": {}}))
        with patch("hamlet.config.settings.CONFIG_PATH", config), \
             patch("hamlet.config.paths.CONFIG_PATH", config), \
             patch("hamlet.config.settings.ensure_hamlet_dir"):
            result = settings_set("mcp_port", "abc")
        assert result == 1
        assert "expected integer" in capsys.readouterr().err.lower()

    def test_set_validation_failure(self, tmp_path, capsys):
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"mcp_port": 8080, "terrain": {}}))
        with patch("hamlet.config.settings.CONFIG_PATH", config), \
             patch("hamlet.config.paths.CONFIG_PATH", config), \
             patch("hamlet.config.settings.ensure_hamlet_dir"):
            result = settings_set("mcp_port", "99999")
        assert result == 1
        assert "validation error" in capsys.readouterr().err.lower()

    def test_set_terrain_dot_notation(self, tmp_path, capsys):
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"terrain": {}}))
        with patch("hamlet.config.settings.CONFIG_PATH", config), \
             patch("hamlet.config.paths.CONFIG_PATH", config), \
             patch("hamlet.config.settings.ensure_hamlet_dir"):
            result = settings_set("terrain.seed", "42")
        assert result == 0
        saved = json.loads(config.read_text())
        assert saved["terrain"]["seed"] == 42

    def test_set_invalid_key(self, tmp_path, capsys):
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"terrain": {}}))
        with patch("hamlet.config.settings.CONFIG_PATH", config), \
             patch("hamlet.config.paths.CONFIG_PATH", config), \
             patch("hamlet.config.settings.ensure_hamlet_dir"):
            result = settings_set("nonexistent", "value")
        assert result == 1
        assert "unknown key" in capsys.readouterr().err.lower()
