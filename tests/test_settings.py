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


class TestSettingsZombieDespawn:
    """Tests for zombie_despawn_seconds setting."""

    def test_zombie_despawn_seconds_defaults_to_300(self) -> None:
        """zombie_despawn_seconds defaults to 300."""
        settings = Settings()
        assert settings.zombie_despawn_seconds == 300


class TestSettingsZombieThreshold:
    """Tests for zombie_threshold_seconds validation."""

    def test_validate_rejects_zero_zombie_threshold(self) -> None:
        """_validate raises ValueError when zombie_threshold_seconds is 0."""
        settings = Settings(zombie_threshold_seconds=0)
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "zombie_threshold_seconds" in msg
        assert "0" in msg

    def test_validate_rejects_negative_zombie_threshold(self) -> None:
        """_validate raises ValueError when zombie_threshold_seconds is negative."""
        settings = Settings(zombie_threshold_seconds=-5)
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "zombie_threshold_seconds" in msg
        assert "-5" in msg

    def test_validate_rejects_non_int_zombie_threshold(self) -> None:
        """_validate raises ValueError when zombie_threshold_seconds is not an integer."""
        settings = Settings()
        settings.zombie_threshold_seconds = "300"  # type: ignore[assignment]
        with pytest.raises(ValueError) as exc_info:
            settings._validate()
        msg = str(exc_info.value)
        assert "zombie_threshold_seconds" in msg
        assert "integer" in msg

    def test_validate_accepts_positive_zombie_threshold(self) -> None:
        """_validate accepts any positive integer for zombie_threshold_seconds."""
        Settings(zombie_threshold_seconds=1)._validate()
        Settings(zombie_threshold_seconds=600)._validate()


class TestSettingsMinVillageDistance:
    """Validation tests for min_village_distance field."""

    def test_validate_rejects_zero(self) -> None:
        with pytest.raises(ValueError, match="min_village_distance"):
            Settings(min_village_distance=0)._validate()

    def test_validate_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match="min_village_distance"):
            Settings(min_village_distance=-1)._validate()

    def test_validate_rejects_non_int(self) -> None:
        s = Settings()
        s.min_village_distance = "15"  # type: ignore
        with pytest.raises(ValueError, match="min_village_distance"):
            s._validate()

    def test_validate_rejects_bool(self) -> None:
        s = Settings()
        s.min_village_distance = True  # type: ignore
        with pytest.raises(ValueError, match="min_village_distance"):
            s._validate()

    def test_validate_accepts_positive(self) -> None:
        Settings(min_village_distance=1)._validate()
        Settings(min_village_distance=15)._validate()
        Settings(min_village_distance=100)._validate()


class TestSettingsDiff:
    """Tests for Settings.diff() method."""

    def test_no_changes_returns_empty(self) -> None:
        a = Settings()
        b = Settings()
        assert a.diff(b) == {}

    def test_single_field_change(self) -> None:
        a = Settings(mcp_port=8080)
        b = Settings(mcp_port=9090)
        result = a.diff(b)
        assert result == {"mcp_port": (8080, 9090)}

    def test_multiple_fields_changed(self) -> None:
        a = Settings(mcp_port=8080, tick_rate=30.0)
        b = Settings(mcp_port=9090, tick_rate=60.0)
        result = a.diff(b)
        assert "mcp_port" in result
        assert "tick_rate" in result
        assert result["mcp_port"] == (8080, 9090)
        assert result["tick_rate"] == (30.0, 60.0)

    def test_terrain_dict_change_detected(self) -> None:
        a = Settings(terrain={"seed": 42})
        b = Settings(terrain={"seed": 99})
        result = a.diff(b)
        assert "terrain" in result
        assert result["terrain"] == ({"seed": 42}, {"seed": 99})

    def test_unchanged_fields_excluded(self) -> None:
        a = Settings(mcp_port=8080, tick_rate=30.0)
        b = Settings(mcp_port=9090, tick_rate=30.0)
        result = a.diff(b)
        assert "mcp_port" in result
        assert "tick_rate" not in result


class TestSettingsRenderer:
    """Validation tests for renderer field."""

    def test_validate_accepts_auto(self) -> None:
        Settings(renderer="auto")._validate()

    def test_validate_accepts_textual(self) -> None:
        Settings(renderer="textual")._validate()

    def test_validate_accepts_kitty(self) -> None:
        Settings(renderer="kitty")._validate()

    def test_validate_rejects_notcurses(self) -> None:
        with pytest.raises(ValueError, match="renderer"):
            Settings(renderer="notcurses")._validate()

    def test_validate_rejects_invalid(self) -> None:
        with pytest.raises(ValueError, match="renderer"):
            Settings(renderer="pygame")._validate()
