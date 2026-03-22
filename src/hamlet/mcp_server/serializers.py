"""Serializers for world state and events for REST API responses."""
from __future__ import annotations

import datetime
import enum
from typing import Any


def _serialize_value(v: Any) -> Any:
    if isinstance(v, datetime.datetime):
        return v.isoformat()
    if isinstance(v, enum.Enum):
        return v.value
    return v


def _serialize_agent(agent: Any) -> dict:
    return {
        "id": agent.id,
        "session_id": agent.session_id,
        "project_id": agent.project_id,
        "village_id": agent.village_id,
        "inferred_type": agent.inferred_type.value,
        "color": agent.color,
        "position": {"x": agent.position.x, "y": agent.position.y},
        "last_seen": agent.last_seen.isoformat(),
        "state": agent.state.value,
        "parent_id": agent.parent_id,
        "current_activity": agent.current_activity,
        "total_work_units": agent.total_work_units,
        "created_at": agent.created_at.isoformat(),
        "updated_at": agent.updated_at.isoformat(),
    }


def _serialize_structure(structure: Any) -> dict:
    return {
        "id": structure.id,
        "village_id": structure.village_id,
        "type": structure.type.value,
        "position": {"x": structure.position.x, "y": structure.position.y},
        "stage": structure.stage,
        "material": structure.material,
        "work_units": structure.work_units,
        "work_required": structure.work_required,
        "size_tier": structure.size_tier,
        "created_at": structure.created_at.isoformat(),
        "updated_at": structure.updated_at.isoformat(),
    }


def _serialize_village(village: Any) -> dict:
    return {
        "id": village.id,
        "project_id": village.project_id,
        "name": village.name,
        "center": {"x": village.center.x, "y": village.center.y},
        "bounds": {
            "min_x": village.bounds.min_x,
            "min_y": village.bounds.min_y,
            "max_x": village.bounds.max_x,
            "max_y": village.bounds.max_y,
        },
        "structure_ids": village.structure_ids,
        "agent_ids": village.agent_ids,
        "has_expanded": village.has_expanded,
        "created_at": village.created_at.isoformat(),
        "updated_at": village.updated_at.isoformat(),
    }


def _serialize_project(project: Any) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "village_id": project.village_id,
        "config": project.config,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }


def _serialize_event(entry: Any) -> dict:
    return {
        "id": entry.id,
        "timestamp": entry.timestamp.isoformat(),
        "session_id": entry.session_id,
        "project_id": entry.project_id,
        "hook_type": entry.hook_type,
        "tool_name": entry.tool_name,
        "summary": entry.summary,
    }


async def serialize_state(world_state: Any, animation_manager: Any = None) -> dict:
    agents = await world_state.get_all_agents()
    structures = await world_state.get_all_structures()
    villages = await world_state.get_all_villages()
    projects = await world_state.get_projects()

    if animation_manager is not None:
        from hamlet.world_state.types import AgentState
        zombie_ids = {a.id for a in agents if a.state == AgentState.ZOMBIE}
        animation_frames = animation_manager.get_frames(zombie_ids=zombie_ids)
    else:
        animation_frames = {}

    return {
        "agents": [_serialize_agent(a) for a in agents],
        "structures": [_serialize_structure(s) for s in structures],
        "villages": [_serialize_village(v) for v in villages],
        "projects": [_serialize_project(p) for p in projects],
        "animation_frames": animation_frames,
    }


async def serialize_events(world_state: Any) -> dict:
    events = await world_state.get_event_log()
    return {
        "events": [_serialize_event(e) for e in events],
    }
