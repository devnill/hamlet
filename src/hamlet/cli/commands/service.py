"""Service command for managing the hamlet daemon as a macOS launchd service."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from xml.sax.saxutils import escape

PLIST_LABEL = "com.hamlet.daemon"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"

PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hamlet.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>{hamlet_executable}</string>
        <string>daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{err_log_path}</string>
</dict>
</plist>
"""


def _check_platform() -> None:
    """Exit with an error message if not running on macOS."""
    if sys.platform != "darwin":
        print("hamlet service requires macOS. Linux systemd support is not yet implemented.")
        sys.exit(1)


def _find_hamlet_executable() -> str | None:
    """Find the hamlet executable via shutil.which or venv fallback."""
    exe = shutil.which("hamlet")
    if exe:
        return exe
    fallback = Path(sys.executable).parent / "hamlet"
    if fallback.exists():
        return str(fallback)
    return None


def _launchctl(args: list[str]) -> tuple[int, str]:
    """Run a launchctl command and return (returncode, output)."""
    result = subprocess.run(["launchctl"] + args, capture_output=True, text=True)
    return result.returncode, (result.stderr + result.stdout).strip()


def _service_is_running() -> bool:
    """Return True if the launchd service is currently loaded/running."""
    rc, _ = _launchctl(["list", PLIST_LABEL])
    return rc == 0


def _install(args: Namespace) -> int:
    """Install the hamlet daemon as a launchd service."""
    _check_platform()

    if PLIST_PATH.exists():
        if _service_is_running():
            print("Service is already installed and running. Run `hamlet service uninstall` first.")
        else:
            print("Service is already installed but not running. Run `hamlet service start` to start it.")
        return 0

    hamlet_exe = _find_hamlet_executable()
    if hamlet_exe is None:
        print("Error: could not find hamlet executable in PATH.")
        print("Make sure hamlet is installed: pip install hamlet")
        return 1

    log_dir = Path.home() / ".hamlet"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = str(log_dir / "daemon.log")
    err_log_path = str(log_dir / "daemon.err.log")

    plist_content = PLIST_TEMPLATE.format(
        hamlet_executable=escape(hamlet_exe),
        log_path=escape(log_path),
        err_log_path=escape(err_log_path),
    )

    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(plist_content, encoding="utf-8")

    rc, output = _launchctl(["bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH)])
    if rc != 0:
        print(f"Error: launchctl bootstrap failed: {output}")
        return 1

    print("hamlet service installed and started.")
    print(f"Plist: {PLIST_PATH}")
    print(f"Logs:  {log_path}")
    print(f"       {err_log_path}")
    return 0


def _uninstall(args: Namespace) -> int:
    """Uninstall the hamlet launchd service."""
    _check_platform()

    if _service_is_running():
        rc, output = _launchctl(["bootout", f"gui/{os.getuid()}/{PLIST_LABEL}"])
        if rc != 0 and output:
            print(f"Warning: launchctl bootout returned error: {output.strip()}")

    if PLIST_PATH.exists():
        PLIST_PATH.unlink()

    print("hamlet service uninstalled.")
    return 0


def _start(args: Namespace) -> int:
    """Load (start) the hamlet launchd service."""
    _check_platform()

    if not PLIST_PATH.exists():
        print("Service not installed. Run `hamlet service install` first.")
        return 1

    if _service_is_running():
        print("Service is already running.")
        return 0

    rc, output = _launchctl(["bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH)])
    if rc != 0:
        print(f"Error: launchctl bootstrap failed: {output}")
        return 1

    print("hamlet service started.")
    return 0


def _stop(args: Namespace) -> int:
    """Unload (stop) the hamlet launchd service."""
    _check_platform()

    if not _service_is_running():
        print("Service is not running.")
        return 0

    rc, output = _launchctl(["bootout", f"gui/{os.getuid()}/{PLIST_LABEL}"])
    if rc != 0:
        print(f"Error: launchctl bootout failed: {output}")
        return 1

    print("hamlet service stopped.")
    return 0


def _restart(args: Namespace) -> int:
    """Restart the hamlet launchd service."""
    _check_platform()

    if not PLIST_PATH.exists():
        print("Service not installed. Run `hamlet service install` first.")
        return 1

    if _service_is_running():
        rc, output = _launchctl(["bootout", f"gui/{os.getuid()}/{PLIST_LABEL}"])
        if rc != 0:
            print(f"Error stopping service: {output.strip()}")
            return 1

    rc, output = _launchctl(["bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH)])
    if rc != 0:
        print(f"Error: launchctl bootstrap failed: {output}")
        return 1

    print("hamlet service restarted.")
    return 0


def _status(args: Namespace) -> int:
    """Print the installation and running status of the hamlet service."""
    _check_platform()

    installed = PLIST_PATH.exists()
    running = _service_is_running()

    print(f"Service installed: {'yes' if installed else 'no'}")
    print(f"Daemon running:    {'yes' if running else 'no'}")
    return 0


def service_command(args: Namespace) -> int:
    """Dispatch to the appropriate service sub-command."""
    subcommand = getattr(args, "service_subcommand", None)
    dispatch = {
        "install": _install,
        "uninstall": _uninstall,
        "start": _start,
        "stop": _stop,
        "restart": _restart,
        "status": _status,
    }
    fn = dispatch.get(subcommand)
    if fn is None:
        print("Usage: hamlet service {install,uninstall,start,stop,restart,status}")
        return 1
    return fn(args)
