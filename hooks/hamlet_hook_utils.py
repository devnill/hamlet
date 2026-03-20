#!/usr/bin/env python3
"""Shared utilities for Hamlet hook scripts."""
import hashlib
import json
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path


def _cwd_hash(cwd: Path) -> str:
    return hashlib.sha256(str(cwd).encode()).hexdigest()[:16]


def _log_error(hook_name: str, exc: Exception) -> None:
    """Log hook errors to file for debugging."""
    try:
        log_dir = Path.home() / ".hamlet"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "hooks.log"
        timestamp = datetime.now(timezone.utc).isoformat()
        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] {hook_name}: {exc}\n{traceback.format_exc()}\n")
    except Exception:
        pass


def find_server_url() -> str:
    """Read server_url: check project config first, then global, then default."""
    default = "http://localhost:8080/hamlet/event"
    cwd = Path(os.getcwd())
    for directory in [cwd, *cwd.parents]:
        config_path = directory / ".hamlet" / "config.json"
        if config_path.exists():
            try:
                cfg = json.loads(config_path.read_text())
                url = cfg.get("server_url", "")
                if url:
                    return url
            except Exception as exc:
                _log_error("find_server_url", exc)
    try:
        config_path = Path.home() / ".hamlet" / "config.json"
        if config_path.exists():
            data = json.loads(config_path.read_text())
            url = data.get("server_url", "")
            return url if url else default
    except Exception as exc:
        _log_error("find_server_url", exc)
    return default


def find_config() -> tuple[str, str]:
    """Traverse from cwd up to root looking for .hamlet/config.json with project_id."""
    cwd = Path(os.getcwd())
    for directory in [cwd, *cwd.parents]:
        config_path = directory / ".hamlet" / "config.json"
        if config_path.exists():
            try:
                cfg = json.loads(config_path.read_text())
                pid = cfg.get("project_id", "")
                if pid:
                    return pid, cfg.get("project_name", directory.name)
            except Exception as exc:
                _log_error("find_config", exc)
    return f"project-{_cwd_hash(cwd)}", cwd.name
