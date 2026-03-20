# 031: Define Data Model Types

## Objective
Create Python dataclasses defining all world state entity types: Position, Bounds, Project, Session, Village, Agent, Structure.

## Acceptance Criteria
- [ ] File `src/hamlet/world_state/types.py` exists
- [ ] `Position` dataclass with x, y integer fields
- [ ] `Bounds` dataclass with min_x, min_y, max_x, max_y fields
- [ ] `Project`, `Session`, `Village`, `Agent`, `Structure` dataclasses defined
- [ ] `AgentType` enum: RESEARCHER, CODER, PLANNER, ARCHITECT, TESTER, GENERAL
- [ ] `StructureType` enum: HOUSE, WORKSHOP, LIBRARY, FORGE, TOWER, ROAD, WELL
- [ ] `AgentState` enum: ACTIVE, IDLE, ZOMBIE

## File Scope
- `src/hamlet/world_state/types.py` (create)

## Dependencies
- Depends on: none
- Blocks: 032, 034, 035, 036, 037

## Implementation Notes
All dataclasses use `@dataclass(frozen=False)`. Position must be frozen=True or implement `__hash__` for dict/set membership.

## Complexity
Low