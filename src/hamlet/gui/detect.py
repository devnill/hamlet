"""Renderer detection and resolution for hamlet GUI."""

from __future__ import annotations

from typing import Optional


def detect_renderer() -> str:
    """Detect the best available renderer for this environment.

    Returns:
        "kitty" if the Kitty graphics protocol is available, else "textual".
    """
    try:
        from hamlet.gui.kitty import KITTY_AVAILABLE
        if KITTY_AVAILABLE:
            return "kitty"
    except Exception:
        pass
    return "textual"


def resolve_renderer(
    cli_arg: Optional[str],
    settings_value: str,
) -> str:
    """Resolve the renderer to use, applying precedence rules.

    Precedence (highest to lowest):
      1. cli_arg — if not None, use it directly
      2. settings_value — if not "auto", use it directly
      3. detect_renderer() — called when settings_value is "auto"

    Args:
        cli_arg: Renderer name passed via CLI flag, or None if not supplied.
        settings_value: Renderer value from settings (e.g. "auto", "textual").

    Returns:
        The resolved renderer name ("textual", "kitty", or the value from cli_arg/settings).
    """
    if cli_arg is not None:
        return cli_arg
    if settings_value == "auto":
        return detect_renderer()
    return settings_value
