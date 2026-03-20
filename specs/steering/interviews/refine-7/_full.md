# Refinement Interview — 2026-03-20 (refine-7: v0.4.0)

**Context**: New requirements for v0.4.0. Three areas: (1) implement all available Claude Code hook types, (2) adaptive viewport based on terminal window size, (3) seamless plugin updates via marketplace.

---

## Intent

**Q: What specific changes do you want to make?**
A: Three things: implement all available Claude Code hook types (currently only 4 of 26+ are implemented), make the viewport adaptive to the terminal window size, and ensure the plugin can update via the marketplace with no human intervention.

**Q: What is the primary motivation for implementing all hooks?**
A: Visual frenetic-ness. Every hook event should feed into movement or animation of characters. Core value (semantic accuracy) is less important than having a busy, interesting-looking UI during active sessions. Elaborate animations can come later when building a GUI — for now, any event = some movement.

**Q: Are there aspects of the current implementation to preserve?**
A: Yes — all existing hook scripts, the inference engine, world state, TUI, persistence. The scope is: new hooks, viewport wiring, install hygiene.

---

## Hook Architecture

**Q: HTTP hooks now exist in Claude Code (v2.1.63+). Want to migrate hook scripts to HTTP hooks for lighter weight?**
A: No. Keep Python scripts. The `async: true` capability (fire-and-forget, no blocking) only exists for command hooks, not HTTP hooks. Silent non-blocking is the priority.

**Q: PreToolUse is a blocking hook event — `async: true` is explicitly unsupported on it per docs. Should we remove it?**
A: Yes, fix it. Hooks should fire as silently as possible.

**Q: SubagentStart/Stop now expose direct agent lifecycle — do you want this to replace the inference engine's spawn detection, or coexist?**
A: Coexist. As long as the hook scripts pass accurate data with sufficient information, it doesn't matter which inference engine processes it. Don't change the inference engine.

**Q: Which of the 11 new hook types should be implemented?**
A: All of them. Even if a hook only triggers simple movement, every hook should feed into something visual.

New hooks to implement:
- SubagentStart, SubagentStop (v2.1.33+) — direct agent spawn/completion
- SessionStart, SessionEnd — session lifecycle
- TeammateIdle, TaskCompleted (v2.1.33+) — team activity
- PostToolUseFailure — tool error state
- UserPromptSubmit — user typing / thinking state
- PreCompact, PostCompact (v2.1.76+) — context compression
- StopFailure (v2.1.78+) — API error observability

---

## Viewport

**Q: Adaptive viewport — should it update only on mount, or also on terminal resize during runtime?**
A: Both. On mount and on every resize.

**Q: The TUI layout has a status bar and event log taking rows. Should the viewport size reserve rows for those, or match the full terminal?**
A: Match the WorldView widget's actual rendered size — whatever Textual gives the WorldView widget after layout. Don't hardcode offsets.

---

## Plugin Updates

**Q: What specifically is broken about the current update flow?**
A: The concern is redundant hooks — `hamlet install` writes hooks to settings.json AND the plugin's hooks.json also registers them. On update, old entries may persist. The user suspects this may already be resolved but wants it confirmed and hardened for the new hook additions.

**Q: Should `hamlet install` detect the plugin is active and skip, warn, or refuse?**
A: Warn and skip. If the plugin is managing hooks, `hamlet install` should not duplicate them.

---

## Principles Check

**Q: Do the guiding principles still apply?**
A: Yes — all 11 principles unchanged.

---

## Scope Boundary

**Not changing**: src/hamlet/ application code (except WorldStateManager/EventProcessor for new event types and WorldView for resize), tests (will need updating for new types), existing hook scripts, inference engine logic, TUI layout, persistence schema, mcp/server.py.
