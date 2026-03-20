# Policies: Data Model

## P-1: Single Source of Truth
World State module owns all entity data. All reads go through World State. No duplicate state.

- **Derived from:** Architecture decision
- **Established:** planning phase
- **Status:** active

## P-2: Project-Based Villages
Each project (codebase) maps to exactly one village. Multiple projects create multiple villages on a shared world map.

- **Derived from:** GP-5 (Persistent World)
- **Established:** planning phase
- **Status:** active

## P-3: Position Uniqueness
No two entities can occupy the same world position. Position assignment uses spiral search from parent or village center.

- **Derived from:** GP-9 (Parent-Child Spatial Relationships)
- **Established:** planning phase
- **Status:** active

## P-4: Inferred Agent Lifecycle
Claude Code doesn't expose agent hooks. Spawning, completion, and relationships are inferred from PreToolUse/PostToolUse patterns.

- **Derived from:** Constraints
- **Established:** planning phase
- **Status:** active

## P-5: Project entity must exist before dependent records
Before creating sessions or agents for a project, `get_or_create_project` must be called to ensure a `Project` record exists. This prevents orphan villages, broken village-per-project mapping, and agent position loss on restart.

- **Derived from:** D-4, archive/cycles/003/code-quality.md (S5), archive/cycles/003/gap-analysis.md (G2)
- **Established:** cycle 003
- **Status:** active

## P-6: Villages must have initial structures on creation
When a village is founded, it must be seeded with at least one structure of each primary type (LIBRARY, WORKSHOP, FORGE) so that work units from tool calls have valid targets. Without initial structures, `add_work_units()` silently drops all incoming work.

- **Derived from:** D-5, archive/cycles/003/gap-analysis.md (G1)
- **Established:** cycle 003
- **Status:** active

## P-7: _seed_initial_structures must be called outside asyncio.Lock
Any code path that calls `_seed_initial_structures` must first release `self._lock`. asyncio locks are not reentrant; `_seed_initial_structures` internally acquires the lock via `create_structure`, so calling it while holding the lock causes deadlock.

- **Derived from:** D-8, archive/cycles/004/decision-log.md (D9), archive/cycles/004/code-quality.md (cross-cutting #5)
- **Established:** cycle 004
- **Status:** active

## P-8: active_tools decrement must be tied to successful pending_tools eviction
`SessionState.active_tools` may only be decremented when a corresponding `pending_tools` entry is found and removed — either by PostToolUse correlation or by TTL eviction in `_update_zombie_states`. Unconditional decrement causes negative counters and spurious agent spawns.

- **Derived from:** D-9, archive/cycles/004/decision-log.md (D7, D8), archive/cycles/004/code-quality.md (cross-cutting #6)
- **Established:** cycle 004
- **Status:** active
