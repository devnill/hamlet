# 064: StatusBar Widget

## Objective
Implement the status bar widget showing agent count, structure count, project name, and viewport position.

## Acceptance Criteria
- [ ] File `src/hamlet/tui/status_bar.py` exists
- [ ] `StatusBar` class inherits from `textual.widgets.Static`
- [ ] Reactive properties: `agent_count`, `structure_count`, `project_name`, `viewport_pos`
- [ ] `render()` method returns formatted string: "Agents: N │ Structures: N │ Project: name │ (x,y)"
- [ ] Separators are `│` (Unicode pipe) with spaces
- [ ] Updates are reactive (Textual's `reactive` decorator)

## File Scope
- `src/hamlet/tui/status_bar.py` (create)

## Dependencies
- Depends on: 061
- Blocks: 068

## Implementation Notes
Use Textual's `reactive` attribute for each status field. The main app updates these reactive properties when state changes. Render format: "Agents: {agent_count} │ Structures: {structure_count} │ Project: {project_name} │ ({x}, {y})"

## Complexity
Low