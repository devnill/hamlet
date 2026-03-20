from __future__ import annotations

import logging
from hamlet.persistence.connection import DatabaseConnection
from hamlet.world_state.state import EventLogEntry

logger = logging.getLogger(__name__)

__all__ = ["EventLogManager"]


class EventLogManager:
    def __init__(self, db: DatabaseConnection, max_entries: int = 10000) -> None:
        self.db = db
        self.max_entries = max_entries

    async def append(self, entry: EventLogEntry) -> None:
        """Insert an event log entry and prune old entries beyond max_entries.

        Both the INSERT and the pruning DELETE run in a single transaction so
        the table never exceeds max_entries rows and a mid-operation crash does
        not leave a partially-pruned state.
        """
        timestamp_str = entry.timestamp.isoformat()
        try:
            await self.db.begin_transaction()
            await self.db.execute(
                "INSERT INTO event_log (timestamp, session_id, project_id, hook_type, tool_name, summary) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    timestamp_str,
                    entry.session_id,
                    entry.project_id,
                    entry.hook_type,
                    entry.tool_name,
                    entry.summary,
                ),
            )
            await self.db.execute(
                "DELETE FROM event_log WHERE id < (SELECT id FROM event_log ORDER BY id DESC LIMIT 1 OFFSET ?)",
                (self.max_entries - 1,),
            )
            await self.db.commit()
        except Exception:
            try:
                await self.db.rollback()
            except Exception:
                pass
            logger.exception(
                "Failed to append event log entry (session=%s hook=%s)",
                entry.session_id,
                entry.hook_type,
            )
