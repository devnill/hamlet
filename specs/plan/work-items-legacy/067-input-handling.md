# 067: Input Handling and Actions

## Objective
Implement key binding actions for scrolling, follow mode toggle, and legend toggle.

## Acceptance Criteria
- [ ] `action_scroll_left()` calls `viewport.scroll(-1, 0)`
- [ ] `action_scroll_right()` calls `viewport.scroll(1, 0)`
- [ ] `action_scroll_up()` calls `viewport.scroll(0, -1)`
- [ ] `action_scroll_down()` calls `viewport.scroll(0, 1)`
- [ ] `action_toggle_follow()` toggles follow mode (center on active agent or village)
- [ ] `action_toggle_legend()` toggles legend overlay visibility
- [ ] `action_quit()` exits the application
- [ ] Bindings use hjkl keys (vim-style) plus arrow keys

## File Scope
- `src/hamlet/tui/app.py` (modify)

## Dependencies
- Depends on: 061, 066
- Blocks: 068

## Implementation Notes
Textual actions are defined as `action_<name>()` methods. Key bindings map keys to actions via `BINDINGS` class attribute. Scroll amount is 1 cell per key press. Follow mode: first press enables follow on most recently active agent, second press returns to village center.

## Complexity
Low