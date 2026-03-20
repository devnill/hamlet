## WI-139 Review

### Verdict: FAIL

### Findings

**F1: `test_tui_legend.py` tests `visible` reactive and `watch_visible` — these conflict with WI-142**

- **File**: `/Users/dan/code/hamlet/tests/test_tui_legend.py:83–115`
- **Issue**: Tests `test_reactive_visible_update`, `test_watch_visible_syncs_display`, `test_action_toggle_legend`, and `test_action_hide_legend` all set and assert `legend.visible` as a reactive property on `LegendOverlay`. The spec for WI-142 requires removing the `visible` reactive from `HelpOverlay` precisely because it shadows `DOMNode.visible`; however `LegendOverlay` in `legend.py` still carries `visible: reactive[bool] = reactive(False)` and a `watch_visible` watcher. WI-139 was required to fix stale legend key tests — it did not remove that shadowing reactive. These two work items are now in direct conflict: the legend tests assume the reactive exists and works, while WI-142's rationale (shadowing `DOMNode.visible` is wrong) applies equally to `LegendOverlay`. WI-139 should have either (a) noted and flagged this inconsistency, or (b) updated the legend tests to use `.display` directly instead of asserting through a reactive. As written, the legend tests will pass only as long as `LegendOverlay` keeps its `visible` reactive, which is an acknowledged anti-pattern per WI-142.
- **Impact**: The accepted fix pattern from WI-142 (`display` instead of `visible` reactive) cannot be applied to `LegendOverlay` without breaking eight tests in `test_tui_legend.py`. Future implementors are blocked from cleaning up `LegendOverlay` by the stale test design.
- **Suggested fix**: Replace every `legend.visible` assertion in `test_tui_legend.py` with `legend.display`. Update `test_initial_visibility` to assert `legend.display is False`. Update `test_action_toggle_legend` and `test_action_hide_legend` to assert `legend.display`. Remove `test_reactive_visible_update` and `test_watch_visible_syncs_display` entirely (they test the shadowing reactive, which is the pattern being abandoned).

**F2: `test_tui_app.py` toggle-legend test still reads `legend.visible` (the shadowing reactive)**

- **File**: `/Users/dan/code/hamlet/tests/test_tui_app.py:175–188`
- **Issue**: `test_action_toggle_legend_toggles_visibility` reads `legend.visible` and asserts `not initial_visible`. Because `app.py:action_toggle_legend` at line 221 sets `overlay.visible = not overlay.visible` (using the reactive), the test passes — but for the wrong reason. If `action_toggle_legend` were corrected to use `overlay.display` (consistent with `action_toggle_help`), this test would break. The test should be asserting `legend.display`, not `legend.visible`.
- **Impact**: Same blocking issue as F1; prevents aligning `LegendOverlay` with the display-based pattern.
- **Suggested fix**: Change lines 175, 182, and 188 to read `legend.display` instead of `legend.visible`.

**F3: README does not document the daemon/viewer split workflow**

- **File**: `/Users/dan/code/hamlet/README.md:34–37`
- **Issue**: The criterion states "daemon/viewer workflow docs" must be added. The Usage section at lines 34–37 lists the three commands (`hamlet daemon`, `hamlet`/`hamlet view`, `hamlet init`) as brief one-liners with no explanation of the relationship between the daemon and the viewer — no mention that the daemon must be started first, no example invocation sequence, no note about what happens if the viewer is opened without a running daemon.
- **Impact**: Users who open the README will not understand they need to run the daemon before the viewer. The criterion is only marginally satisfied (the commands are listed) but the workflow documentation is absent.
- **Suggested fix**: Add a "Daemon & Viewer" subsection under Usage explaining: (1) start the daemon with `hamlet daemon` in one terminal; (2) open the viewer with `hamlet view` in another; (3) both must share the same `~/.hamlet/world.db`; (4) what the viewer shows when no daemon is reachable.

---

## WI-142 Review

### Verdict: PASS_WITH_NOTES

### Findings

**N1: `action_toggle_legend` in `app.py` still uses `overlay.visible` (the shadowing reactive on `LegendOverlay`)**

- **File**: `/Users/dan/code/hamlet/src/hamlet/tui/app.py:221`
- **Issue**: `action_toggle_help` correctly uses `overlay.display` (the criterion is satisfied for `HelpOverlay`). However, the directly adjacent `action_toggle_legend` (line 221) still sets `overlay.visible = not overlay.visible` on `LegendOverlay`, which still carries the shadowing reactive. WI-142 fixed the pattern for `HelpOverlay` but left the identical anti-pattern untouched in `LegendOverlay`/`action_toggle_legend`. This is not a criterion violation for WI-142 (which only required fixing `HelpOverlay`), but it leaves the codebase in an inconsistent state that will cause confusion.
- **Suggested fix**: Change line 221 to `overlay.display = not overlay.display` and remove the `visible` reactive from `LegendOverlay` (coordinated with the legend test fixes described in WI-139 F1 and F2 above).

**N2: No tests added for `HelpOverlay` or `action_toggle_help`**

- **File**: `/Users/dan/code/hamlet/tests/test_tui_app.py` (no corresponding help overlay test file found)
- **Issue**: WI-142 changed the visibility mechanism for `HelpOverlay` — the only user-visible behaviour of that widget. There are no tests verifying that pressing `?` shows the overlay, that pressing `?` again hides it, or that `overlay.display` is the property that changes. The fix is therefore untested.
- **Suggested fix**: Add a `test_action_toggle_help_toggles_display` test in `test_tui_app.py` mirroring the structure of `test_action_toggle_legend_toggles_visibility` (lines 162–188), but asserting `help_overlay.display` before and after pressing `?`.
