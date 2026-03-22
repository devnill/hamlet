# Review: WI-218 — Add five missing methods to WorldStateProtocol

## Verdict: Pass

All critical and significant findings from the previous review have been resolved.

---

## Rework Applied (from Verdict: Fail pass)

**C1 resolved**: `WorldStateProtocol.found_village` in `protocols.py` now declares `originating_village_id: str` as the first positional parameter, matching `WorldStateManager.found_village`.

**C2 resolved**: `RemoteWorldState.found_village` stub in `remote_world_state.py` now declares `originating_village_id: str` as the first positional parameter, matching the protocol and the manager.

**S1 resolved**: The `hasattr(world_state, "create_structure")` guard in `ExpansionManager.create_road_between` has been removed. The method now calls `world_state.create_structure(...)` directly. The stale docstring sentence ("If *world_state* does not expose a `create_structure` method the operation is silently skipped") was also removed. The test `test_create_road_between_skips_without_create_structure` (which encoded the old guard behavior) was deleted.

**S2 resolved**: The `logger.warning(...)` call in the `create_structure` stub was removed. The stub now raises `NotImplementedError` cleanly, consistent with the `found_village`, `get_or_create_project`, and `get_or_create_session` stubs.

**M1 resolved**: `create_structure` stub now uses `structure_type: StructureType` and `position: Position` type annotations instead of `Any`.

---

## Acceptance Criteria

- [x] **AC1**: `WorldStateProtocol` declares `found_village` with correct 4-param signature — met
- [x] **AC2**: `WorldStateProtocol` declares `create_structure`, `update_structure`, `get_agents_in_view`, `get_structures_in_view` — met
- [x] **AC3**: `RemoteWorldState` stubs added for all five methods with correct signatures — met
- [x] **AC4**: `hasattr` guard removed from `create_road_between`; direct call in place — met
- [x] **AC5**: Existing `get_agents_in_view` and `get_structures_in_view` in `RemoteWorldState` match protocol — met
