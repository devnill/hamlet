"""Tests for Settings config validation."""
from __future__ import annotations

import json
import pytest

from hamlet.config.settings import Settings


class TestSettingsValidate:
    """Tests for Settings._validate()."""

    def test_validate_accepts_valid_defaults(self) -> None:
        """Default Settings instance passes validation without error."""
        settings = Settings()
        settings._validate()  # Should not raise

    def test_validate_rejects_empty_db_path(self) -> None:
        """_validate raises ValueError when db_path is empty string."""
        settings = Settings(db_path="")
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "db_path" in msg
        assert "''" in msg or "non-empty" in msg

    def test_validate_rejects_non_string_db_path(self) -> None:
        """_validate raises ValueError when db_path is not a string."""
        settings = Settings()
        settings.db_path = 123  # type: ignore[assignment]
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "db_path" in msg
        assert "123" in msg

    def test_validate_rejects_mcp_port_zero(self) -> None:
        """_validate raises ValueError when mcp_port is 0 (below range)."""
        settings = Settings(mcp_port=0)
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "mcp_port" in msg
        assert "between 1 and 65535" in msg
        assert "0" in msg

    def test_validate_rejects_mcp_port_above_max(self) -> None:
        """_validate raises ValueError when mcp_port exceeds 65535."""
        settings = Settings(mcp_port=65536)
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "mcp_port" in msg
        assert "65536" in msg

    def test_validate_accepts_mcp_port_boundary_values(self) -> None:
        """_validate accepts mcp_port values 1 and 65535 (boundary inclusive)."""
        Settings(mcp_port=1)._validate()
        Settings(mcp_port=65535)._validate()

    def test_validate_rejects_non_int_mcp_port(self) -> None:
        """_validate raises ValueError when mcp_port is not an int."""
        settings = Settings()
        settings.mcp_port = "8080"  # type: ignore[assignment]
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "mcp_port" in msg
        assert "8080" in msg

    def test_validate_rejects_bool_mcp_port(self) -> None:
        """_validate raises ValueError when mcp_port is a bool (bool is subclass of int)."""
        settings = Settings()
        settings.mcp_port = True  # type: ignore[assignment]
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "mcp_port" in msg
        assert "integer" in msg

    def test_validate_rejects_negative_mcp_port(self) -> None:
        """_validate raises ValueError when mcp_port is negative."""
        settings = Settings(mcp_port=-1)
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "mcp_port" in msg
        assert "between 1 and 65535" in msg
        assert "-1" in msg

    def test_validate_rejects_empty_activity_model(self) -> None:
        """_validate raises ValueError when activity_model is empty string."""
        settings = Settings(activity_model="")
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "activity_model" in msg
        assert "non-empty" in msg

    def test_validate_rejects_non_string_activity_model(self) -> None:
        """_validate raises ValueError when activity_model is not a string."""
        settings = Settings()
        settings.activity_model = None  # type: ignore[assignment]
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "activity_model" in msg
        assert "None" in msg


class TestSettingsLoad:
    """Tests for Settings.load() calling _validate()."""

    def test_load_calls_validate_and_raises_for_bad_port(self, tmp_path, monkeypatch) -> None:
        """load() raises ValueError when config file contains invalid mcp_port."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"mcp_port": 0}))

        monkeypatch.setattr("hamlet.config.settings.CONFIG_PATH", config_file)
        monkeypatch.setattr("hamlet.config.settings.ensure_hamlet_dir", lambda: None)

        with pytest.raises(ValueError) as exc_info:
            Settings.load()
        assert "mcp_port" in str(exc_info.value)

    def test_load_ignores_unknown_keys(self, tmp_path, monkeypatch) -> None:
        """load() silently drops unknown keys from old config files."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"mcp_port": 9090, "legacy_option": "old"}))

        monkeypatch.setattr("hamlet.config.settings.CONFIG_PATH", config_file)
        monkeypatch.setattr("hamlet.config.settings.ensure_hamlet_dir", lambda: None)

        settings = Settings.load()
        assert settings.mcp_port == 9090
        assert not hasattr(settings, "legacy_option")

    def test_load_defaults_pass_validation(self, tmp_path, monkeypatch) -> None:
        """load() succeeds with default values when no config file exists."""
        missing_config = tmp_path / "nonexistent.json"

        monkeypatch.setattr("hamlet.config.settings.CONFIG_PATH", missing_config)
        monkeypatch.setattr("hamlet.config.settings.ensure_hamlet_dir", lambda: None)

        settings = Settings.load()
        assert settings.mcp_port == 8080
        assert settings.db_path == "~/.hamlet/world.db"
        assert settings.activity_model == "claude-haiku-4-5-20251001"
