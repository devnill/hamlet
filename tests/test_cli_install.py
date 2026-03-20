"""Tests for hamlet install command helpers (work item WI-188)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from hamlet.cli.commands.install import is_plugin_active


class TestIsPluginActive:
    """Tests for is_plugin_active function."""

    def _plugins_dir(self, tmp_path: Path) -> Path:
        plugins_dir = tmp_path / ".claude" / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        return plugins_dir

    def test_returns_true_for_wrapped_format(self, tmp_path: Path) -> None:
        """is_plugin_active returns True when installed_plugins.json uses wrapped format."""
        plugins_dir = self._plugins_dir(tmp_path)
        data = {"plugins": {"hamlet-xyz": [{"installPath": "/some/path/hamlet"}]}}
        (plugins_dir / "installed_plugins.json").write_text(json.dumps(data), encoding="utf-8")

        with patch.object(Path, "home", return_value=tmp_path):
            result = is_plugin_active()

        assert result is True

    def test_returns_true_for_unwrapped_format(self, tmp_path: Path) -> None:
        """is_plugin_active returns True when installed_plugins.json uses unwrapped format."""
        plugins_dir = self._plugins_dir(tmp_path)
        data = {"hamlet-xyz": [{"installPath": "/some/path/hamlet"}]}
        (plugins_dir / "installed_plugins.json").write_text(json.dumps(data), encoding="utf-8")

        with patch.object(Path, "home", return_value=tmp_path):
            result = is_plugin_active()

        assert result is True

    def test_returns_false_when_file_missing(self, tmp_path: Path) -> None:
        """is_plugin_active returns False when installed_plugins.json does not exist."""
        # Create the .claude/plugins directory but no file inside it
        self._plugins_dir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path):
            result = is_plugin_active()

        assert result is False

    def test_returns_false_when_no_matching_key(self, tmp_path: Path) -> None:
        """is_plugin_active returns False when no key contains 'hamlet'."""
        plugins_dir = self._plugins_dir(tmp_path)
        data = {"other-plugin": [{"installPath": "/other"}]}
        (plugins_dir / "installed_plugins.json").write_text(json.dumps(data), encoding="utf-8")

        with patch.object(Path, "home", return_value=tmp_path):
            result = is_plugin_active()

        assert result is False
