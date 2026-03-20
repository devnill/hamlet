# Policies: Visualization

## P-1: Roguelike Iconography
Agents are `@` characters. Colors indicate type (researcher=cyan, coder=yellow, architect=magenta, tester=blue, general=white). Terrain uses standard roguelike symbols (`.` floor, `#` wall).

- **Derived from:** GP-3 (Thematic Consistency)
- **Established:** planning phase
- **Amended:** cycle 003 — EXECUTOR color changed from green to red (was colliding with zombie tint); PLANNER changed from green to dark_green. See D-4.
- **Status:** active

## P-2: Frenetic Activity is Good
More events = more visual interest. Debounce similar actions, but otherwise allow rapid updates. The simulation runs at 30 FPS.

- **Derived from:** GP-1 (Visual Interest Over Accuracy)
- **Established:** planning phase
- **Status:** active

## P-3: Deterministic Color Assignment
Agent color is derived from inferred type, not random. Same type = same color. Zombie state blends with green.

- **Derived from:** GP-6 (Deterministic Identity)
- **Established:** planning phase
- **Status:** active

## P-4: Parent-Child Proximity
New agents spawn near their parent (within 3 cells). Team/session agents cluster together.

- **Derived from:** GP-9 (Parent-Child Spatial Relationships)
- **Established:** planning phase
- **Status:** active

## P-5: Agent type colors must be defined in a single authoritative table
All agent type color assignments must be defined in `inference/types.py` `TYPE_COLORS`. Any module needing agent colors must import from that table. No local color map copies are permitted.

- **Derived from:** D-4, D-6, D-11, archive/cycles/006/decision-log.md (D-E8, CR2)
- **Established:** cycle 004
- **Amended:** cycle 006 — scope changed from "EXECUTOR must be red in all color tables" to "single authoritative table." `AGENT_BASE_COLORS` was removed from `animation.py` (WI-123); `TYPE_COLORS` in `inference/types.py` is now the sole color authority. The multi-table requirement is no longer applicable.
- **Status:** active
