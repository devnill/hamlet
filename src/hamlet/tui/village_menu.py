"""VillageMenu overlay widget — jump to village centers."""
from __future__ import annotations

from textual.widgets import Static

__all__ = ["VillageMenu"]


class VillageMenu(Static):
    """Modal overlay displaying a list of villages for navigation.

    Toggled by ``v`` from HamletApp. Shows village name, project name,
    agent count, and structure count. Navigate with arrow keys or j/k,
    press Enter to jump to selected village center, Escape or ``v`` to close.

    The current village (nearest to viewport center) is highlighted.
    """

    DEFAULT_CSS = """
VillageMenu {
    display: none;
    layer: overlay;
    offset: 2 2;
    width: 60;
    height: auto;
    max-height: 20;
    background: $panel;
    border: solid $primary;
}
"""

    def __init__(
        self,
        villages: list | None = None,
        current_village_id: str | None = None,
        selected_index: int = 0,
        loading: bool = False,
    ) -> None:
        """Initialize the menu.

        Args:
            villages: List of Village objects to display.
            current_village_id: ID of the currently active village for highlighting.
            selected_index: Currently selected row index.
            loading: Whether the menu is in a loading state.
        """
        super().__init__()
        self._villages = villages or []
        self._current_village_id = current_village_id
        self._selected_index = selected_index
        self._loading = loading

    def set_loading(self, loading: bool) -> None:
        """Set the loading state of the menu.

        Args:
            loading: True to show loading state, False to show villages.
        """
        self._loading = loading

    def set_villages(self, villages: list, current_village_id: str | None = None) -> None:
        """Update the list of villages to display.

        Villages are sorted by structure count (descending), then agent count (descending),
        then name alphabetically (case-insensitive).

        Args:
            villages: List of Village objects.
            current_village_id: ID of the currently active village for highlighting.
        """
        # Sort villages: structures desc, agents desc, name asc (case-insensitive)
        sorted_villages = sorted(
            villages,
            key=lambda v: (
                -len(getattr(v, "structure_ids", []) or []),
                -len(getattr(v, "agent_ids", []) or []),
                getattr(v, "name", "").lower(),
            ),
        )
        self._villages = sorted_villages
        self._current_village_id = current_village_id
        self._loading = False  # Data loaded, no longer loading
        # Clamp selected index to valid range
        if self._villages:
            self._selected_index = min(self._selected_index, len(self._villages) - 1)
        else:
            self._selected_index = 0

    def get_selected_village(self) -> object | None:
        """Return the currently selected village, or None if no villages."""
        if self._villages and 0 <= self._selected_index < len(self._villages):
            return self._villages[self._selected_index]
        return None

    def move_selection(self, delta: int) -> None:
        """Move the selection up or down by delta rows.

        Args:
            delta: Number of rows to move (negative for up, positive for down).
        """
        if not self._villages:
            return
        new_index = self._selected_index + delta
        new_index = max(0, min(new_index, len(self._villages) - 1))
        self._selected_index = new_index

    def render(self) -> str:
        """Return Rich-markup string with village list."""
        # Show loading state if data is being fetched
        if self._loading:
            return (
                "┌─ Villages ────────────────────────────────────────────┐\n"
                "│  [dim]Loading villages...[/dim]                           │\n"
                "│                                                       │\n"
                "│  [dim]Press v to close  •  Esc to close[/dim]              │\n"
                "└───────────────────────────────────────────────────────┘"
            )

        if not self._villages:
            return (
                "┌─ Villages ────────────────────────────────────────────┐\n"
                "│  [dim]No villages found[/dim]                               │\n"
                "│                                                       │\n"
                "│  [dim]Press v to close  •  Esc to close[/dim]              │\n"
                "└───────────────────────────────────────────────────────┘"
            )

        lines = [
            "┌─ Villages ────────────────────────────────────────────┐",
            "│  Name / Project            Agents  Structures        │",
        ]

        for i, village in enumerate(self._villages):
            # Get village attributes with safe defaults
            name = getattr(village, "name", "Unknown")
            project_id = getattr(village, "project_id", "")
            agent_ids = getattr(village, "agent_ids", [])
            structure_ids = getattr(village, "structure_ids", [])
            village_id = getattr(village, "id", "")

            # Truncate name if too long
            if len(name) > 18:
                name = name[:15] + "..."

            # Truncate project_id for display (last 8 chars for brevity)
            project_display = project_id[-8:] if len(project_id) > 8 else project_id

            # Count agents and structures
            agent_count = len(agent_ids) if isinstance(agent_ids, list) else 0
            structure_count = len(structure_ids) if isinstance(structure_ids, list) else 0

            # Highlight current village and selected row
            is_current = village_id == self._current_village_id
            is_selected = i == self._selected_index

            # Selection marker and current marker
            if is_selected:
                marker = ">"
            else:
                marker = " "

            # Current village marker
            current_marker = "*" if is_current else " "

            # Build display line: name, project_id, counts
            # Format: "  Name (project)      Agents  Structures"
            name_field = f"{name} ({project_display})"
            name_field = name_field[:28].ljust(28)

            if is_current:
                if is_selected:
                    line = f"│{marker}{current_marker} [bold cyan]{name_field}[/bold cyan] {agent_count:3d}     {structure_count:3d}"
                else:
                    line = f"│{marker}{current_marker} [cyan]{name_field}[/cyan] {agent_count:3d}     {structure_count:3d}"
            elif is_selected:
                line = f"│{marker}{current_marker} [bold]{name_field}[/bold] {agent_count:3d}     {structure_count:3d}"
            else:
                line = f"│{marker}{current_marker} {name_field} {agent_count:3d}     {structure_count:3d}"

            lines.append(line)

        # Add instructions
        lines.append("│                                                       │")
        lines.append("│  [dim]* = current  •  j/k or arrows navigate[/dim]          │")
        lines.append("│  [dim]Enter jump  •  v/Esc close[/dim]                     │")
        lines.append("└───────────────────────────────────────────────────────┘")

        return "\n".join(lines)