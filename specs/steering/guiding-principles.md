# Guiding Principles

## 1. Visual Interest Over Accuracy
The primary goal is a fun, visually engaging idle game. Agent activity should produce frenetic, interesting visuals. Debounce similar actions to prevent visual spam, but otherwise allow high event throughput to create activity. When in doubt, choose the option that makes the screen more interesting to watch.

**Why:** User explicitly stated "more work in claude code to yield a more visually interesting and frenetic screen." The idle game is the primary interface; observability is a future benefit.

**How to apply:** When designing event handling, prefer real-time visual feedback over queued/aggregate display. When mapping tools to actions, prioritize visual variety over semantic precision.

## 2. Lean Client, Heavy Server
Hook scripts should do minimal processing — just enough to extract essential telemetry and send it to the MCP server. All state management, inference, and world simulation happen server-side. The client is a thin data collector.

**Why:** User emphasized "the client should be as lean as possible, even if that means additional processing happens on the other side." Non-destructive hook integration is critical.

**How to apply:** Hook scripts should contain no business logic. They extract agent name, tool name, and basic context, then immediately push to the server. No local state, no complex parsing.

## 3. Thematic Consistency
This is a simulation-style idle game. Thematic consistency must hold regardless of rendering backend. In the ASCII backend (Textual), the aesthetic is Dwarf Fortress / ADOM / Nethack — characters with semantic meaning where experienced players "see through" the text. In the graphical backend (Kitty graphics protocol), the aesthetic is SNES/16-bit simulation — think Stardew Valley or the Thronglets game from Black Mirror's "Plaything." Both backends share the same medieval village theme; only the visual language changes.

**Why:** User specified roguelike games as the ASCII visual target and SNES/Stardew Valley as the graphical target: "In a terminal, dwarf fortress makes sense. In 16 bit, this would be a 16 bit sim game."

**How to apply:** ASCII backend: use established symbol conventions (`@` for humanoids, `.` for floor, `#` for walls), color indicates status. Graphical backend: use pixel-art sprites with constrained 16-32 color palette, SNES-era proportions, zoom-dependent resolution via Kitty graphics protocol (pure Python escape sequences, no C library). Both: structure types feel like a medieval village, agents are visually distinct by type, zombie state is always visible.

> _Changed in refinement (2026-03-22): Expanded from ASCII-only roguelike to backend-agnostic thematic consistency. Added SNES/Stardew graphical aesthetic alongside existing Dwarf Fortress ASCII aesthetic._
> _Changed in refinement (2026-03-22): Replaced notcurses with Kitty graphics protocol. notcurses segfaults with Python 3.14 due to memory allocator incompatibility (see steering/research/notcurses-python314-segfault.md). Kitty protocol is pure Python — no C library needed._

## 4. Modularity for Iteration
All mappings (tool-to-action, agent-type-to-color, structure progression) should be configurable and swappable. The first version won't be perfect, so the architecture must support easy iteration on visual and gameplay elements.

**Why:** User stated: "It doesn't need to be a perfect mapping as long as the screen is visually interesting" and "This is subject to change, but design around the agents having specific activities that they do based on hook. It should be designed in a way that could be modular."

**How to apply:** Use configuration files or data structures for tool-to-action mappings. Don't hardcode building types or animation timings. Make it easy to swap in new visual behaviors without rewriting core logic.

## 5. Persistent World, Project-Based Villages
The world persists across sessions. Each project (codebase) maps to a village that grows over time. Multiple projects create multiple villages on a global map. Villages can expand, connect via roads, and found new settlements.

**Why:** User specified: "the persistent map should track all projects ever worked on - this is a global map that has lots of little villages" and "a single codebase should be a single village that grows out."

**How to apply:** SQLite must store project-to-village mappings. New events from a project update its village. The UI must support scrolling to view different villages. World state survives app restarts.

## 6. Deterministic Agent Identity
Agent appearance and behavior should be deterministic based on extractable properties: type (researcher, coder, planner, etc.) determines color, team/session determines spatial clustering, idle time determines visual state (zombie effect).

**Why:** User specified: "deterministic" for color assignment, "agents on the same team or session should prefer to be close together," and agents not heard from "could turn a greenish hue to look like a zombie."

**How to apply:** Derive color from a hash of agent type, not random assignment. Group agents by session/team for proximity calculations. Track last-seen timestamp per agent for idle detection.

## 7. Graceful Degradation Over Robustness
If the MCP server is down or events are lost, the game continues. Hook scripts fail silently without blocking Claude Code. The UI shows what it has, not error states. Missing data is preferable to broken workflows.

**Why:** User specified: "We can discard messages for now" when asked about failure handling. The priority is a working idle game, not mission-critical observability.

**How to apply:** Hook scripts should have minimal error handling — catch exceptions and exit cleanly. The server should handle missing or malformed events gracefully. No retry logic, no blocking waits.

## 8. Agent-Driven World Building
The world changes as agents work. Token expenditure roughly correlates to construction progress. Structures evolve (wood → stone). Roads connect settlements. The village grows outward over time.

**Why:** User specified: "the amount they work should roughly map to the number of tokens spent. As work continues, workers might rebuild from wooden building to stone, make roads, etc."

**How to apply:** Design a progress system where tool calls contribute to construction "work units." Track cumulative work per structure type. Trigger upgrades at thresholds. Agents visibly participate in construction animations.

## 9. Parent-Child Spatial Relationships
New agents spawn near their parent. This creates visual clustering of related work and makes the spawn relationship visible at a glance.

**Why:** User specified: "when they spawn, they should just pop on to the screen next to the parent which spawned them."

**How to apply:** When an agent spawn event is detected (inferred from tool patterns), place the new agent at a position adjacent to the parent agent. Use proximity for team clustering as a secondary behavior.

## 10. Scrollable World, Visible Agents
The user can scroll the world view. Agents should remain visible on screen when possible, with the view automatically scrolling to follow workers as they move beyond the current viewport center.

**Why:** User specified: "the screen should sometimes need to scroll as the workers move beyond the center as the village as it become a city."

**How to apply:** Implement viewport panning. When agents move near the edge, optionally auto-scroll to keep them visible. The global map can extend beyond the visible area; scrolling reveals other villages.

## 11. Low-Friction Setup
Getting started with Hamlet should require minimal steps. Prefer auto-detection over manual configuration. A new user should be able to install and see their first village within minutes, not hours.

**Why:** User explicitly stated: "ensuring that the tool is low friction to set up." Complex setup creates adoption friction and discourages usage.

**How to apply:** Hook installation should be a single command. Configuration should use sensible defaults with optional overrides. The app should auto-detect Claude Code installation and suggest hook paths. Error messages should guide users to fixes, not just report failures.