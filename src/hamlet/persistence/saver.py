"""Entity save operations — converts world state entities to WriteOperations."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from hamlet.persistence.queue import WriteQueue
from hamlet.persistence.types import WriteOperation

if TYPE_CHECKING:
    from hamlet.world_state.types import Agent, Project, Session, Structure, Village

__all__ = ["EntitySaver"]


class EntitySaver:
    """Converts world state entities to WriteOperations and queues them."""

    def __init__(self, queue: WriteQueue) -> None:
        self._queue = queue

    async def save_project(self, project: Project) -> None:
        """Queue a project upsert. Non-blocking."""
        op = WriteOperation(
            entity_type="project",
            entity_id=project.id,
            operation="insert",
            data={
                "id": project.id,
                "name": project.name,
                "config_json": json.dumps(project.config),
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
            },
        )
        await self._queue.put(op)

    async def save_session(self, session: Session) -> None:
        """Queue a session upsert. Non-blocking."""
        op = WriteOperation(
            entity_type="session",
            entity_id=session.id,
            operation="insert",
            data={
                "id": session.id,
                "project_id": session.project_id,
                "started_at": session.started_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "agent_ids_json": json.dumps(session.agent_ids),
            },
        )
        await self._queue.put(op)

    async def save_agent(self, agent: Agent) -> None:
        """Queue an agent upsert. Non-blocking."""
        now = datetime.now(UTC).isoformat()
        op = WriteOperation(
            entity_type="agent",
            entity_id=agent.id,
            operation="insert",
            data={
                "id": agent.id,
                "session_id": agent.session_id,
                "village_id": agent.village_id,
                "parent_id": agent.parent_id,
                "inferred_type": agent.inferred_type.value,
                "color": agent.color,
                "position_x": agent.position.x,
                "position_y": agent.position.y,
                "last_seen": agent.last_seen.isoformat(),
                "state": agent.state.value,
                "current_activity": agent.current_activity,
                "total_work_units": agent.total_work_units,
                "created_at": agent.created_at.isoformat(),
                "updated_at": now,
            },
        )
        await self._queue.put(op)

    async def save_structure(self, structure: Structure) -> None:
        """Queue a structure upsert. Non-blocking."""
        now = datetime.now(UTC).isoformat()
        op = WriteOperation(
            entity_type="structure",
            entity_id=structure.id,
            operation="insert",
            data={
                "id": structure.id,
                "village_id": structure.village_id,
                "type": structure.type.value,
                "position_x": structure.position.x,
                "position_y": structure.position.y,
                "stage": structure.stage,
                "material": structure.material,
                "work_units": structure.work_units,
                "work_required": structure.work_required,
                "created_at": structure.created_at.isoformat(),
                "updated_at": now,
            },
        )
        await self._queue.put(op)

    async def save_village(self, village: Village) -> None:
        """Queue a village upsert. Non-blocking."""
        now = datetime.now(UTC).isoformat()
        op = WriteOperation(
            entity_type="village",
            entity_id=village.id,
            operation="insert",
            data={
                "id": village.id,
                "project_id": village.project_id,
                "name": village.name,
                "center_x": village.center.x,
                "center_y": village.center.y,
                "bounds_min_x": village.bounds.min_x,
                "bounds_min_y": village.bounds.min_y,
                "bounds_max_x": village.bounds.max_x,
                "bounds_max_y": village.bounds.max_y,
                "created_at": village.created_at.isoformat(),
                "updated_at": now,
            },
        )
        await self._queue.put(op)
