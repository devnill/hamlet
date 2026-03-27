"""Tests for hamlet.gui.detect — renderer detection and resolution."""

from __future__ import annotations

import types

import pytest

from hamlet.gui.detect import detect_renderer, resolve_renderer


class TestDetectRenderer:
    """Tests for detect_renderer()."""

    def test_returns_kitty_when_available(self, monkeypatch) -> None:
        """detect_renderer() returns 'kitty' when KITTY_AVAILABLE is True."""
        # Create a fake hamlet.gui.kitty module with KITTY_AVAILABLE = True
        fake_module = types.ModuleType("hamlet.gui.kitty")
        fake_module.KITTY_AVAILABLE = True  # type: ignore[attr-defined]
        monkeypatch.setitem(__import__("sys").modules, "hamlet.gui.kitty", fake_module)

        result = detect_renderer()
        assert result == "kitty"

    def test_returns_textual_when_kitty_unavailable(self, monkeypatch) -> None:
        """detect_renderer() returns 'textual' when KITTY_AVAILABLE is False."""
        fake_module = types.ModuleType("hamlet.gui.kitty")
        fake_module.KITTY_AVAILABLE = False  # type: ignore[attr-defined]
        monkeypatch.setitem(__import__("sys").modules, "hamlet.gui.kitty", fake_module)

        result = detect_renderer()
        assert result == "textual"

    def test_returns_textual_when_import_fails(self, monkeypatch) -> None:
        """detect_renderer() returns 'textual' when hamlet.gui.kitty cannot be imported."""
        # Remove the module so import fails
        monkeypatch.delitem(
            __import__("sys").modules, "hamlet.gui.kitty", raising=False
        )
        # Also make the import itself fail by patching builtins
        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        def fail_import(name, *args, **kwargs):
            if name == "hamlet.gui.kitty":
                raise ImportError("no kitty")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fail_import)
        result = detect_renderer()
        assert result == "textual"


class TestResolveRenderer:
    """Tests for resolve_renderer() precedence logic."""

    def test_cli_arg_wins_over_settings_auto(self) -> None:
        """cli_arg takes precedence over settings_value='auto'."""
        result = resolve_renderer(cli_arg="textual", settings_value="auto")
        assert result == "textual"

    def test_cli_arg_kitty_wins_over_settings(self) -> None:
        """cli_arg='kitty' takes precedence over settings_value."""
        result = resolve_renderer(cli_arg="kitty", settings_value="textual")
        assert result == "kitty"

    def test_cli_arg_wins_over_explicit_settings(self) -> None:
        """cli_arg takes precedence over an explicit settings_value."""
        result = resolve_renderer(cli_arg="textual", settings_value="textual")
        assert result == "textual"

    def test_cli_arg_none_and_settings_textual_returns_textual(self) -> None:
        """When cli_arg is None and settings_value is 'textual', returns 'textual'."""
        result = resolve_renderer(cli_arg=None, settings_value="textual")
        assert result == "textual"

    def test_cli_arg_none_and_settings_kitty_returns_kitty(self) -> None:
        """When cli_arg is None and settings_value is 'kitty', returns 'kitty'."""
        result = resolve_renderer(cli_arg=None, settings_value="kitty")
        assert result == "kitty"

    def test_cli_arg_none_settings_auto_calls_detect(self, monkeypatch) -> None:
        """When cli_arg is None and settings_value is 'auto', calls detect_renderer()."""
        import hamlet.gui.detect as detect_mod
        monkeypatch.setattr(detect_mod, "detect_renderer", lambda: "kitty")
        result = resolve_renderer(cli_arg=None, settings_value="auto")
        assert result == "kitty"

    def test_detect_not_called_when_cli_arg_provided(self, monkeypatch) -> None:
        """detect_renderer() is not called when cli_arg is not None."""
        called = []

        import hamlet.gui.detect as detect_mod
        monkeypatch.setattr(detect_mod, "detect_renderer", lambda: called.append(1) or "textual")
        resolve_renderer(cli_arg="textual", settings_value="auto")
        assert called == [], "detect_renderer should not be called when cli_arg is set"

    def test_detect_not_called_when_settings_explicit(self, monkeypatch) -> None:
        """detect_renderer() is not called when settings_value is explicit (not 'auto')."""
        called = []

        import hamlet.gui.detect as detect_mod
        monkeypatch.setattr(detect_mod, "detect_renderer", lambda: called.append(1) or "textual")
        resolve_renderer(cli_arg=None, settings_value="textual")
        assert called == [], "detect_renderer should not be called for explicit settings_value"
