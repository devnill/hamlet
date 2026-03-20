#!/bin/sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if command -v uv >/dev/null 2>&1; then
    exec uv run --script "${SCRIPT_DIR}/server.py"
else
    # python3 fallback: requires mcp package pre-installed
    if ! command -v python3 >/dev/null 2>&1; then
        echo "hamlet: python3 not found. Install uv (https://docs.astral.sh/uv/) or ensure python3 is on PATH." >&2
        exit 1
    fi
    if ! python3 -c "from mcp.server import Server" 2>/dev/null; then
        echo "hamlet: mcp package not found. Install uv (https://docs.astral.sh/uv/) or run: python3 -m pip install mcp" >&2
        exit 1
    fi
    exec python3 "${SCRIPT_DIR}/server.py"
fi
