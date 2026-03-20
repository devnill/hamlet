# 066: LegendOverlay Widget

## Objective
Implement a toggleable legend overlay showing agent types, colors, and structure symbols.

## Acceptance Criteria
- [ ] File `src/hamlet/tui/legend.py` exists
- [ ] `LegendOverlay` class inherits from `textual.widgets.Static`
- [ ] Shows agent types with colors: "@ Researcher (cyan), @ Coder (yellow), @ Executor (green), @ Architect (magenta), @ Tester (blue), @ General (white)"
- [ ] Shows structure symbols: "∩ House, ◊ Workshop, ⌂ Library, ▲ Forge, ⎔ Tower, # Road, ○ Well"
- [ ] Shows material progression: "░ Wood → ▒ Stone → ▓ Brick → █ Enhanced"
- [ ] Shows agent states: "-\\|/ Active, @ Idle, @ (green-tinted) Zombie"
- [ ] `visible` reactive property controls display (default False)
- [ ] Toggle with `?` key binding
- [ ] Dismiss with `Esc` key

## File Scope
- `src/hamlet/tui/legend.py` (create)

## Dependencies
- Depends on: 061, 062
- Blocks: 067

## Implementation Notes
The legend is a modal overlay that covers part of the WorldView. Use Textual's `visible` reactive property to show/hide. Format as a bordered box with header. Key binding `?` toggles visibility, `Esc` hides it.

## Complexity
Low