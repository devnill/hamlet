# 002: Event Schema and Validation

## Objective
Define the JSON schema for incoming hook events and implement validation logic that discards malformed events per the graceful degradation principle.

## Acceptance Criteria
- [ ] File `src/hamlet/mcp_server/validation.py` exists
- [ ] `EVENT_SCHEMA` constant defines JSON-RPC 2.0 envelope with required fields
- [ ] Schema validates `params.session_id`, `params.timestamp`, `params.hook_type`, `params.project_id`
- [ ] Schema validates `hook_type` is one of "PreToolUse", "PostToolUse", "Notification", "Stop"
- [ ] `validate_event(payload: dict) -> ValidationResult` function returns validated data or error
- [ ] Invalid payloads are logged at WARN level and discarded
- [ ] Module exports `ValidationResult` and `validate_event`

## File Scope
- `src/hamlet/mcp_server/validation.py` (create)

## Dependencies
- Depends on: none
- Blocks: 003

## Implementation Notes
Use `jsonschema` library for validation. The schema must match the HookEvent contract from architecture. Validation failures are logged but not raised — per guiding principle 7, malformed events never crash the server.

## Complexity
Low