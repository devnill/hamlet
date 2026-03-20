# Questions: Data Model

## Q-1: Agent Type Inference Accuracy
- **Question:** How accurate must type inference be? Current heuristics use 60% threshold for tool frequency.
- **Source:** plan/modules/agent-inference.md
- **Impact:** Affects color assignment. Low accuracy causes wrong colors; high accuracy requires complex logic.
- **Status:** open
- **Reexamination trigger:** User confusion about agent colors.

## Q-2: Event Log Retention
- **Question:** How many events to retain in SQLite? Current design caps at 10,000.
- **Source:** plan/modules/persistence.md
- **Impact:** Affects long-running session memory. Higher retention uses more disk.
- **Status:** open
- **Reexamination trigger:** Users need historical analysis.

## Q-3: Migration 2 BEGIN/COMMIT — retain or remove?
- **Question:** WI-109 added explicit `BEGIN;`/`COMMIT;` to migration 2 for atomicity. Code review notes `executescript` issues an implicit COMMIT before running, making these redundant and potentially conflicting on some SQLite versions. Should the explicit transaction markers be retained or removed?
- **Source:** archive/cycles/003/code-quality.md (M4); archive/cycles/003/decision-log.md (D59)
- **Impact:** Technical contradiction. Retaining may cause unexpected behavior on some SQLite versions; removing may leave interrupted migrations in an inconsistent state.
- **Status:** open
- **Reexamination trigger:** SQLite version upgrade, migration failure report, or next persistence work item.

## Q-4: InternalEvent missing notification_message and stop_reason typed fields
- **Question:** `InternalEvent` has no `notification_message` or `stop_reason` fields. `event_processor.py` does not extract them. `_handle_notification()` is a no-op. Should `notification_message: str | None` and `stop_reason: str | None` be added to `InternalEvent` with corresponding `raw.get()` calls in `event_processor.py`?
- **Source:** archive/cycles/004/gap-analysis.md (IR1); archive/cycles/004/decision-log.md (OQ4)
- **Impact:** Notification and Stop hooks fire correctly but their semantic content is inaccessible through the typed event model. The interview requirement "every single hook to be implemented" is only half-met for these two hook types.
- **Status:** resolved
- **Resolution:** Both `notification_message: str | None` and `stop_reason: str | None` added to `InternalEvent`. `event_processor.py` populates them via `raw.get()`. Extraction complete; consumption remains deferred (see architecture Q-11 and Q-12).
- **Resolved in:** cycle 005

## Q-5: Undocumented asyncio scheduling assumption in _seed_initial_structures
- **Question:** `_seed_initial_structures` calls `self._grid.is_occupied(pos)` without holding the lock, then calls `create_structure` which acquires the lock. No `await` exists between check and lock acquisition, so in asyncio single-threaded scheduling no race can occur. Should this assumption be documented with a comment, or should the code be restructured to check-and-occupy atomically?
- **Source:** archive/cycles/004/code-quality.md (M2); archive/cycles/004/decision-log.md (OQ8)
- **Impact:** Latent race if an `await` is ever introduced on the check-then-act path.
- **Status:** open
- **Reexamination trigger:** Any modification to the _seed_initial_structures code path.
