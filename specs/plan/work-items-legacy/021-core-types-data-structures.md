# 021: Core Types and Data Structures

## Objective
Define core types for agent inference: AgentType enum, InferenceResult dataclass, InferenceState, PendingTool, SessionState, and ToolWindow.

## Acceptance Criteria
- [ ] `AgentType` enum exists with values: RESEARCHER, CODER, EXECUTOR, ARCHITECT, TESTER, GENERAL
- [ ] `InferenceResult` dataclass with action, agent_id, parent_id, inferred_type, position fields
- [ ] `InferenceAction` enum with SPAWN, UPDATE, COMPLETE, IDLE values
- [ ] `PendingTool`, `SessionState`, `ToolWindow`, `InferenceState` dataclasses
- [ ] `TYPE_COLORS` constant maps AgentType to color strings
- [ ] Module exports all types

## File Scope
- `src/hamlet/inference/__init__.py` (create)
- `src/hamlet/inference/types.py` (create)

## Dependencies
- Depends on: none
- Blocks: 022, 023, 024, 025

## Implementation Notes
All types use `@dataclass`. `AgentType` enum defines color mapping. `InferenceState` tracks pending tools, sessions, and tool windows for inference.

## Complexity
Low