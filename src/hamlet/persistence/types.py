"""Persistence layer data structures for Hamlet."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


EntityType = Literal["project", "session", "agent", "structure", "village", "event_log", "world_metadata"]

Operation = Literal["insert", "update", "delete"]


@dataclass
class WriteOperation:
    """A queued write to the database."""
    entity_type: EntityType
    entity_id: str
    operation: Operation
    data: dict[str, Any]


@dataclass
class PersistenceConfig:
    """Configuration for the persistence layer."""
    db_path: str = field(
        default_factory=lambda: str(Path("~/.hamlet/world.db").expanduser())
    )
    write_queue_size: int = 1000
    checkpoint_interval: float = 5.0


@dataclass
class WorldStateData:
    """All entities loaded from the database on startup."""
    projects: list[dict[str, Any]] = field(default_factory=list)
    sessions: list[dict[str, Any]] = field(default_factory=list)
    villages: list[dict[str, Any]] = field(default_factory=list)
    agents: list[dict[str, Any]] = field(default_factory=list)
    structures: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["WriteOperation", "PersistenceConfig", "WorldStateData", "EntityType", "Operation"]
