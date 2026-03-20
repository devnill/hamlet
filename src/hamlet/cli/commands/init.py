"""Init command — creates per-project hamlet config."""
from __future__ import annotations
import json
import uuid
from argparse import Namespace
from pathlib import Path


def init_command(args: Namespace) -> int:
    cwd = Path.cwd()
    config_dir = cwd / ".hamlet"
    config_path = config_dir / "config.json"

    if config_path.exists():
        print(f"Config already exists at {config_path}:")
        print(config_path.read_text())
        print()
        print("Overwrite? (y/N): ", end="", flush=True)
        try:
            response = input().strip().lower()
        except EOFError:
            response = ""
        if response not in ("y", "yes"):
            print("Cancelled.")
            return 0

    try:
        from hamlet.config.settings import Settings
        settings = Settings.load()
        mcp_port = settings.mcp_port
    except Exception:
        mcp_port = 8080

    config_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "project_id": str(uuid.uuid4()),
        "project_name": cwd.name,
        "server_url": f"http://localhost:{mcp_port}/hamlet/event"
    }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Created {config_path}:")
    print(json.dumps(config, indent=2))
    return 0
