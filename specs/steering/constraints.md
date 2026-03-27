# Constraints

## Technology Constraints

1. **Python with Textual.** The UI must be built using Python and the Textual framework. This is non-negotiable based on the research recommendation for async-native architecture and MCP SDK integration.

2. **SQLite for persistence.** World state must be stored in SQLite. No other database is acceptable for the MVP.

3. **MCP Protocol.** Communication between Claude Code hooks and the application must use the Model Context Protocol (MCP). The application exposes an MCP server that receives hook events.

4. **Claude Code Hooks.** The application must integrate with all four Claude Code hook types: PreToolUse, PostToolUse, Notification, Stop. No other integration points exist.

## Design Constraints

1. **ASCII rendering is the default and must always be available.** The Textual backend uses ASCII characters with color and works in all terminals including tmux. Sprite-based rendering via the Kitty graphics protocol is permitted as an optional backend for terminals that support it (Ghostty, kitty, WezTerm). The system must gracefully degrade to ASCII when the graphical backend is unavailable. The graphical backend must be pure Python (no C libraries) to avoid interpreter compatibility issues.

> _Changed in refinement (2026-03-22): Expanded from "ASCII-only" to allow optional sprite-based backend while preserving ASCII as the universal fallback._
> _Changed in refinement (2026-03-22): Specified Kitty graphics protocol (pure Python) as the graphical backend. notcurses (C library via ctypes) removed due to Python 3.14 segfaults. Added "pure Python" constraint to prevent future C library dependencies in the rendering layer._

2. **Terminal UI.** The application runs in a terminal, not a browser or native GUI window. It must work in standard terminal emulators.

3. **Single persistent server.** One MCP server process handles events from multiple Claude Code sessions. The server is long-running and maintains world state.

4. **Lean hook scripts.** Hook scripts must do minimal processing. They extract basic telemetry and push to the MCP server. No local state, no complex parsing, no business logic.

5. **Non-destructive integration.** Hook setup must not interfere with existing Claude Code functionality. The setup command/skill must be reversible and safe.

6. **Project-based villages.** Each project (codebase) maps to exactly one village. Multiple projects create multiple villages on a shared global map.

7. **Deterministic identity.** Agent appearance (color) must be derived deterministically from agent type, not randomly assigned.

## Process Constraints

1. **No dedicated agent/task hooks.** Claude Code does not expose agent lifecycle or task lifecycle hooks. Agent spawning, completion, and relationships must be inferred from PreToolUse/PostToolUse patterns.

2. **Silent failure on errors.** If the MCP server is unreachable, hook scripts exit cleanly without blocking Claude Code. No retry logic, no error states in the UI.

3. **No out-of-scope features.** The following are explicitly excluded from MVP:
   - Sound effects
   - Multiplayer/spectator viewing
   - Replay/history scrubbing
   - Data export features
   - Filtering/search in logs

4. **Deployment is future scope.** The application should be pip-installable eventually, but packaging, distribution, and installation UX are not part of this iteration.

## Scope Constraints

1. **MVP focus.** The first iteration must be usable and demonstrate core functionality. Visual polish and iteration are expected, but the foundation must work.

2. **Observability is secondary.** The primary interface is an idle game. Observability is a future benefit, not a driving design requirement.

3. **Manual config.** Project configuration is done via a config file. No auto-detection of projects, no complex setup wizards.