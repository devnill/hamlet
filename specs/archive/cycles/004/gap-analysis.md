## Summary

Four gaps were found in the Cycle 004 implementation (WI-208 through WI-212). Two significant gaps were fixed during this cycle: `PersistenceProtocol` was missing `delete_agent`, and `despawn_agent` did not remove the dead agent ID from `session.agent_ids`. One minor gap was also fixed: `RemoteWorldState` did not implement `despawn_agent`. One minor gap remains deferred: `AgentUpdater` and `AgentInferenceEngine._update_zombie_states` both write `AgentState.ZOMBIE` independently every tick — the `AgentUpdater` branch is now vestigial after WI-211 and produces redundant persistence writes.

The despawn pipeline end-to-end (WorldStateManager → PersistenceFacade → WriteExecutor → SQLite) is functionally complete. The viewer-mode path is correctly structured. Resurrection after despawn works correctly without corrupting zombie TTL state.

## Critical Gaps

None.

## Significant Gaps (fixed during cycle)

### G1: `PersistenceProtocol` missing `delete_agent` — FIXED
`WorldStateManager.despawn_agent` calls `self._persistence.delete_agent(agent_id)` but `PersistenceProtocol` did not declare the method. Fixed: `async def delete_agent(self, agent_id: str) -> None: ...` added to `PersistenceProtocol` in `protocols.py`.

### G2: `despawn_agent` did not remove agent from `session.agent_ids` — FIXED
Stale agent IDs accumulated in `session.agent_ids` after despawn, causing `get_or_create_agent` to accumulate dead IDs and `_handle_stop` to attempt redundant despawns. Fixed: session cleanup added inside the lock in `despawn_agent`. Test added to `test_world_state_manager.py`.

## Minor Gaps

### G3: `RemoteWorldState` lacked `despawn_agent` — FIXED
`WorldStateProtocol` declares `despawn_agent`; `RemoteWorldState` did not implement it. Fixed: no-op `despawn_agent` added to `RemoteWorldState` consistent with `update_viewport_center` (viewer does not control agent lifecycle).

### G4: `AgentUpdater` ZOMBIE branch is vestigial after WI-211
- **Expected**: Zombie state management owned by one component. WI-211 placed the authoritative zombie detection and TTL despawn path in `AgentInferenceEngine._update_zombie_states`.
- **Actual**: `AgentUpdater.update_agents` (`simulation/agent_updater.py`) independently checks `last_seen` against `SimulationConfig.zombie_threshold` and calls `update_agent(state=AgentState.ZOMBIE)` for stale agents on every tick. `AgentInferenceEngine._update_zombie_states` does the same check via `_check_zombie`. Every stale agent gets two redundant ZOMBIE writes per tick. The `AgentUpdater` path does not set `zombie_since` and does not participate in despawn scheduling — it is now fully vestigial.
- **Impact**: Doubled persistence write volume for every stale agent every tick. No correctness failure — writes are idempotent.
- **Suggested fix**: Remove the `AgentState.ZOMBIE` branch from `AgentUpdater.update_agents`. Update `test_agent_updater.py`. Defer to a future refinement cycle.

## No Gaps Found In

- **WI-208 (ZOMBIE on load)**: `load_from_persistence` forces `AgentState.ZOMBIE` for all loaded agents. Docstring explains rationale. Covered by tests.
- **WI-209 (premature resize removed)**: `WorldView.on_mount` no longer calls `self._viewport.resize`. Fix present and correct.
- **WI-210 (despawn infrastructure)**: `despawn_agent` removes from `_state.agents`, grid, `village.agent_ids`, and `session.agent_ids`. `delete_agent` enqueues a parameterised DELETE. SQL path complete and injection-safe.
- **WI-211 (inference engine despawn)**: Session-end despawn, zombie TTL despawn, and startup seeding all present and tested.
- **WI-212 (legend overlay CSS)**: Both `LegendOverlay` and `HelpOverlay` declare `layer: overlay` and `position: absolute`. `HamletApp.LAYERS` declared.
- **`startup()` call placement**: Called only in `build_components` (daemon path). Viewer path correctly omits it — `RemoteWorldState` and the absence of an inference engine in viewer mode make it unnecessary.
- **`zombie_since` on resurrection**: New agents created via resurrection receive new UUIDs; no stale `zombie_since` entries survive. Old entries removed by despawn callers.
- **Settings**: `zombie_despawn_seconds: int = 300` present in `Settings`, passed to `AgentInferenceEngine` in `build_components`.
