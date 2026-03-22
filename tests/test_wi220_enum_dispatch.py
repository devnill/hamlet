from __future__ import annotations
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from hamlet.event_processing.internal_event import HookType, InternalEvent
from hamlet.world_state.manager import WorldStateManager

def _make_minimal_event(hook_type):
    return InternalEvent(
        id=str(uuid.uuid4()),
        sequence=1,
        received_at=datetime.now(UTC),
        session_id="session-smoke",
        project_id="proj-smoke",
        project_name="Smoke Project",
        hook_type=hook_type,
    )

@pytest.fixture
def world_state_manager():
    p = MagicMock()
    p.queue_write = AsyncMock()
    p.load_state = AsyncMock()
    return WorldStateManager(p)

@pytest.mark.parametrize("hook_type", list(HookType))
async def test_handle_event_all_hook_types(hook_type, world_state_manager):
    event = _make_minimal_event(hook_type)
    await world_state_manager.handle_event(event)

def test_hook_type_count():
    assert len(list(HookType)) == 15
