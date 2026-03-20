"""LegendOverlay widget — shows a reference legend for Hamlet TUI symbols."""
from __future__ import annotations

from textual.widgets import Static

__all__ = ["LegendOverlay"]


class LegendOverlay(Static):
    """Modal overlay displaying the legend for agents, structures, materials, and states.

    Toggled by ``/`` from HamletApp; dismissed by ``Esc`` from HamletApp.
    """

    DEFAULT_CSS = "LegendOverlay { display: none; }"

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> str:
        """Return Rich-markup string with full legend content."""
        return (
            "┌─ Legend ─────────────────────────────────────┐\n"
            "│ [bold]Agents[/bold]                                         │\n"
            "│  [cyan]@[/cyan] Researcher  [cyan](cyan)[/cyan]                          │\n"
            "│  [yellow]@[/yellow] Coder       [yellow](yellow)[/yellow]                       │\n"
            "│  [dark_green]@[/dark_green] Planner     [dark_green](dark_green)[/dark_green]                   │\n"
            "│  [orange1]@[/orange1] Executor    [orange1](orange1)[/orange1]                      │\n"
            "│  [magenta]@[/magenta] Architect   [magenta](magenta)[/magenta]                     │\n"
            "│  [blue]@[/blue] Tester      [blue](blue)[/blue]                         │\n"
            "│  [white]@[/white] General     [white](white)[/white]                        │\n"
            "│                                               │\n"
            "│ [bold]Structures[/bold]                                     │\n"
            "│  ∩ House    ◊ Workshop    ⌂ Library          │\n"
            "│  ▲ Forge    ⎔ Tower       # Road             │\n"
            "│  ○ Well                                       │\n"
            "│                                               │\n"
            "│ [bold]Materials:[/bold]                                     │\n"
            "│  ░ Wood → ▒ Stone → ▓ Brick → █ Enhanced     │\n"
            "│                                               │\n"
            "│ [bold]States:[/bold]                                        │\n"
            "│  -\\|/ Active    @ Idle    [bright_green]@[/bright_green] Zombie (bright_green) │\n"
            "│                                               │\n"
            "│ [dim]Press / to toggle  •  Esc to close[/dim]           │\n"
            "└───────────────────────────────────────────────┘"
        )
