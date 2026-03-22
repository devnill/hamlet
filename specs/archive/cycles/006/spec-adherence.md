# Spec Adherence Review — Cycle 6 (Full Review)

Work items in scope: WI-213, WI-214, WI-215, WI-216.
Cross-cutting review covers architecture, all guiding principles, and constraints.

---

## Architecture Deviations

### D1: `SimulationConfig.zombie_threshold` is a dead field not wired to any live logic

- **Expected**: The architecture simulation-tick diagram states "If delta > ZOMBIE_THRESHOLD: mark as zombie". `SimulationConfig` carries `zombie_threshold: float = 300.0`, implying the simulation drives zombie transitions.
- **Actual**: Zombie transitions are entirely owned by `AgentInferenceEngine._zombie_threshold_seconds`, wired from `Settings.zombie_threshold_seconds` via `app_factory.py:77`. `AgentUpdater.update_agents` explicitly skips ZOMBIE agents. `SimulationConfig.zombie_threshold` is never read by any runtime code path.
- **Evidence**: `src/hamlet/simulation/config.py:15` — field declared but never consumed.

### D2: `WorldStateProtocol` does not declare `found_village`

- **Expected**: `WorldStateProtocol` is the interface boundary between the simulation module and world state. WI-216 adds `found_village` to `WorldStateManager` and `ExpansionManager.process_expansion` calls it across this boundary.
- **Actual**: `WorldStateProtocol` at `src/hamlet/protocols.py:23-43` does not include `found_village`. `ExpansionManager.process_expansion` uses a `hasattr` duck-type guard rather than the protocol interface.
- **Evidence**: `src/hamlet/protocols.py:23-43` — method absent. `src/hamlet/simulation/expansion.py:83` — `if hasattr(world_state, "found_village"):`.

---

## Unmet Acceptance Criteria

### Work Item 215: Add request timeout to RemoteStateProvider fetch methods

- [ ] AC3: "A test verifies that a timeout on `fetch_state` raises `aiohttp.ServerTimeoutError` (or equivalent) rather than hanging" — the test at `tests/test_remote_state.py:55-66` injects `asyncio.TimeoutError` as a mock side-effect and accepts either `asyncio.TimeoutError` or `aiohttp.ServerTimeoutError` in a broad `pytest.raises` union. It does not verify that aiohttp's `ClientTimeout` mechanism produces `ServerTimeoutError`. (Carried from incremental review 215.)

### Work Item 216: Village expansion founds new settlements

- [ ] AC4: "A second expansion check does not create a duplicate settlement at the same site (idempotency)" — the 5-cell proximity guard inside `WorldStateManager.found_village` at `src/hamlet/world_state/manager.py:893-900` has no direct unit test. The test suite only exercises the outer 15-cell `_is_clear_site` path. (Carried from incremental review 216, S1.)

---

## Principle Violations

None.

---

## Principle Adherence Evidence

- **Principle 1 — Visual Interest Over Accuracy**: `WorldView._update_animation_frame` runs at 4 Hz, cycling `SPIN_SYMBOLS`. Structure stage progression produces visible symbol transitions. Animation is decoupled from event arrival rate.

- **Principle 2 — Lean Client, Heavy Server**: All hook scripts delegate to `hamlet_hook_utils.py`. No business logic or state in hook scripts. Utility is stdlib-only.

- **Principle 3 — Thematic Consistency**: `AGENT_SYMBOL = "@"`. Structure symbols use box-drawing characters. Stage symbols use block-fill characters. Zombie agents render as green. Consistent with roguelike conventions.

- **Principle 4 — Modularity for Iteration**: `TOOL_TO_STRUCTURE` and `STRUCTURE_RULES` are data-driven dicts in `src/hamlet/world_state/rules.py`. Swapping mappings requires editing one file.

- **Principle 5 — Persistent World, Project-Based Villages**: SQLite schema persists all entity types. `WorldStateManager.load_from_persistence` restores all on startup. WI-216 adds `found_village`, enabling new settlements. Road-building via Bresenham's algorithm connects villages. "Found new settlements" clause now implemented. Remaining gap: `WorldStateProtocol` does not declare `found_village` (D2); idempotency guard at `found_village` level not unit-tested (AC4 above).

- **Principle 6 — Deterministic Agent Identity**: Color derived from `TYPE_COLORS` keyed by `AgentType`, not randomly assigned. Zombie overrides to green deterministically in `get_agent_color`.

- **Principle 7 — Graceful Degradation**: Hook scripts use `sys.exit(0)` in `finally`. `StateLoader.load_state` wraps each query in `try/except`. `RemoteStateProvider.check_health` returns `False` on any exception. `_run_viewer` prints human-readable guidance and exits cleanly when daemon unreachable. `shutdown_components` wraps each stop in `try/except`.

- **Principle 8 — Agent-Driven World Building**: `AgentInferenceEngine` maps `PostToolUse` tool names via `TOOL_TO_STRUCTURE` and calls `world_state.add_work_units`. `StructureUpdater.update_structures` advances stage at thresholds from `STRUCTURE_RULES`. Material transitions wood→stone→brick at stages 2 and 3. Village expansion fires at `expansion_threshold` agents.

- **Principle 9 — Parent-Child Spatial Relationships**: `WorldStateManager.get_or_create_agent` places new agents near parent using nearest-empty-cell search. `AgentInferenceEngine` passes `parent_id` when spawning sub-agents.

- **Principle 10 — Scrollable World, Visible Agents**: `ViewportManager` provides world/screen coordinate translation. `HamletApp` binds `h/j/k/l` and arrow keys to pan. `WorldView.on_resize` updates viewport on terminal resize.

- **Principle 11 — Low-Friction Setup**: WI-213 error message reads "Start the daemon first with: hamlet daemon". `_view_command` and `main()` no-subcommand branch load `Settings.mcp_port` dynamically. Port conflict detection in `daemon_command` gives actionable guidance.

---

## Naming/Pattern Inconsistencies

### N1: `SimulationConfig.zombie_threshold` vs `Settings.zombie_threshold_seconds` — mismatched name and type

- `SimulationConfig.zombie_threshold: float = 300.0` vs canonical `zombie_threshold_seconds: int`. The dead field (D1) uses different name and type. No behavioural impact but misleads readers.

### N2: `@pytest.mark.asyncio` decorators in `test_expansion.py` — verify removal

- `CLAUDE.md`: `asyncio_mode = "auto"` — do not add `@pytest.mark.asyncio` decorators. Rework for WI-216 M1 was supposed to remove these; verify they are absent from `test_expansion.py`.

---

## Summary

WI-213 and WI-214 fully satisfied. WI-215 has one unmet criterion (AC3). WI-216 has one unmet criterion (AC4). Two architecture deviations (dead SimulationConfig field, missing protocol method). **No guiding principle violations.** Two naming/pattern inconsistencies noted.
