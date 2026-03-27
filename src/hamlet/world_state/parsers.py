"""world_state.parsers — public deserialization helpers for world-state dicts.

These functions convert raw JSON-decoded dicts (from the daemon HTTP API) into
typed dataclasses.  They are intentionally free of side-effects and suitable
for use in both the async TUI path and the synchronous Kitty GUI path.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from hamlet.world_state.state import EventLogEntry
from hamlet.world_state.types import (
    Agent,
    AgentState,
    AgentType,
    Bounds,
    Position,
    Project,
    Structure,
    StructureType,
    Village,
)

__all__ = [
    "try_parse",
    "parse_datetime",
    "parse_position",
    "parse_bounds",
    "parse_agent",
    "parse_structure",
    "parse_village",
    "parse_project",
    "parse_event_log_entry",
]


def try_parse(fn, d):
    """Call fn(d), returning None on any exception (graceful degradation, GP-7)."""
    try:
        return fn(d)
    except Exception:
        return None


def parse_datetime(value: Any) -> datetime:
    """Parse an ISO timestamp string to a timezone-aware datetime, or return now."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            pass
    return datetime.now(UTC)


def parse_position(value: Any) -> Position:
    """Parse a position dict {"x": int, "y": int} to a Position."""
    if isinstance(value, dict):
        return Position(x=int(value.get("x", 0)), y=int(value.get("y", 0)))
    return Position(x=0, y=0)


def parse_bounds(value: Any) -> Bounds:
    """Parse a bounds dict to a Bounds object."""
    if isinstance(value, dict):
        return Bounds(
            min_x=int(value.get("min_x", 0)),
            min_y=int(value.get("min_y", 0)),
            max_x=int(value.get("max_x", 0)),
            max_y=int(value.get("max_y", 0)),
        )
    return Bounds(min_x=0, min_y=0, max_x=0, max_y=0)


def parse_agent(d: dict) -> Agent:
    """Deserialize a dict to an Agent dataclass."""
    return Agent(
        id=d.get("id", ""),
        session_id=d.get("session_id", ""),
        project_id=d.get("project_id", ""),
        village_id=d.get("village_id", ""),
        inferred_type=AgentType(d.get("inferred_type", "general")),
        color=d.get("color", "white"),
        position=parse_position(d.get("position", {})),
        last_seen=parse_datetime(d.get("last_seen")),
        state=AgentState(d.get("state", "active")),
        parent_id=d.get("parent_id"),
        current_activity=d.get("current_activity"),
        total_work_units=int(d.get("total_work_units", 0)),
        created_at=parse_datetime(d.get("created_at")),
        updated_at=parse_datetime(d.get("updated_at")),
    )


def parse_structure(d: dict) -> Structure:
    """Deserialize a dict to a Structure dataclass."""
    return Structure(
        id=d.get("id", ""),
        village_id=d.get("village_id", ""),
        type=StructureType(d.get("type", "house")),
        position=parse_position(d.get("position", {})),
        stage=int(d.get("stage", 0)),
        material=d.get("material", "wood"),
        work_units=int(d.get("work_units", 0)),
        work_required=int(d.get("work_required", 100)),
        size_tier=int(d.get("size_tier", 1)),
        created_at=parse_datetime(d.get("created_at")),
        updated_at=parse_datetime(d.get("updated_at")),
    )


def parse_village(d: dict) -> Village:
    """Deserialize a dict to a Village dataclass."""
    return Village(
        id=d.get("id", ""),
        project_id=d.get("project_id", ""),
        name=d.get("name", ""),
        center=parse_position(d.get("center", {})),
        bounds=parse_bounds(d.get("bounds", {})),
        structure_ids=list(d.get("structure_ids", [])),
        agent_ids=list(d.get("agent_ids", [])),
        has_expanded=bool(d.get("has_expanded", False)),
        created_at=parse_datetime(d.get("created_at")),
        updated_at=parse_datetime(d.get("updated_at")),
    )


def parse_project(d: dict) -> Project:
    """Deserialize a dict to a Project dataclass."""
    return Project(
        id=d.get("id", ""),
        name=d.get("name", ""),
        village_id=d.get("village_id", ""),
        config=dict(d.get("config", {})),
        created_at=parse_datetime(d.get("created_at")),
        updated_at=parse_datetime(d.get("updated_at")),
    )


def parse_event_log_entry(d: dict) -> EventLogEntry:
    """Deserialize a dict to an EventLogEntry dataclass."""
    return EventLogEntry(
        id=d.get("id", ""),
        timestamp=parse_datetime(d.get("timestamp")),
        session_id=d.get("session_id", ""),
        project_id=d.get("project_id", ""),
        hook_type=d.get("hook_type", ""),
        tool_name=d.get("tool_name"),
        summary=d.get("summary", ""),
    )
