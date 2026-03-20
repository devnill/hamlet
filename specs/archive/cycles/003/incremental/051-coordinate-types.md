## Verdict: Fail

get_visible_bounds has an off-by-one for even viewport dimensions causing is_visible to approve positions that world_to_screen maps off-screen; integer constraint unmet at runtime.

## Critical Findings

### C1: `get_visible_bounds` off-by-one for even viewport dimensions
- **File**: `src/hamlet/viewport/coordinates.py:85-90`
- **Issue**: With even width (e.g., 10), half_w=5. Bounds span [center-5, center+5] = 11 cells. But world_to_screen maps world_x=center+5 to screen_x=10, which equals viewport_size.width — one past valid columns 0-9.
- **Impact**: Rendering code trusting is_visible will attempt to draw at screen_x==viewport_size.width.
- **Suggested fix**: `max_x = center.x + half_w - 1 + (viewport_size.width % 2)`, same for max_y.

## Significant Findings

### S1: Integer type annotations not enforced at runtime
- **File**: `src/hamlet/viewport/coordinates.py:13-35`
- **Issue**: Dataclasses declare int fields but Python doesn't enforce at runtime. Float inputs propagate silently.
- **Impact**: Downstream rendering receives float screen positions; TUI APIs require integer cell coordinates.
- **Suggested fix**: Add `__post_init__` coercion or validation to each dataclass.

## Minor Findings

### M1: BoundingBox fields have no type annotations
- **File**: `src/hamlet/viewport/coordinates.py:29-35`
- **Issue**: min_x, min_y, max_x, max_y defined without `: int` annotations.
- **Suggested fix**: Add `: int` to each field.

## Unmet Acceptance Criteria

- [ ] Criterion 9 — All coordinates are integers: int annotations not enforced at runtime; floats pass through.
