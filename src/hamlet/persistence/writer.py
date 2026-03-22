"""Write executor — executes batches of WriteOperations against the database."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from hamlet.persistence.types import WriteOperation

if TYPE_CHECKING:
    from hamlet.persistence.connection import DatabaseConnection

logger = logging.getLogger(__name__)

__all__ = ["WriteExecutor"]


class WriteExecutor:
    """Executes batches of write operations in a single atomic transaction."""

    def __init__(self, db: "DatabaseConnection") -> None:
        self._db = db

    async def execute_batch(self, operations: list[WriteOperation]) -> None:
        """Execute all operations in a single transaction. Logs but does not raise on failure."""
        if not operations:
            return
        try:
            await self._db.begin_transaction()
            for op in operations:
                await self._execute_write(op)
            await self._db.commit()
        except Exception:
            try:
                await self._db.rollback()
            except Exception:
                pass
            logger.exception("execute_batch: failed to execute %d operations", len(operations))

    async def _execute_write(self, op: WriteOperation) -> None:
        """Execute a single write operation."""
        if op.operation == "delete":
            await self._delete_entity(op)
            return
        if op.entity_type == "project":
            await self._write_project(op)
        elif op.entity_type == "session":
            await self._write_session(op)
        elif op.entity_type == "agent":
            await self._write_agent(op)
        elif op.entity_type == "structure":
            await self._write_structure(op)
        elif op.entity_type == "village":
            await self._write_village(op)
        elif op.entity_type == "event_log":
            await self._write_event_log(op)
        elif op.entity_type == "world_metadata":
            await self._write_world_metadata(op)
        else:
            logger.warning("_execute_write: unknown entity_type %r", op.entity_type)

    _TABLE_MAP = {
        "project": "projects",
        "session": "sessions",
        "agent": "agents",
        "structure": "structures",
        "village": "villages",
    }

    async def _delete_entity(self, op: WriteOperation) -> None:
        """Execute a DELETE for the given entity by primary key."""
        table = self._TABLE_MAP.get(op.entity_type)
        if table is None:
            logger.warning("_delete_entity: no table mapping for %r", op.entity_type)
            return
        await self._db.execute(f"DELETE FROM {table} WHERE id = ?", (op.entity_id,))

    async def _write_project(self, op: WriteOperation) -> None:
        """Write a project record using INSERT OR REPLACE."""
        d = op.data
        config_json = d.get("config_json")
        if config_json is None:
            config_json = json.dumps(d.get("config", {}))
        elif not isinstance(config_json, str):
            config_json = json.dumps(config_json)
        await self._db.execute(
            "INSERT OR REPLACE INTO projects (id, name, config_json, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                d.get("id"),
                d.get("name"),
                config_json,
                _iso(d.get("created_at")),
                _iso(d.get("updated_at")),
            ),
        )

    async def _write_session(self, op: WriteOperation) -> None:
        """Write a session record using INSERT OR REPLACE."""
        d = op.data
        agent_ids_json = d.get("agent_ids_json")
        if agent_ids_json is None:
            agent_ids_json = json.dumps(d.get("agent_ids", []))
        elif not isinstance(agent_ids_json, str):
            agent_ids_json = json.dumps(agent_ids_json)
        await self._db.execute(
            "INSERT OR REPLACE INTO sessions"
            " (id, project_id, started_at, last_activity, agent_ids_json)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                d.get("id"),
                d.get("project_id"),
                _iso(d.get("started_at")),
                _iso(d.get("last_activity")),
                agent_ids_json,
            ),
        )

    async def _write_agent(self, op: WriteOperation) -> None:
        """Write an agent record using INSERT OR REPLACE."""
        d = op.data
        await self._db.execute(
            "INSERT OR REPLACE INTO agents"
            " (id, session_id, village_id, parent_id, inferred_type, color,"
            "  position_x, position_y, last_seen, state, current_activity,"
            "  total_work_units, created_at, updated_at, project_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                d.get("id"),
                d.get("session_id"),
                d.get("village_id"),
                d.get("parent_id"),
                d.get("inferred_type", "general"),
                d.get("color", "white"),
                d.get("position_x", 0),
                d.get("position_y", 0),
                _iso(d.get("last_seen")),
                d.get("state", "active"),
                d.get("current_activity"),
                d.get("total_work_units", 0),
                _iso(d.get("created_at")),
                _iso(d.get("updated_at")),
                d.get("project_id", ""),
            ),
        )

    async def _write_structure(self, op: WriteOperation) -> None:
        """Write a structure record using INSERT OR REPLACE."""
        d = op.data
        await self._db.execute(
            "INSERT OR REPLACE INTO structures"
            " (id, village_id, type, position_x, position_y, stage, material,"
            "  work_units, work_required, size_tier, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                d.get("id"),
                d.get("village_id"),
                d.get("type"),
                d.get("position_x", 0),
                d.get("position_y", 0),
                d.get("stage", 0),
                d.get("material", "wood"),
                d.get("work_units", 0),
                d.get("work_required", 100),
                d.get("size_tier", 1),
                _iso(d.get("created_at")),
                _iso(d.get("updated_at")),
            ),
        )

    async def _write_village(self, op: WriteOperation) -> None:
        """Write a village record using INSERT OR REPLACE."""
        d = op.data
        await self._db.execute(
            "INSERT OR REPLACE INTO villages"
            " (id, project_id, name, center_x, center_y,"
            "  bounds_min_x, bounds_min_y, bounds_max_x, bounds_max_y,"
            "  has_expanded, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                d.get("id"),
                d.get("project_id"),
                d.get("name"),
                d.get("center_x", 0),
                d.get("center_y", 0),
                d.get("bounds_min_x", 0),
                d.get("bounds_min_y", 0),
                d.get("bounds_max_x", 0),
                d.get("bounds_max_y", 0),
                1 if d.get("has_expanded") else 0,
                _iso(d.get("created_at")),
                _iso(d.get("updated_at")),
            ),
        )

    async def _write_event_log(self, op: WriteOperation) -> None:
        """Append an event_log row (plain INSERT; id is AUTOINCREMENT)."""
        d = op.data
        await self._db.execute(
            "INSERT INTO event_log"
            " (timestamp, session_id, project_id, hook_type, tool_name, summary)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                _iso(d.get("timestamp")) or "",
                d.get("session_id") or "",
                d.get("project_id") or "",
                d.get("hook_type") or "",
                d.get("tool_name"),  # nullable
                d.get("summary") or "",
            ),
        )

    async def _write_world_metadata(self, op: WriteOperation) -> None:
        """Upsert key/value pairs into the world_metadata table."""
        for key, value in op.data.items():
            await self._db.execute(
                "INSERT OR REPLACE INTO world_metadata (key, value) VALUES (?, ?)",
                (key, str(value)),
            )


def _iso(value: object) -> str | None:
    """Return value as an ISO 8601 string if it has an isoformat() method, else str or None."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
