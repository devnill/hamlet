---
## Refinement Interview — 2026-03-21

Full compiled transcript. See _general.md for the cross-cutting questions.

### Triggers
- New features (two, described below)
- Open questions Q-10, Q-13, Q-14, Q-15
- Hotfixes needing formal test coverage

### Open Questions Triaged

| Question | Decision |
|----------|----------|
| Q-10: Bash string tool_output | Address now — widen schema + event processor |
| Q-14: handle_event enum dispatch | Address now — 1-line fix in manager.py |
| Q-13: stop_reason behavioral differentiation | Address now — "tool" stop → ZOMBIE, clean stop → immediate despawn |
| Q-15: Test coverage gaps | Address now — split into two work items |
| Q-16: notification_type silently discarded | Defer |
| Q-17: is_plugin_active substring match | Fold into Q-15 test coverage item |

### Feature 1: Viewport-Centered Village Name

Status bar "Project:" line replaced with the name of the village the viewport is currently centered on.

Implementation notes:
- Viewport center is world coordinates (x, y) known in the TUI layer
- Need a method to find the nearest village to a given point — add to WorldStateManager, WorldStateProtocol, RemoteWorldState
- StatusBar polls this each refresh cycle (same 500ms polling cadence as RemoteStateProvider)
- When viewport is over empty space with no village within reasonable range, show the nearest village name anyway (or "—" if none exist)

### Feature 2: Multi-Cell Structures Based on Work Volume

Structure size is determined by cumulative work_units:
- Tier 1: 1×1 (current behavior, small work)
- Tier 2: 3×3 (medium work)
- Tier 3: 5×5 (large work)
- Tier 4: 7×7 (very large, rare)

Thresholds configurable in settings/config, defaulting to reasonable values.
Work-type classifier is modular — starts as "work unit volume only" but designed for pluggable future classifiers (new feature vs bug fix).

Visual: rectangular box-drawing border for tiers 2+:
```
Tier 2 (3×3):    Tier 3 (5×5):
+---+            +-----+
| W |            |     |
+---+            |  W  |
                 |     |
                 +-----+
```
Interior cells show the structure symbol; border cells show box-drawing characters.

Hard footprint: structure claims all cells in its footprint in the occupancy grid.
Agent displacement: when a structure's tier increases, agents occupying the new footprint cells are moved to the nearest free cell outside the footprint.

Work type classifier is a pluggable interface (function or class) in simulation/structure_updater.py. Default implementation: work unit volume → tier. Future: tool ratio heuristics for new-feature vs bug-fix classification.

### Hotfixes to Formally Track

Two fixes applied outside the ideate cycle need test coverage:
1. `PersistenceFacade.stop()` drains write queue before cancelling task — needs test
2. `WorldView.render()` syncs viewport to `self.size` on every frame — needs test
