## Summary

Cycle 006 closed all five significant gaps from Cycle 005 (SG1–SG5: error message, zombie threshold wiring, fetch timeouts, hardcoded CLI port, expansion never founding settlements). The full review finds no new critical gaps. Two significant gaps and three minor gaps remain.

SG1 is a protocol completeness gap: `WorldStateProtocol` in `src/hamlet/protocols.py` is missing five methods that expansion, simulation, and TUI components call at runtime — `found_village`, `create_structure`, `update_structure`, `get_agents_in_view`, and `get_structures_in_view`. Without these in the protocol, static analysis cannot verify that `RemoteWorldState` and test mocks satisfy the full interface.

SG2 is a behavioral gap introduced by WI-216: `found_village` correctly persists expansion-founded outposts to SQLite and registers them in memory, but does not call `_seed_initial_structures`. Primary villages receive three seeded structures. Expansion outposts receive zero.

Additionally, the code quality review found S1: `process_expansion` runs on every tick with no per-village cooldown — when a village reaches `expansion_threshold` agents, it calls `create_road_between` (N lock acquisitions) and `found_village` on every tick. Road cells are re-inserted into `_state.structures` and re-queued for SQLite on every tick, causing unbounded memory and write queue growth.

## Critical Gaps

None.

## Significant Gaps

### SG1: `WorldStateProtocol` missing five methods consumed by expansion, simulation, and TUI

- **Interview reference**: Guiding principle 4 (Modularity for Iteration): module boundaries must be well-defined.
- **Current state**: `WorldStateProtocol` at `src/hamlet/protocols.py:23-43` declares 14 methods. Five methods present on `WorldStateManager` are absent: `found_village`, `create_structure`, `update_structure`, `get_agents_in_view`, `get_structures_in_view`. Their consumers (`expansion.py`, `structure_updater.py`, `app.py`, `world_view.py`) type `world_state` as `Any` because the protocol omits these methods.
- **Gap**: A future change to `WorldStateManager` that renames or removes one of these five methods will not be caught by static analysis. `RemoteWorldState` cannot be verified as protocol-complete for these operations.
- **Severity**: Significant
- **Recommendation**: Address now — adding the five method signatures to `WorldStateProtocol` is a no-logic change. Enables consumers to type `world_state: WorldStateProtocol` instead of `Any`.

### SG2: `found_village` does not seed initial structures for expansion outposts

- **Interview reference**: "As time goes on, the screen should fill up and the workers should expand outward." Guiding principle 5: villages can found new settlements.
- **Current state**: `WorldStateManager.found_village` creates a `Village`, adds it to `_state.villages`, and queues a persistence write — but does not call `_seed_initial_structures`. `get_or_create_project` (line 226) calls `_seed_initial_structures` outside its lock block, placing `LIBRARY`, `WORKSHOP`, and `FORGE` near the village center. `found_village` does not.
- **Gap**: Expansion-founded outposts are structurally empty. Road segments appear at the site, but no buildings are placed. Agents that migrate into the outpost area have no structures to contribute work units to. The outpost center is not registered in `PositionGrid`.
- **Severity**: Significant
- **Recommendation**: Address now — `found_village` should call `_seed_initial_structures(village)` after its `async with self._lock:` block. Three-line addition; no lock complexity since `_seed_initial_structures` acquires the lock itself.

### SG3: `process_expansion` runs on every tick with no cooldown (from code quality review)

- **Current state**: `ExpansionManager.process_expansion` runs for every village on every simulation tick. The only gate is `check_village_expansion`, which returns a site whenever `len(agents) >= expansion_threshold`. Once a village reaches 20 agents the condition stays true permanently. On every subsequent tick: `create_road_between` calls `create_structure` once per road cell (each acquiring `WorldStateManager._lock`), then `found_village`. `_create_structure_locked` does not deduplicate — it catches `ValueError` from `_grid.occupy()` but still adds the structure to `_state.structures` and queues a DB write. Road cells are re-inserted on every tick.
- **Gap**: Unbounded memory growth in `_state.structures`, unbounded SQLite write queue, lock contention from O(road_length) acquisitions per tick.
- **Severity**: Significant
- **Recommendation**: Add `has_expanded: bool = False` flag to `Village` dataclass. Set it to `True` inside `WorldStateManager.found_village` on the originating village. Check it at the top of the per-village loop in `process_expansion` — skip any village where `village.has_expanded` is True.

## Minor Gaps

### MG1: `expansion.py` `hasattr` guard on `found_village` is a protocol smell

- **Component**: `src/hamlet/simulation/expansion.py:83`
- `if hasattr(world_state, "found_village"):` guard exists because the protocol doesn't declare `found_village`. In tests using `spec=WorldStateProtocol`, the guard fires and outpost creation is silently skipped without a test failure.
- **Recommendation**: Defer until SG1 is fixed — remove the guard in the same work item that adds `found_village` to the protocol.

### MG2: `SimulationConfig.expansion_threshold` and `work_unit_scale` are not user-configurable

- **Component**: `src/hamlet/simulation/config.py`, `src/hamlet/app_factory.py:83`
- `expansion_threshold` (default: 20) and `work_unit_scale` (default: 1.0) are fixed. Users cannot tune simulation pacing. Conflicts with Guiding Principle 4.
- **Recommendation**: Defer — add to `Settings` in a configuration-focused cycle.

### MG3: `tool_output` schema rejects plain-string Bash responses (pre-existing, carried)

- **Component**: `src/hamlet/mcp_server/validation.py:35`
- `tool_output` constrained to `["object", "null"]`. Bash `PostToolUse` with string output rejected; work units never awarded for Bash calls.
- **Recommendation**: Defer — widen to `["object", "string", "null"]` in a dedicated schema cycle.

## No Gaps Found In

- **WI-213**: Error message says `hamlet daemon`; CLI uses `settings.mcp_port`.
- **WI-214**: `zombie_threshold_seconds` in `Settings`, validated, wired to `AgentInferenceEngine`.
- **WI-215**: `fetch_state` and `fetch_events` both apply a 5-second timeout.
- **WI-216 persistence**: Expansion villages added to `_state.villages` and queued for SQLite write. Persistence path correct.
- **Service subcommand**: All six operations implemented. macOS platform guard correct.
- **Daemon port-conflict detection**: Detects conflict before startup, prints clear warning, exits cleanly.
- **Legend and key**: Available via `/` key. Covers agents, structures, materials, states.
- **Deterministic agent color**: Derived from `AgentType` via `TYPE_COLORS`.
- **Event log**: Chronological, scrollable, capped at `Settings.event_log_max_entries`.
- **All 15 hook types**: Registered, scripted, enumerated, routed.
- **Agent despawn**: Wired end-to-end; inference engine triggers after `zombie_despawn_seconds`.
- **Global world map**: All projects share a single `world.db`.
- **Project identity via config file**: `.hamlet/config.json`; `hamlet init` creates it.
