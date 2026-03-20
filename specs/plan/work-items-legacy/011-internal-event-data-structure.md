# 011: InternalEvent Data Structure

## Objective
Define the `InternalEvent` dataclass and `HookType` enum for normalized events within the Hamlet system.

## Acceptance Criteria
- [ ] File `src/hamlet/event_processing/internal_event.py` exists
- [ ] `HookType` enum defined with values: `PreToolUse`, `PostToolUse`, `Notification`, `Stop`
- [ ] `InternalEvent` dataclass defined with all fields from architecture contract
- [ ] `InternalEvent` has `__post_init__` validation for hook_type and id
- [ ] Module exports `InternalEvent` and `HookType`

## File Scope
- `src/hamlet/event_processing/__init__.py` (create)
- `src/hamlet/event_processing/internal_event.py` (create)

## Dependencies
- Depends on: none
- Blocks: 012, 013, 014

## Implementation Notes
Fields: `id`, `sequence`, `received_at`, `session_id`, `project_id`, `project_name`, `hook_type`, `tool_name`, `tool_input`, `tool_output`, `success`, `duration_ms`, `raw_payload`. Use `@dataclass` decorator. Validation ensures `hook_type` is valid and `id` is non-empty.

## Complexity
Low