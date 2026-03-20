## Verdict: Fail

Three tests that assert `legend.display is False` on a standalone (unmounted) widget fail at runtime because Textual's `DEFAULT_CSS` is not applied until a widget is mounted inside a running app; the bare Python attribute defaults to `True`.

## Critical Findings

### C1: Three display-state tests fail against standalone widget instances

- **File**: `/Users/dan/code/hamlet/tests/test_tui_legend.py:81`, `:86`, `:95`
- **Issue**: `test_initial_display_is_false`, `test_display_can_be_set_true`, and `test_display_can_be_toggled` all instantiate `LegendOverlay()` without mounting it in a Textual app and assert `legend.display is False`. Textual only parses and applies `DEFAULT_CSS` during the mount lifecycle; the underlying `_reactive` for `display` defaults to `True` before CSS is applied. All three assertions fail with `assert True is False`.
- **Impact**: The test suite is broken — `pytest tests/test_tui_legend.py` exits with 3 failures. CI will not be green.
- **Suggested fix**: The three unit tests must be rewritten to use the app-context pattern already present in `test_render_integration`. Each should spin up a minimal `TestApp`, mount the overlay, and then read `display` via `pilot.app.query_one(LegendOverlay).display`. For example:

  ```python
  @pytest.mark.asyncio
  async def test_initial_display_is_false(self) -> None:
      class TestApp(App):
          def compose(self):
              yield LegendOverlay()

      async with TestApp().run_test() as pilot:
          overlay = pilot.app.query_one(LegendOverlay)
          assert overlay.display is False
  ```

  Alternatively, if a synchronous unit test is preferred, the test can avoid asserting the CSS-derived default and instead only assert the post-set value (removing the precondition assertion that assumes `False` before any assignment).

## Significant Findings

None.

## Minor Findings

### M1: `test_no_bindings_on_overlay` passes for the wrong reason

- **File**: `/Users/dan/code/hamlet/tests/test_tui_legend.py:103`
- **Issue**: The test asserts `not hasattr(LegendOverlay, "BINDINGS") or LegendOverlay.BINDINGS == []`. `Static` (the base class) defines `BINDINGS = []`, so the condition is satisfied by inheritance, not by any LegendOverlay-specific characteristic. The test does not distinguish between "LegendOverlay explicitly declares no bindings" and "LegendOverlay inherits an empty list."
- **Suggested fix**: Change the assertion to verify that `BINDINGS` is not defined directly on `LegendOverlay`:

  ```python
  assert "BINDINGS" not in LegendOverlay.__dict__
  ```

## Unmet Acceptance Criteria

- [ ] **Tests verify display attribute not visible reactive** — Three of the seven replacement tests (`test_initial_display_is_false`, `test_display_can_be_set_true`, `test_display_can_be_toggled`) fail at execution. The acceptance criterion requires passing tests that verify display-based behavior; broken tests do not satisfy this.
