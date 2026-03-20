# Review: Work Item 117 — Move TOOL_TO_STRUCTURE to world_state/rules.py

**Verdict: Pass**

The implementation correctly moves `TOOL_TO_STRUCTURE` from `inference/engine.py` to `world_state/rules.py` with no correctness, security, or circular-import issues.

## Critical Findings

None.

## Significant Findings

None.

## Minor Findings

### M1: No test exercises the import path of the moved symbol directly
- **File**: `/Users/dan/code/hamlet/tests/test_type_inference.py:567`
- **Issue**: The existing work-unit tests import `StructureType` directly from `hamlet.world_state.types` and call `engine._handle_post_tool_use`, which exercises `TOOL_TO_STRUCTURE` indirectly through the engine. No test imports `TOOL_TO_STRUCTURE` from `hamlet.world_state.rules` to verify the symbol is publicly accessible at its new location.
- **Suggested fix**: Add a one-line smoke test: `from hamlet.world_state.rules import TOOL_TO_STRUCTURE` inside a `test_tool_to_structure_importable` function to pin the public API location.

## Unmet Acceptance Criteria

None. All five criteria are satisfied:

1. `TOOL_TO_STRUCTURE` is defined in `src/hamlet/world_state/rules.py` at line 8.
2. `TOOL_TO_STRUCTURE` is in `__all__` at `rules.py:6`.
3. `engine.py` imports `TOOL_TO_STRUCTURE` from `hamlet.world_state.rules` at `engine.py:12`.
4. No local definition of `TOOL_TO_STRUCTURE` exists anywhere in `engine.py`.
5. All three values in `TOOL_TO_STRUCTURE` use `world_state.types.StructureType` enum members (`LIBRARY`, `WORKSHOP`, `FORGE`).

## Circular Import Analysis

No cycles introduced. The full chain is:

- `world_state/types.py` — no hamlet imports
- `world_state/rules.py` → `world_state/types.py`
- `world_state/manager.py` → `world_state/rules.py`, `world_state/types.py`, `inference/types.py`
- `inference/types.py` — no hamlet imports
- `inference/engine.py` → `world_state/rules.py`, `world_state/types.py`, `inference/rules.py`, `inference/types.py`

No module imports from a module that imports it back.

## Type Compatibility

`TOOL_TO_STRUCTURE.get(event.tool_name or "")` at `engine.py:268` returns `StructureType | None`, which is passed to `self._world_state.add_work_units(agent_id, structure_type, units)` guarded by a `if structure_type is not None` check at line 269. The type is the same `world_state.types.StructureType` that `add_work_units` already expects. No compatibility issue.
