"""Tests for hamlet service command (work item WI-204)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

import hamlet.cli.commands.service as svc_module
from hamlet.cli.commands.service import (
    PLIST_LABEL,
    PLIST_PATH,
    service_command,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args(**kwargs):
    """Build a minimal Namespace for service sub-commands."""
    from argparse import Namespace
    defaults = {"service_subcommand": None}
    defaults.update(kwargs)
    return Namespace(**defaults)


def _run_service(subcommand: str):
    """Return (exit_code_or_return, stdout) for the given subcommand.

    Uses sys.exit side-effects where appropriate; caller wraps in
    pytest.raises(SystemExit) when an exit is expected.
    """
    args = _make_args(service_subcommand=subcommand)
    return service_command(args)


# ---------------------------------------------------------------------------
# Non-macOS platform guard
# ---------------------------------------------------------------------------

class TestNonMacosPlatformGuard:
    """Every sub-command must exit 1 with a clear message on non-macOS."""

    SUBCOMMANDS = ["install", "uninstall", "start", "stop", "restart", "status"]

    @pytest.mark.parametrize("subcommand", SUBCOMMANDS)
    def test_exits_on_non_macos(self, subcommand: str, capsys) -> None:
        with patch.object(sys, "platform", "linux"):
            with pytest.raises(SystemExit) as exc_info:
                _run_service(subcommand)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "macOS" in captured.out


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

class TestInstallCommand:
    """Tests for `hamlet service install`."""

    def _patch_common(self, which_result="/usr/local/bin/hamlet"):
        """Return a stack of patches common to most install tests."""
        return [
            patch("sys.platform", "darwin"),
            patch("shutil.which", return_value=which_result),
            patch.object(Path, "mkdir", return_value=None),
            patch.object(Path, "write_text", return_value=None),
            patch(
                "hamlet.cli.commands.service._launchctl",
                return_value=(0, ""),
            ),
            patch("hamlet.cli.commands.service._service_is_running", return_value=False),
            patch("hamlet.cli.commands.service.PLIST_PATH"),
        ]

    def test_happy_path(self, capsys) -> None:
        """install writes the plist and loads it via launchctl."""
        patches = self._patch_common()
        with patches[0], patches[1], patches[2], patches[3], patches[4] as mock_launchctl, \
             patches[5], patches[6] as mock_plist_path:
            mock_plist_path.exists.return_value = False
            mock_plist_path.__str__ = lambda self: str(PLIST_PATH)
            mock_plist_path.parent = PLIST_PATH.parent
            result = _run_service("install")

        assert result == 0
        import os
        mock_launchctl.assert_called_once_with(["bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH)])
        captured = capsys.readouterr()
        assert "installed" in captured.out

    def test_plist_content_contains_executable_and_keys(self) -> None:
        """Plist written to disk must contain required keys and the hamlet path."""
        written_content: list[str] = []

        def capture_write(content, **kwargs):
            written_content.append(content)

        with patch("sys.platform", "darwin"), \
             patch("shutil.which", return_value="/usr/local/bin/hamlet"), \
             patch.object(Path, "mkdir", return_value=None), \
             patch("hamlet.cli.commands.service._launchctl", return_value=(0, "")), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=False), \
             patch("hamlet.cli.commands.service.PLIST_PATH") as mock_plist_path:
            mock_plist_path.exists.return_value = False
            mock_plist_path.parent = PLIST_PATH.parent
            mock_plist_path.write_text.side_effect = capture_write
            _run_service("install")

        assert written_content, "write_text was never called"
        plist = written_content[0]
        assert "/usr/local/bin/hamlet" in plist
        assert "KeepAlive" in plist
        assert "RunAtLoad" in plist
        assert "daemon.log" in plist
        assert "daemon.err.log" in plist

    def test_executable_not_found_exits(self, capsys) -> None:
        """install returns 1 with a clear error when hamlet cannot be found."""
        fake_parent = MagicMock()
        fake_parent.__truediv__ = MagicMock(
            return_value=MagicMock(exists=MagicMock(return_value=False))
        )
        fake_sys_executable_path = MagicMock()
        fake_sys_executable_path.parent = fake_parent

        with patch("sys.platform", "darwin"), \
             patch("shutil.which", return_value=None), \
             patch("hamlet.cli.commands.service.Path", wraps=Path) as mock_path:
            # Make sys.executable parent / "hamlet" not exist
            with patch.object(Path, "exists", return_value=False), \
                 patch("hamlet.cli.commands.service.shutil.which", return_value=None):
                result = _run_service("install")

        assert result == 1
        captured = capsys.readouterr()
        assert "hamlet executable" in captured.out

    def test_launchctl_failure_exits(self, capsys) -> None:
        """install returns 1 when launchctl load returns non-zero."""
        with patch("sys.platform", "darwin"), \
             patch("shutil.which", return_value="/usr/local/bin/hamlet"), \
             patch.object(Path, "mkdir", return_value=None), \
             patch.object(Path, "write_text", return_value=None), \
             patch("hamlet.cli.commands.service._launchctl", return_value=(1, "error msg")), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=False), \
             patch("hamlet.cli.commands.service.PLIST_PATH") as mock_plist_path:
            mock_plist_path.exists.return_value = False
            mock_plist_path.parent = PLIST_PATH.parent
            result = _run_service("install")

        assert result == 1
        captured = capsys.readouterr()
        assert "launchctl bootstrap failed" in captured.out

    def test_venv_fallback_executable(self, capsys) -> None:
        """install uses sys.executable parent when shutil.which returns None."""
        with patch("sys.platform", "darwin"), \
             patch("hamlet.cli.commands.service._find_hamlet_executable",
                   return_value="/venv/bin/hamlet"), \
             patch.object(Path, "mkdir", return_value=None), \
             patch.object(Path, "write_text", return_value=None), \
             patch("hamlet.cli.commands.service._launchctl", return_value=(0, "")):
            result = _run_service("install")

        assert result == 0

    def test_install_when_already_running_exits_gracefully(self, capsys) -> None:
        """install prints an informational message and returns 0 when already installed and running."""
        with patch("hamlet.cli.commands.service.sys.platform", "darwin"), \
             patch("hamlet.cli.commands.service._find_hamlet_executable",
                   return_value="/usr/local/bin/hamlet"), \
             patch("hamlet.cli.commands.service.PLIST_PATH") as mock_path, \
             patch("hamlet.cli.commands.service._service_is_running", return_value=True):
            mock_path.exists.return_value = True
            result = _run_service("install")

        assert result == 0
        captured = capsys.readouterr()
        assert "already installed and running" in captured.out
        assert "uninstall" in captured.out

    def test_install_when_plist_exists_but_not_running(self, capsys) -> None:
        """install returns 0 with a 'not running' message when plist exists but service is not running."""
        with patch("hamlet.cli.commands.service.sys.platform", "darwin"), \
             patch("hamlet.cli.commands.service._find_hamlet_executable",
                   return_value="/usr/local/bin/hamlet"), \
             patch("hamlet.cli.commands.service.PLIST_PATH") as mock_path, \
             patch("hamlet.cli.commands.service._service_is_running", return_value=False):
            mock_path.exists.return_value = True
            result = _run_service("install")

        assert result == 0
        captured = capsys.readouterr()
        assert "not running" in captured.out
        assert "start" in captured.out


# ---------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------

class TestUninstallCommand:
    """Tests for `hamlet service uninstall`."""

    def test_happy_path_unloads_and_removes(self, capsys) -> None:
        """uninstall unloads the service and deletes the plist."""
        with patch("sys.platform", "darwin"), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=True), \
             patch("hamlet.cli.commands.service._launchctl", return_value=(0, "")) as mock_lctl, \
             patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "unlink") as mock_unlink:
            result = _run_service("uninstall")

        assert result == 0
        import os
        mock_lctl.assert_called_once_with(["bootout", f"gui/{os.getuid()}/{PLIST_LABEL}"])
        mock_unlink.assert_called_once()
        assert "uninstalled" in capsys.readouterr().out

    def test_not_installed_no_error(self, capsys) -> None:
        """uninstall succeeds gracefully when the service is not installed."""
        with patch("sys.platform", "darwin"), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=False), \
             patch.object(Path, "exists", return_value=False), \
             patch("hamlet.cli.commands.service._launchctl", return_value=(0, "")) as mock_lctl:
            result = _run_service("uninstall")

        assert result == 0
        mock_lctl.assert_not_called()

    def test_not_running_skips_unload(self) -> None:
        """uninstall does not call launchctl unload when service is not running."""
        with patch("sys.platform", "darwin"), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=False), \
             patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "unlink"), \
             patch("hamlet.cli.commands.service._launchctl") as mock_lctl:
            _run_service("uninstall")

        mock_lctl.assert_not_called()


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------

class TestStartCommand:
    """Tests for `hamlet service start`."""

    def test_not_installed_exits(self, capsys) -> None:
        """start returns 1 when the plist does not exist."""
        with patch("sys.platform", "darwin"), \
             patch.object(Path, "exists", return_value=False):
            result = _run_service("start")

        assert result == 1
        assert "not installed" in capsys.readouterr().out

    def test_already_running_returns_zero(self, capsys) -> None:
        """start exits 0 with an informational message when already running."""
        with patch("sys.platform", "darwin"), \
             patch.object(Path, "exists", return_value=True), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=True):
            result = _run_service("start")

        assert result == 0
        assert "already running" in capsys.readouterr().out

    def test_happy_path(self, capsys) -> None:
        """start loads the service when the plist exists and it is not running."""
        with patch("sys.platform", "darwin"), \
             patch.object(Path, "exists", return_value=True), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=False), \
             patch("hamlet.cli.commands.service._launchctl", return_value=(0, "")) as mock_lctl:
            result = _run_service("start")

        assert result == 0
        import os
        mock_lctl.assert_called_once_with(["bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH)])
        assert "started" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------

class TestStopCommand:
    """Tests for `hamlet service stop`."""

    def test_not_running_returns_zero(self, capsys) -> None:
        """stop exits 0 with an informational message when not running."""
        with patch("sys.platform", "darwin"), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=False):
            result = _run_service("stop")

        assert result == 0
        assert "not running" in capsys.readouterr().out

    def test_happy_path(self, capsys) -> None:
        """stop unloads the service when it is running."""
        with patch("sys.platform", "darwin"), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=True), \
             patch("hamlet.cli.commands.service._launchctl", return_value=(0, "")) as mock_lctl:
            result = _run_service("stop")

        assert result == 0
        import os
        mock_lctl.assert_called_once_with(["bootout", f"gui/{os.getuid()}/{PLIST_LABEL}"])
        assert "stopped" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# restart
# ---------------------------------------------------------------------------

class TestRestartCommand:
    """Tests for `hamlet service restart`."""

    def test_happy_path(self, capsys) -> None:
        """restart unloads (if running) then loads the service."""
        launchctl_calls: list = []

        def mock_launchctl(args):
            launchctl_calls.append(args)
            return (0, "")

        with patch("sys.platform", "darwin"), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=True), \
             patch.object(Path, "exists", return_value=True), \
             patch("hamlet.cli.commands.service._launchctl", side_effect=mock_launchctl):
            result = _run_service("restart")

        import os
        assert result == 0
        assert ["bootout", f"gui/{os.getuid()}/{PLIST_LABEL}"] in launchctl_calls
        assert ["bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH)] in launchctl_calls
        assert "restarted" in capsys.readouterr().out

    def test_restart_when_not_running(self, capsys) -> None:
        """restart skips unload and just loads when service is not running."""
        launchctl_calls: list = []

        def mock_launchctl(args):
            launchctl_calls.append(args)
            return (0, "")

        with patch("sys.platform", "darwin"), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=False), \
             patch.object(Path, "exists", return_value=True), \
             patch("hamlet.cli.commands.service._launchctl", side_effect=mock_launchctl):
            result = _run_service("restart")

        import os
        assert result == 0
        assert ["bootout", f"gui/{os.getuid()}/{PLIST_LABEL}"] not in launchctl_calls
        assert ["bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH)] in launchctl_calls


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

class TestStatusCommand:
    """Tests for `hamlet service status`."""

    def test_installed_and_running(self, capsys) -> None:
        """status reports installed=yes and running=yes."""
        with patch("sys.platform", "darwin"), \
             patch.object(Path, "exists", return_value=True), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=True):
            result = _run_service("status")

        assert result == 0
        out = capsys.readouterr().out
        assert "Service installed: yes" in out
        assert "Daemon running:" in out
        assert "yes" in out

    def test_installed_not_running(self, capsys) -> None:
        """status reports installed=yes and running=no."""
        with patch("sys.platform", "darwin"), \
             patch.object(Path, "exists", return_value=True), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=False):
            result = _run_service("status")

        assert result == 0
        out = capsys.readouterr().out
        assert "Service installed: yes" in out
        assert "Daemon running:    no" in out

    def test_not_installed(self, capsys) -> None:
        """status reports installed=no and running=no."""
        with patch("sys.platform", "darwin"), \
             patch.object(Path, "exists", return_value=False), \
             patch("hamlet.cli.commands.service._service_is_running", return_value=False):
            result = _run_service("status")

        assert result == 0
        out = capsys.readouterr().out
        assert "Service installed: no" in out
        assert "Daemon running:    no" in out


# ---------------------------------------------------------------------------
# CLI registration smoke test
# ---------------------------------------------------------------------------

class TestCliRegistration:
    """Verify the service subcommand appears in the top-level CLI."""

    def test_service_in_help(self, capsys) -> None:
        """hamlet --help output includes the service subcommand."""
        from hamlet.cli import create_parser
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])
        out = capsys.readouterr().out
        assert "service" in out
