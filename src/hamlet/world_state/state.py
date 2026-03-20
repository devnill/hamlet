"""WorldState container and EventLogEntry for the Hamlet world model."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .types import (
    Agent,
    AgentState,
    AgentType,
    Bounds,
    Position,
    Project,
    Session,
    Structure,
    StructureType,
    Village,
)

__all__ = ["WorldState", "EventLogEntry"]


@dataclass
class EventLogEntry:
    """A single entry in the chronological event log."""

    id: str
    timestamp: datetime
    session_id: str
    project_id: str
    hook_type: str
    tool_name: str | None
    summary: str


class WorldState:
    """Container for all world state: projects, sessions, agents, villages, and structures."""

    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}
        self.sessions: dict[str, Session] = {}
        self.agents: dict[str, Agent] = {}
        self.villages: dict[str, Village] = {}
        self.structures: dict[str, Structure] = {}
        self.event_log: list[EventLogEntry] = []
        self.world_metadata: dict[str, str] = {}
