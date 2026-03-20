# 061: Textual Application Setup (HamletApp)

## Objective
Create the main Textual application class with widget hierarchy and lifecycle management.

## Acceptance Criteria
- [ ] File `src/hamlet/tui/app.py` exists
- [ ] `HamletApp` class inherits from `textual.app.App`
- [ ] CSS layout defines three-row grid: StatusBar (1fr), WorldView (20fr), EventLog (5fr)
- [ ] `__init__(world_state: WorldStateManager, viewport: ViewportManager)` receives dependencies
- [ ] `compose()` method yields StatusBar, WorldView, EventLog widgets
- [ ] Key bindings defined for: q (quit), h/l/j/k (scroll), ? (legend), f (follow)
- [ ] `on_mount()` sets up 30 FPS refresh interval
- [ ] `async run_async()` method starts the application

## File Scope
- `src/hamlet/tui/app.py` (create)

## Dependencies
- Depends on: none
- Blocks: 063, 064, 065, 067

## Implementation Notes
Textual apps use CSS-like styling for layout. The grid layout ensures StatusBar is at top, EventLog at bottom, WorldView fills remaining space. Use `set_interval(1/30, self._refresh_world)` for frame-rate control.

## Complexity
Medium