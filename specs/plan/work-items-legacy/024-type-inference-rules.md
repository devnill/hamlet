# 024: Type Inference Rules

## Objective
Implement sliding window type inference that determines agent type from tool usage frequency.

## Acceptance Criteria
- [ ] `TYPE_RULES` constant defines (tool_patterns, minimum_ratio, agent_type)
- [ ] Rules include: Read/Grep/Glob → RESEARCHER (0.6), Write/Edit → CODER (0.6), Bash → EXECUTOR (0.5), Task → ARCHITECT (0.4)
- [ ] `_update_tool_window(event)` adds events to sliding window
- [ ] `_infer_type(session_id)` analyzes tool frequency
- [ ] Returns GENERAL if window has fewer than 10 events
- [ ] `_handle_post_tool_use` updates tool window and infers type

## File Scope
- `src/hamlet/inference/engine.py` (modify)
- `src/hamlet/inference/rules.py` (create)
- `tests/test_type_inference.py` (create)

## Dependencies
- Depends on: 022
- Blocks: none

## Implementation Notes
Use sliding window of 5 minutes. Tool frequency = count(tool_name) / total_events. If multiple rules match, first match wins.

## Complexity
Medium