# Change Plan — refine-13: Village Name Display + Multi-Cell Structures + Maintenance

## What is changing and why

Post-convergence refinement after brrr cycle 7. Addresses four deferred open questions, two
hotfixes needing formal test coverage, and two new features requested after first use.

### Maintenance: Open Questions

**Q-14: handle_event enum dispatch** (WI-220)
`WorldStateManager.handle_event()` compares `event.hook_type.value == "Notification"` (string)
rather than `event.hook_type == HookType.Notification` (enum). Engine uses enum. Unify.

**Q-10: Bash string tool_output** (WI-221)
`EVENT_SCHEMA` rejects plain-string `tool_output`. Bash PostToolUse events with string stdout
are silently discarded. Widen schema to accept `["object", "string", "null"]` and update
`event_processor.py` to handle the string case without crashing.

**Q-13: stop_reason behavioral differentiation** (WI-222)
All Stop events currently produce immediate despawn. Differentiate:
- `"stop"` / `"end_turn"`: immediate despawn (clean session end)
- `"tool"`: transition to ZOMBIE (interrupted; may resume)

**Q-15: Test coverage gaps** (WI-223, WI-224)
11 new HookType values, 11 handle_event branches, on_resize handler, is_plugin_active —
all untested since cycle 008. Two work items: event pipeline coverage, and TUI/install/
persistence coverage (which also covers the two hotfixes below).

### Maintenance: Hotfixes with Missing Tests

Two fixes applied outside the formal cycle need test coverage:
- `PersistenceFacade.stop()` drains queue before cancelling (WI-224)
- `WorldView.render()` syncs viewport to `self.size` each frame (WI-224)

### Feature 1: Viewport-Centered Village Name in Status Bar (WI-225, WI-226)

The status bar "Project:" line currently shows the project name from `.hamlet/config.json`.
Replace it with the name of the village the viewport is currently centered on.

- New `get_nearest_village_to(x, y)` method on WorldStateManager, WorldStateProtocol, RemoteWorldState
- StatusBar widget updated to query nearest village name based on viewport center coordinates
- When no village exists, show "—"

### Feature 2: Multi-Cell Structures Based on Work Volume (WI-227–WI-231)

Structures gain a size tier determined by cumulative work_units. Thresholds are configurable.
The work-type classifier is a pluggable interface (default: volume-only; future: new-feature vs bug-fix heuristic).

Size tiers:
| Tier | Footprint | Default work_unit threshold |
|------|-----------|----------------------------|
| 1    | 1×1       | 0 (initial)                |
| 2    | 3×3       | 500                        |
| 3    | 5×5       | 2000                       |
| 4    | 7×7       | 5000                       |

Visual: rectangular box-drawing border (`+`, `-`, `|`) for tiers 2+; interior shows structure symbol.

Hard footprint: structure claims all cells in its footprint in the occupancy grid.
Agent displacement: when tier increases, agents in the new footprint cells move to the nearest free cell outside.

Work items:
- WI-227: Structure size_tier data model + persistence + serialization
- WI-228: Size tier calculation in StructureUpdater (pluggable classifier)
- WI-229: Multi-cell footprint in PositionGrid + agent displacement in WorldStateManager
- WI-230: Multi-cell rendering in WorldView with box-drawing characters
- WI-231: RemoteWorldState deserialization for size_tier

## Scope

**Changing:**
- `src/hamlet/world_state/manager.py` — nearest village query; agent displacement; enum dispatch (Q-14)
- `src/hamlet/world_state/types.py` — Structure.size_tier field
- `src/hamlet/world_state/grid.py` — multi-cell footprint occupancy
- `src/hamlet/world_state/rules.py` — size tier thresholds
- `src/hamlet/simulation/structure_updater.py` — pluggable work classifier, tier upgrade logic
- `src/hamlet/simulation/config.py` — size tier threshold config
- `src/hamlet/protocols.py` — get_nearest_village_to method
- `src/hamlet/mcp_server/validation.py` — widen tool_output schema (Q-10)
- `src/hamlet/mcp_server/serializers.py` — serialize size_tier
- `src/hamlet/event_processing/event_processor.py` — handle string tool_output (Q-10)
- `src/hamlet/inference/engine.py` — stop_reason differentiation (Q-13)
- `src/hamlet/tui/world_view.py` — multi-cell rendering
- `src/hamlet/tui/status_bar.py` — village name display
- `src/hamlet/tui/remote_world_state.py` — nearest village stub + size_tier deserialization
- `src/hamlet/persistence/migrations.py` — add size_tier column
- `src/hamlet/persistence/loader.py` — load size_tier
- `src/hamlet/persistence/writer.py` — write size_tier
- Tests for all modified modules

**Not changing:** Hook scripts, CLI commands, inference type rules, MCP plugin server, viewport module, legend/help overlays, animation system, expansion system (beyond agent displacement).

## Work items

- WI-220: Fix handle_event enum dispatch (Q-14)
- WI-221: Fix EVENT_SCHEMA + event_processor for Bash string tool_output (Q-10)
- WI-222: stop_reason behavioral differentiation in inference engine (Q-13)
- WI-223: Event pipeline test coverage — HookType parametrized + handle_event branches (Q-15)
- WI-224: TUI/persistence test coverage — on_resize, is_plugin_active, facade drain, worldview render (Q-15 + hotfixes)
- WI-225: get_nearest_village_to() method on WorldStateManager + protocol + RemoteWorldState
- WI-226: StatusBar village name from viewport center
- WI-227: Structure size_tier data model + persistence migration + serialization
- WI-228: Size tier calculation in StructureUpdater with pluggable work classifier
- WI-229: Multi-cell footprint in PositionGrid + agent displacement on tier upgrade
- WI-230: Multi-cell rendering in WorldView with box-drawing characters
- WI-231: RemoteWorldState deserialization for size_tier
