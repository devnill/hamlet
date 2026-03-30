"""Tests for hamlet.tui.village_menu module."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from hamlet.tui.village_menu import VillageMenu


# Minimal Village-like dataclass for testing
@dataclass
class MockVillage:
    """Mock village for testing."""

    id: str
    project_id: str
    name: str
    center_x: int = 0
    center_y: int = 0
    agent_ids: list | None = None
    structure_ids: list | None = None

    @property
    def center(self):
        """Return position-like object."""
        from hamlet.world_state.types import Position

        return Position(self.center_x, self.center_y)


def test_village_menu_render_empty():
    """VillageMenu renders 'No villages found' when empty."""
    menu = VillageMenu()
    output = menu.render()
    assert "No villages found" in output
    assert "Press v to close" in output


def test_village_menu_render_loading():
    """VillageMenu renders 'Loading villages...' when loading."""
    menu = VillageMenu(loading=True)
    output = menu.render()
    assert "Loading villages..." in output
    assert "Press v to close" in output


def test_village_menu_loading_state():
    """VillageMenu.set_loading() toggles the loading state."""
    menu = VillageMenu()
    assert menu._loading is False

    menu.set_loading(True)
    assert menu._loading is True
    output = menu.render()
    assert "Loading villages..." in output

    menu.set_loading(False)
    assert menu._loading is False
    output = menu.render()
    assert "No villages found" in output


def test_village_menu_render_with_villages():
    """VillageMenu renders a list of villages."""
    villages = [
        MockVillage(
            id="v1",
            project_id="project-alpha-123",
            name="Alpha Village",
            agent_ids=["a1", "a2"],
            structure_ids=["s1", "s2", "s3"],
        ),
        MockVillage(
            id="v2",
            project_id="project-beta-456",
            name="Beta Village",
            agent_ids=["a3"],
            structure_ids=["s4"],
        ),
    ]
    menu = VillageMenu(villages=villages)
    output = menu.render()

    assert "Alpha Village" in output
    assert "Beta Village" in output
    # Project IDs are shown (last 8 chars)
    assert "alpha-123" in output or "pha-123" in output  # truncated project id
    assert "beta-456" in output or "eta-456" in output  # truncated project id


def test_village_menu_current_village_highlighted():
    """VillageMenu highlights the current village."""
    villages = [
        MockVillage(id="v1", project_id="p1", name="Alpha"),
        MockVillage(id="v2", project_id="p2", name="Beta"),
    ]
    menu = VillageMenu(villages=villages, current_village_id="v2")
    output = menu.render()

    # Current village should have a * marker
    lines = output.split("\n")
    beta_line = [l for l in lines if "Beta" in l][0]
    assert "*" in beta_line  # Current marker
    assert "[cyan]" in beta_line or "cyan" in beta_line


def test_village_menu_selection_navigation():
    """VillageMenu selection moves with move_selection()."""
    villages = [
        MockVillage(id="v1", project_id="p1", name="Alpha"),
        MockVillage(id="v2", project_id="p2", name="Beta"),
        MockVillage(id="v3", project_id="p3", name="Gamma"),
    ]
    menu = VillageMenu(villages=villages, selected_index=0)

    # Initial selection
    assert menu._selected_index == 0
    assert menu.get_selected_village().id == "v1"

    # Move down
    menu.move_selection(1)
    assert menu._selected_index == 1
    assert menu.get_selected_village().id == "v2"

    # Move up
    menu.move_selection(-1)
    assert menu._selected_index == 0
    assert menu.get_selected_village().id == "v1"

    # Move past end (should clamp)
    menu.move_selection(100)
    assert menu._selected_index == 2
    assert menu.get_selected_village().id == "v3"

    # Move past start (should clamp)
    menu.move_selection(-100)
    assert menu._selected_index == 0
    assert menu.get_selected_village().id == "v1"


def test_village_menu_set_villages():
    """VillageMenu.set_villages() updates the list and clamps selection."""
    villages = [
        MockVillage(id="v1", project_id="p1", name="Alpha"),
        MockVillage(id="v2", project_id="p2", name="Beta"),
    ]
    menu = VillageMenu(villages=villages, selected_index=1)

    # Selection should be at index 1
    assert menu._selected_index == 1

    # Update to a shorter list - selection should clamp
    new_villages = [MockVillage(id="v3", project_id="p3", name="Gamma")]
    menu.set_villages(new_villages)
    assert menu._selected_index == 0  # Clamped to valid range


def test_village_menu_set_villages_sorting():
    """VillageMenu.set_villages() sorts villages by structures desc, agents desc, name asc."""
    villages = [
        MockVillage(id="v1", project_id="p1", name="Zebra", agent_ids=["a1"], structure_ids=[]),
        MockVillage(id="v2", project_id="p2", name="Alpha", agent_ids=["a1", "a2"], structure_ids=[]),
        MockVillage(id="v3", project_id="p3", name="Beta", agent_ids=["a1"], structure_ids=["s1", "s2", "s3"]),
        MockVillage(id="v4", project_id="p4", name="Gamma", agent_ids=["a1", "a2", "a3"], structure_ids=["s4", "s5"]),
        MockVillage(id="v5", project_id="p5", name="Delta", agent_ids=[], structure_ids=["s6", "s7", "s8", "s9"]),
    ]
    menu = VillageMenu()
    menu.set_villages(villages)

    # Sorting: structures desc, agents desc, name asc
    # v1 (Zebra): 0 structures, 1 agent
    # v2 (Alpha): 0 structures, 2 agents
    # v3 (Beta): 3 structures, 1 agent
    # v4 (Gamma): 2 structures, 3 agents
    # v5 (Delta): 4 structures, 0 agents
    # Expected order: Delta (4), Beta (3), Gamma (2), Alpha (0, 2 agents), Zebra (0, 1 agent)

    assert menu._villages[0].id == "v5"  # Delta - 4 structures
    assert menu._villages[1].id == "v3"  # Beta - 3 structures
    assert menu._villages[2].id == "v4"  # Gamma - 2 structures
    assert menu._villages[3].id == "v2"  # Alpha - 0 structures, 2 agents
    assert menu._villages[4].id == "v1"  # Zebra - 0 structures, 1 agent


def test_village_menu_set_villages_sorting_same_structures_agents():
    """VillageMenu sorts alphabetically when structures and agents are equal."""
    villages = [
        MockVillage(id="v1", project_id="p1", name="Charlie", agent_ids=["a1"], structure_ids=["s1"]),
        MockVillage(id="v2", project_id="p2", name="Alpha", agent_ids=["a2"], structure_ids=["s2"]),
        MockVillage(id="v3", project_id="p3", name="Bravo", agent_ids=["a3"], structure_ids=["s3"]),
    ]
    menu = VillageMenu()
    menu.set_villages(villages)

    # All have 1 structure and 1 agent, so sort by name alphabetically
    assert menu._villages[0].id == "v2"  # Alpha
    assert menu._villages[1].id == "v3"  # Bravo
    assert menu._villages[2].id == "v1"  # Charlie


def test_village_menu_set_villages_clears_loading():
    """VillageMenu.set_villages() clears loading state."""
    menu = VillageMenu(loading=True)
    assert menu._loading is True

    villages = [MockVillage(id="v1", project_id="p1", name="Alpha")]
    menu.set_villages(villages)
    assert menu._loading is False


def test_village_menu_get_selected_village_none():
    """VillageMenu.get_selected_village() returns None when empty."""
    menu = VillageMenu()
    assert menu.get_selected_village() is None


def test_village_menu_selected_marker():
    """VillageMenu shows > marker on selected row."""
    villages = [
        MockVillage(id="v1", project_id="p1", name="Alpha"),
        MockVillage(id="v2", project_id="p2", name="Beta"),
    ]
    menu = VillageMenu(villages=villages, selected_index=0)
    output = menu.render()

    lines = output.split("\n")
    # First village row should have ">" marker (selected)
    alpha_line = [l for l in lines if "Alpha" in l][0]
    assert ">" in alpha_line

    # Second village row should NOT have ">" marker
    beta_line = [l for l in lines if "Beta" in l][0]
    assert ">" not in beta_line


def test_village_menu_escape_hint():
    """VillageMenu shows Escape and v as close options."""
    menu = VillageMenu()
    output = menu.render()
    assert "Esc" in output
    assert "v" in output