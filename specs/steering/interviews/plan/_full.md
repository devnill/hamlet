<!-- domains: architecture, visualization, data-model -->
# Interview Summary — Planning Session

## Context
Planning session for Hamlet, a terminal-based idle game that visualizes Claude Code agent activity as ASCII characters building a village.

---

## General Questions

**Q: What technology stack for the UI?**
A: Terminal based, ASCII art like Dwarf Fortress/ADOM/Nethack. Textual (Python) recommended for async-native architecture and MCP SDK integration.

**Q: How should agent types be determined?**
A: Deterministic color by inferred type. Minimal processing on hook side, inference on server. Agents spawn near parent, cluster with team.

**Q: How should world state persist?**
A: SQLite, single persistent server tracking all projects. One village per project on global map.

**Q: What's explicitly out of scope?**
A: Tile graphics, sound effects, multiplayer viewing, replay/history, export features. MVP focus on usable, iterable foundation.

**Q: How should failures be handled?**
A: Discard messages silently. Idle game first, observability later. No blocking on errors.

---

## Architecture Domain

**Q: How should hook scripts be configured?**
A: All 4 hook types (PreToolUse, PostToolUse, Notification, Stop) send minimal telemetry. Config file specifies project name and MCP endpoint.

**Q: How should agent spawns be detected?**
A: Infer from PreToolUse/PostToolUse patterns. No dedicated agent hooks in Claude Code. Track concurrent tool calls to detect spawning.

---

## Visualization Domain

**Q: What should agents build?**
A: Structures that evolve (wood → stone). Roads connect villages. Token expenditure maps to construction work units. Visually interesting is priority over accuracy.

**Q: What visual states do agents have?**
A: Active (animated), idle (static), zombie (greenish color), blocked. Animation timing is designer judgment, modifiable.

**Q: How should colors be assigned?**
A: By agent type (researcher=cyan, coder=yellow, etc.). Idle agents fade. Zombie agents blend with green.

---

## Data Model Domain

**Q: How should projects be identified?**
A: Config file with project name and MCP configuration. Sent over MCP with each event.

**Q: How should events be logged?**
A: Chronological scroll, no filtering yet. High volume acceptable — visual indicator of activity.

**Q: How should villages expand?**
A: When crowded, agents build roads to new settlements. Automatic expansion threshold.