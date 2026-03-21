"""World state data model types for Hamlet."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class AgentType(Enum):
    """Inferred agent type based on tool usage patterns."""
    RESEARCHER = "researcher"
    CODER = "coder"
    PLANNER = "planner"
    EXECUTOR = "executor"
    ARCHITECT = "architect"
    TESTER = "tester"
    GENERAL = "general"


class StructureType(Enum):
    """Types of structures that can be built in a village."""
    HOUSE = "house"
    WORKSHOP = "workshop"
    LIBRARY = "library"
    FORGE = "forge"
    TOWER = "tower"
    ROAD = "road"
    WELL = "well"


class AgentState(Enum):
    """Current lifecycle state of an agent."""
    ACTIVE = "active"
    IDLE = "idle"
    ZOMBIE = "zombie"


@dataclass(frozen=True)
class Position:
    """World coordinate position. Immutable and hashable for use in dicts/sets."""
    x: int
    y: int


@dataclass
class Bounds:
    """Bounding box for a region in world coordinates."""
    min_x: int
    min_y: int
    max_x: int
    max_y: int


@dataclass
class Project:
    """A Claude Code project (codebase), mapped to one village."""
    id: str
    name: str
    village_id: str
    config: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Session:
    """A Claude Code session within a project."""
    id: str
    project_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    agent_ids: list[str] = field(default_factory=list)


@dataclass
class Village:
    """A village on the world map, one per project."""
    id: str
    project_id: str
    name: str
    center: Position = field(default_factory=lambda: Position(0, 0))
    bounds: Bounds = field(default_factory=lambda: Bounds(0, 0, 0, 0))
    structure_ids: list[str] = field(default_factory=list)
    agent_ids: list[str] = field(default_factory=list)
    has_expanded: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Agent:
    """An agent active in a village."""
    id: str
    session_id: str
    project_id: str  # persisted to agents table via migration 2
    village_id: str = ""
    inferred_type: AgentType = AgentType.GENERAL
    color: str = "white"
    position: Position = field(default_factory=lambda: Position(0, 0))
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    state: AgentState = AgentState.ACTIVE
    parent_id: str | None = None
    current_activity: str | None = None
    total_work_units: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Structure:
    """A structure built in a village."""
    id: str
    village_id: str
    type: StructureType
    position: Position = field(default_factory=lambda: Position(0, 0))
    stage: int = 0
    material: str = "wood"
    work_units: int = 0
    work_required: int = 100
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "AgentType",
    "StructureType",
    "AgentState",
    "Position",
    "Bounds",
    "Project",
    "Session",
    "Village",
    "Agent",
    "Structure",
]
