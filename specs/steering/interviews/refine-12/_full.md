# Refinement Interview — 2026-03-20 (refine-12: startup bugs)

**Context**: Two runtime bugs discovered after installing the hamlet daemon as a launchd service (`hamlet service install`). A third bug (`RemoteWorldState.get_viewport_center` missing) was fixed directly as a hotfix in the same session (not planned through ideate).

---

**Q: When opening hamlet you see 6 agents even though no agents are running. What behavior do you expect?**

A: No active agents should be visible when no Claude sessions are running. Agents from past sessions that persist in the database are acceptable (persistent world), but they should not appear as active.

**Root cause identified**: `WorldStateManager.load_from_persistence()` restores agents with their stored DB state (e.g. `"active"`). The inference engine's `_check_zombie()` only evaluates agents in its own `_state.last_seen` dict, which is empty at startup. Loaded agents are therefore never transitioned to zombie through normal zombie detection — they stay "active" indefinitely after a daemon restart.

**Fix**: Restore all agents as `AgentState.ZOMBIE` in `load_from_persistence()`, regardless of their stored state. New hook events from active Claude sessions will promote specific agents back to ACTIVE via the normal inference path.

---

**Q: The initial paint shows only 2 rows and requires a terminal resize to render correctly. Is this the full extent of the issue?**

A: Yes — after resizing, the layout is correct. The fix should make the initial render fill the terminal correctly without requiring a manual resize.

**Root cause identified**: `WorldView.on_mount()` calls `self._viewport.resize(self.size.width, self.size.height)`. At mount time, Textual has not completed its layout pass, so `self.size` returns an incorrect partial value. This overwrites `ViewportState`'s default of `Size(80, 24)` with a wrong size. The `on_resize` event fires after the layout pass with the correct terminal size, but only after the first (broken) render.

**Fix**: Remove the `resize()` call from `on_mount`. The `on_resize` handler already updates the viewport dimensions after every layout change. The default `Size(80, 24)` is a better fallback for the brief period before the first resize event.

---

**Scope**: WI-208, WI-209. No architecture changes. Guiding principles and constraints unchanged.
