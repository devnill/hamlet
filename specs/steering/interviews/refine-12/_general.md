## Refinement Interview — 2026-03-20 (refine-12: startup bugs)

**Context**: Two runtime bugs discovered after installing the hamlet daemon as a launchd service.
A third bug (`RemoteWorldState` missing `get_viewport_center`) was found in the same session and fixed directly as a hotfix (version bumped to 0.5.1).

**Q: When opening hamlet you see 6 agents even though no agents are running. What behavior do you expect?**
A: No active agents should be visible when no Claude sessions are running. Agents from past sessions that persist in the database are acceptable (persistent world), but they should not appear as active.

**Q: The initial paint shows only 2 rows and requires a terminal resize to render correctly. Is this the full extent of the issue?**
A: Yes — after resizing, the layout is correct. The fix should make the initial render fill the terminal correctly without requiring a manual resize.

**Q: Zombies persist in the world indefinitely. What should happen to them?**
A: After a session ends cleanly (Stop hook), agents from that session should despawn immediately — no zombie phase, just gone. For agents that became zombie from timeout (no clean stop), they should despawn after a configurable delay (default 5 minutes). If an agent comes back (new events after zombification), it re-appears normally.

**Q: The legend opens but shows nothing. Is the content wrong or is it a display issue?**
A: Display issue — the legend content (symbols, colors, key bindings) exists in code but the overlay is not visible. Needs to be fixed so it renders correctly when toggled with /.

**Scope boundary**: Two bugs (WI-208, WI-209), zombie despawn (WI-210, WI-211), and legend fix (WI-212). No architecture changes. Guiding principles and constraints unchanged.
