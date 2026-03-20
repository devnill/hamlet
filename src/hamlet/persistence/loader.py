"""State loading — reads all tables from the database and returns WorldStateData."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from hamlet.persistence.types import WorldStateData

if TYPE_CHECKING:
    from hamlet.persistence.connection import DatabaseConnection

__all__ = ["StateLoader"]

log = logging.getLogger(__name__)


def _parse_dt(value) -> datetime:
    """Convert a DB timestamp value (ISO string or datetime) to a timezone-aware datetime.

    If the value is None, returns the current UTC time so that callers always
    receive a valid datetime and zombie/idle detection can safely perform
    arithmetic without an additional None-check.
    """
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class StateLoader:
    """Loads world state from the database on startup."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    async def load_state(self) -> WorldStateData:
        """Load all entities from the database and return a WorldStateData instance.

        Each table query is wrapped in its own try/except so that a missing or
        unreadable table degrades gracefully rather than aborting the whole load
        (GP-7: graceful degradation).
        """
        projects = await self._load_projects()
        sessions = await self._load_sessions()
        villages = await self._load_villages()
        agents = await self._load_agents()
        structures = await self._load_structures()
        metadata = await self._load_metadata()

        return WorldStateData(
            projects=projects,
            sessions=sessions,
            villages=villages,
            agents=agents,
            structures=structures,
            metadata=metadata,
        )

    async def _load_projects(self) -> list[dict]:
        try:
            await self._db.execute(
                "SELECT id, name, config_json, created_at, updated_at FROM projects"
            )
            rows = await self._db.fetchall()
        except Exception as exc:
            log.warning("Failed to load projects table: %s", exc)
            return []

        result: list[dict] = []
        for row in rows:
            d = dict(zip(["id", "name", "config_json", "created_at", "updated_at"], row))
            # Parse config_json: JSON string → dict
            raw = d.get("config_json")
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                    d["config_json"] = parsed if isinstance(parsed, dict) else {}
                except json.JSONDecodeError:
                    log.warning("Could not parse config_json for project %s", d.get("id"))
                    d["config_json"] = {}
            elif raw is None:
                d["config_json"] = {}
            d["created_at"] = _parse_dt(d.get("created_at"))
            d["updated_at"] = _parse_dt(d.get("updated_at"))
            result.append(d)
        return result

    async def _load_sessions(self) -> list[dict]:
        try:
            await self._db.execute(
                "SELECT id, project_id, started_at, last_activity, agent_ids_json FROM sessions"
            )
            rows = await self._db.fetchall()
        except Exception as exc:
            log.warning("Failed to load sessions table: %s", exc)
            return []

        result: list[dict] = []
        for row in rows:
            d = dict(zip(["id", "project_id", "started_at", "last_activity", "agent_ids_json"], row))
            # Parse agent_ids_json: JSON string → list
            raw = d.get("agent_ids_json")
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                    d["agent_ids_json"] = parsed if isinstance(parsed, list) else []
                except json.JSONDecodeError:
                    log.warning("Could not parse agent_ids_json for session %s", d.get("id"))
                    d["agent_ids_json"] = []
            else:
                d["agent_ids_json"] = []
            d["started_at"] = _parse_dt(d.get("started_at"))
            d["last_activity"] = _parse_dt(d.get("last_activity"))
            result.append(d)
        return result

    async def _load_villages(self) -> list[dict]:
        cols = [
            "id", "project_id", "name",
            "center_x", "center_y",
            "bounds_min_x", "bounds_min_y", "bounds_max_x", "bounds_max_y",
            "created_at", "updated_at",
        ]
        try:
            await self._db.execute(
                "SELECT id, project_id, name, center_x, center_y,"
                " bounds_min_x, bounds_min_y, bounds_max_x, bounds_max_y,"
                " created_at, updated_at FROM villages"
            )
            rows = await self._db.fetchall()
        except Exception as exc:
            log.warning("Failed to load villages table: %s", exc)
            return []

        result: list[dict] = []
        for row in rows:
            d = dict(zip(cols, row))
            d["created_at"] = _parse_dt(d.get("created_at"))
            d["updated_at"] = _parse_dt(d.get("updated_at"))
            result.append(d)
        return result

    async def _load_agents(self) -> list[dict]:
        cols = [
            "id", "session_id", "village_id", "parent_id",
            "inferred_type", "color",
            "position_x", "position_y",
            "last_seen", "state", "current_activity",
            "total_work_units", "created_at", "updated_at",
            "project_id",
        ]
        try:
            await self._db.execute(
                "SELECT id, session_id, village_id, parent_id,"
                " inferred_type, color, position_x, position_y,"
                " last_seen, state, current_activity,"
                " total_work_units, created_at, updated_at, project_id FROM agents"
            )
            rows = await self._db.fetchall()
        except Exception as exc:
            log.warning("Failed to load agents table: %s", exc)
            return []

        result: list[dict] = []
        for row in rows:
            d = dict(zip(cols, row))
            d["last_seen"] = _parse_dt(d.get("last_seen"))
            d["created_at"] = _parse_dt(d.get("created_at"))
            d["updated_at"] = _parse_dt(d.get("updated_at"))
            result.append(d)
        return result

    async def _load_structures(self) -> list[dict]:
        cols = [
            "id", "village_id", "type",
            "position_x", "position_y",
            "stage", "material", "work_units", "work_required",
            "created_at", "updated_at",
        ]
        try:
            await self._db.execute(
                "SELECT id, village_id, type, position_x, position_y,"
                " stage, material, work_units, work_required,"
                " created_at, updated_at FROM structures"
            )
            rows = await self._db.fetchall()
        except Exception as exc:
            log.warning("Failed to load structures table: %s", exc)
            return []

        result: list[dict] = []
        for row in rows:
            d = dict(zip(cols, row))
            d["created_at"] = _parse_dt(d.get("created_at"))
            d["updated_at"] = _parse_dt(d.get("updated_at"))
            result.append(d)
        return result

    async def _load_metadata(self) -> dict:
        try:
            await self._db.execute("SELECT key, value FROM world_metadata")
            rows = await self._db.fetchall()
        except Exception as exc:
            log.warning("Failed to load world_metadata table: %s", exc)
            return {}

        return {row[0]: row[1] for row in rows}
