# 063: WorldView Widget

## Objective
Implement the main world rendering widget that displays agents and structures.

## Acceptance Criteria
- [ ] File `src/hamlet/tui/world_view.py` exists
- [ ] `WorldView` class inherits from `textual.widgets.Static`
- [ ] `__init__(world_state: WorldStateManager, viewport: ViewportManager)` receives dependencies
- [ ] `render()` method returns Rich Text with world display
- [ ] `on_mount()` sets up animation frame update interval (4 Hz)
- [ ] Builds display buffer by iterating over visible bounds
- [ ] Agents render as spin animation symbols when active, `@` when idle/zombie
- [ ] Structures render with type symbol and material color
- [ ] Empty cells render as `.` (period)
- [ ] Uses `viewport.get_visible_bounds()` for bounds
- [ ] Uses `world_state.get_agents_in_view(bounds)` and `get_structures_in_view(bounds)`

## File Scope
- `src/hamlet/tui/world_view.py` (create)

## Dependencies
- Depends on: 061, 062
- Blocks: 068

## Implementation Notes
The WorldView widget is the main rendering surface. It iterates over world positions within the viewport bounds and checks for entities at each position. Render priority: agents over structures over empty. Animation uses 4-frame spin: `-\|/`. Use Rich Text for color styling.

## Complexity
Medium