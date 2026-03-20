# 022: Agent Inference Engine Skeleton

## Objective
Create the `AgentInferenceEngine` class with initialization, event dispatch logic, and main `process_event` method.

## Acceptance Criteria
- [ ] `AgentInferenceEngine` class in `src/hamlet/inference/engine.py`
- [ ] `__init__` accepts `world_state` dependency
- [ ] `async process_event(event: InternalEvent)` routes to hook-type handlers
- [ ] `_handle_pre_tool_use`, `_handle_post_tool_use`, `_handle_notification`, `_handle_stop` placeholder methods
- [ ] `get_inference_state()` returns current state
- [ ] Module exports `AgentInferenceEngine`

## File Scope
- `src/hamlet/inference/engine.py` (create)
- `src/hamlet/inference/__init__.py` (modify)

## Dependencies
- Depends on: 021
- Blocks: 023, 024, 025

## Implementation Notes
Define WorldState protocol for type hints. Placeholder handlers will be implemented in subsequent work items.

## Complexity
Low