---
## Refinement Interview — 2026-03-21

**Context**: Post-convergence refinement. Brrr session achieved convergence after 7 cycles (WI-217–219). Two hotfixes applied outside the formal cycle (facade drain fix, world_view render fix). User reporting new feature ideas and wants to address deferred open questions.

**Q: What triggered this refinement session?**
A: New features, open questions from prior cycles, and hotfixes needing formal tracking.

**Q: Which open questions do you want to address?**
A: Q-10 (Bash string tool_output), Q-15 (test coverage gaps), Q-13 (stop_reason behavioral differentiation), Q-14 (handle_event enum vs string dispatch). All four.

**Q: Do the guiding principles still apply?**
A: Yes, all 11 principles unchanged.

**Q: What new features do you have in mind?**
A: (1) The project title/status bar line should show the name of the village the viewport is currently centered on. (2) Structure size should be based on amount of work done — multi-cell footprint AND stage progression. New features create new structures, refinements/bug fixes extend existing ones. Size relative to work volume.

**Q: For the status bar: where should the village name appear?**
A: The 'Project:' line in the status bar. Replace project name with the village name of the village currently centered in the viewport.

**Q: For structures: what does 'size' mean in ASCII terms?**
A: Both multi-cell footprint AND stage progression. Multi-cell footprint is the priority.

**Q: How should hamlet infer new feature vs bug fix/refinement?**
A: Start with work unit volume only — skip the distinction for now. Structure code to be modular so the work type classifier can be swapped in later.

**Q: What should multi-cell structures look like visually?**
A: Rectangular border with interior using box-drawing characters. `+--+` / `|  |` / `+--+` style. Size scales with work units.

**Q: For the status bar: replace project name with village name, or show both?**
A: Replace project name with village name. The 'Project:' line shows the name of the village the viewport is centered on.

**Q: When a structure grows and nearby agents are in the way?**
A: Hard footprint — structure claims all cells in its footprint. Agents in the way should move out when a structure needs to expand.

**Q: What is the scope boundary?**
A: Architecture, guiding principles, constraints all unchanged. Changing: world_state, simulation, tui, persistence, mcp_server serializers, protocols. Not changing: hook scripts, CLI commands, inference type rules.
