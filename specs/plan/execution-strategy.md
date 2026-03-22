# Execution Strategy — refine-13: Village Name + Multi-Cell Structures + Maintenance

## Mode
Batched parallel — three phases. Maintenance items and feature data-model are independent.
Feature logic and rendering depend on data model.

## Parallelism
- Max concurrent agents: 4 (phase 1)
- Max concurrent agents: 4 (phase 2)
- Max concurrent agents: 2 (phase 3)

## Worktree configuration
- Isolation: worktree recommended for phase 1 (4 parallel agents)

## Review cadence
- Incremental review after each work item completes
- Capstone review after WI-230 (multi-cell rendering, last feature work item)

## Work item groups

### Phase 1 (parallel — no dependencies)
| ID | Title | Complexity | Key files |
|----|-------|------------|-----------|
| WI-220 | Fix handle_event enum dispatch | low | world_state/manager.py |
| WI-221 | Fix Bash string tool_output in schema + processor | low | mcp_server/validation.py, event_processing/event_processor.py |
| WI-222 | stop_reason behavioral differentiation | low | inference/engine.py |
| WI-223 | Event pipeline test coverage | medium | tests/test_event_processor.py, tests/test_world_state_manager.py |
| WI-224 | TUI/persistence test coverage | medium | tests/test_tui_world_view.py, tests/test_tui_app.py, tests/test_persistence_facade.py, tests/test_cli_install.py |
| WI-225 | get_nearest_village_to() method | low | world_state/manager.py, protocols.py, tui/remote_world_state.py |
| WI-227 | Structure size_tier data model + persistence | medium | world_state/types.py, persistence/migrations.py, persistence/loader.py, persistence/writer.py, mcp_server/serializers.py |

### Phase 2 (after phase 1 completes)
| ID | Title | Complexity | Key files |
|----|-------|------------|-----------|
| WI-226 | StatusBar village name from viewport center | low | tui/status_bar.py |
| WI-228 | Size tier calculation in StructureUpdater | medium | simulation/structure_updater.py, simulation/config.py, world_state/rules.py |
| WI-229 | Multi-cell footprint + agent displacement | medium | world_state/grid.py, world_state/manager.py |
| WI-231 | RemoteWorldState size_tier deserialization | low | tui/remote_world_state.py |

### Phase 3 (after WI-228 and WI-229)
| ID | Title | Complexity | Key files |
|----|-------|------------|-----------|
| WI-230 | Multi-cell rendering in WorldView | medium | tui/world_view.py |

## Dependency graph

```
WI-220 ─────────────────────────────────────────────► (done)
WI-221 ─────────────────────────────────────────────► (done)
WI-222 ─────────────────────────────────────────────► (done)
WI-223 ─────────────────────────────────────────────► (done)
WI-224 ─────────────────────────────────────────────► (done)
WI-225 ──► WI-226
WI-227 ──► WI-228 ──► WI-230
WI-227 ──► WI-229 ──► WI-230
WI-227 ──► WI-231
```

## Agent configuration
- Model: sonnet (all items)
- No additional decomposer required
