# Decisions: Data Model

## D-1: SQLite for Persistence
- **Decision:** Store world state in SQLite database at `~/.hamlet/world.db`.
- **Rationale:** Simple, reliable, supports concurrent reads, built into Python.
- **Source:** steering/interview.md
- **Status:** settled

## D-2: Entity Relationships
- **Decision:** Project (1) : Village (1) : Agents (N). Session (N) : Project (1) : Agents (N). Structures belong to Villages.
- **Rationale:** Mirrors conceptual model: projects are villages, sessions are work periods, agents are workers.
- **Source:** plan/architecture.md
- **Status:** settled

## D-3: Agent Inference from Tool Patterns
- **Decision:** Detect agent spawns by analyzing concurrent PreToolUse/PostToolUse pairs. Infer type from tool frequency sliding window.
- **Rationale:** Claude Code exposes no agent hooks. Must use heuristics.
- **Assumes:** Pattern matching accuracy acceptable for MVP.
- **Source:** plan/modules/agent-inference.md
- **Status:** settled

## D-4: Project entity must be created before session and agent
- **Decision:** `_handle_pre_tool_use` must call `get_or_create_project(event.project_id, event.project_name)` before `get_or_create_session` and `get_or_create_agent`. Without this, sessions reference a non-existent project, villages are created as orphan placeholders, and agents lose their village assignment on restart.
- **Rationale:** SQLite `sessions` table has `project_id NOT NULL REFERENCES projects(id)`. FK enforcement is off, so inserts succeed but in-memory state has no `Project` record. After restart, `projects.get(project_id)` returns `None` and agents fall to position (0,0).
- **Source:** archive/cycles/003/code-quality.md (S5); archive/cycles/003/gap-analysis.md (G2)
- **Policy:** P-5
- **Status:** settled

## D-5: Villages must be seeded with initial structures on creation
- **Decision:** When a village is founded (via `get_or_create_village` or first agent placement), initial structures (LIBRARY, WORKSHOP, FORGE) must be created at positions near the village center. Without initial structures, `add_work_units()` silently drops all work units because no structure of the required type exists.
- **Rationale:** `add_work_units()` finds the nearest structure of the given type and returns silently when none exists. `create_structure` is only called from road-building expansion logic, which triggers only after agent count exceeds `expansion_threshold`. On a fresh world, all work units are dropped.
- **Source:** archive/cycles/003/gap-analysis.md (G1)
- **Policy:** P-6
- **Status:** settled

## D-6: active_tools counter must be decremented on PostToolUse
- **Decision:** `SessionState.active_tools` must be decremented in `_handle_post_tool_use` by correlating the event back to `pending_tools` (using `event.id` as key). The decrement must be guarded with `max(0, ...)`. `pending_tools` entries must be evicted after correlation.
- **Rationale:** Without decrement, `active_tools` is permanently >= 1 after the first tool call. Every subsequent PreToolUse passes the `session.active_tools > 0` spawn check, causing a single sequential session to spawn N agents for N tools. `pending_tools` grows without bound.
- **Source:** archive/cycles/003/code-quality.md (S2)
- **Status:** settled

## D-7: Migration 2 BEGIN/COMMIT retained despite executescript redundancy
- **Decision:** Explicit `BEGIN;`/`COMMIT;` were added to migration 2's SQL string for atomicity on interrupted migrations. Code review notes these are redundant inside `executescript` (which issues an implicit COMMIT before running) and may cause unexpected behavior on some SQLite versions.
- **Rationale:** WI-109 rework prioritized atomicity for interrupted migrations. The redundancy was acknowledged but not resolved.
- **Source:** archive/cycles/003/decision-log.md (D59); archive/cycles/003/code-quality.md (M4)
- **Status:** provisional
- **Note:** Technical contradiction. See Q-3.

## D-8: _seed_initial_structures must be called outside asyncio.Lock
- **Decision:** Both `get_or_create_project` and `get_or_create_agent` must release `self._lock` before calling `_seed_initial_structures`. asyncio locks are not reentrant; calling `_seed_initial_structures` (which internally acquires the lock via `create_structure`) while holding the lock causes deadlock.
- **Rationale:** Inside-lock call caused deadlock in practice. Restructured both code paths to exit the lock block before the seeding call.
- **Source:** archive/cycles/004/decision-log.md (D9); archive/cycles/004/code-quality.md (cross-cutting #5)
- **Policy:** P-7
- **Status:** settled

## D-9: active_tools decrement tied to successful pending_tools eviction
- **Decision:** `active_tools` is decremented only when a matching `pending_tools` entry is found and evicted. This prevents the counter going negative on out-of-order or already-evicted events. TTL eviction in `_update_zombie_states` also decrements for stale entries.
- **Rationale:** Decrementing without matching eviction allowed the counter to go negative or double-decrement.
- **Source:** archive/cycles/004/decision-log.md (D7, D8); archive/cycles/004/code-quality.md (cross-cutting #6)
- **Policy:** P-8
- **Status:** settled

## D-10: TTL eviction added for stale pending_tools entries
- **Decision:** `_update_zombie_states` evicts `pending_tools` entries older than TTL and decrements `active_tools` for each. Without eviction, `pending_tools` grew without bound and `active_tools` never returned to zero when PostToolUse events were lost.
- **Rationale:** Hook scripts fire-and-forget with no retry. Lost PostToolUse events leave pending_tools entries permanently, inflating active_tools.
- **Source:** archive/cycles/004/decision-log.md (D8)
- **Status:** settled

## D-11: Agent dataclass has no name field — TeammateIdle cannot resolve agents by name
- **Decision:** The TeammateIdle daemon handler cannot look up agents by teammate name because the `Agent` dataclass has no `name` field and no name-to-agent_id index exists. The handler is log-only with no state mutation.
- **Rationale:** No stored mapping from teammate name to Agent entity exists. Adding one requires extending the data model.
- **Source:** archive/cycles/008/decision-log.md (decision 4)
- **Status:** settled

## D-12: min_village_distance promoted from class constant to Settings field
- **Decision:** `MIN_VILLAGE_DISTANCE = 15` moved from a `WorldStateManager` class constant to `Settings.min_village_distance: int = 15`. The value is wired through `app_factory.py` at startup. Default behavior is unchanged.
- **Rationale:** Village spacing is a tunable world-generation parameter. Keeping it as a class constant prevented users from adjusting it without code changes. The Settings/config pattern is the established mechanism for user-tunable parameters.
- **Source:** archive/cycles/014/decision-log.md (D1)
- **Status:** settled
