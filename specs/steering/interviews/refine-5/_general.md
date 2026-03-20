---
## Refinement Interview — 2026-03-19

**Context**: Cycle 4 achieved convergence (0 critical, 0 significant findings). This refinement transitions hooks from manual inline configuration to the plugin system and registers hamlet in the plugin marketplace.

**Q: Do the guiding principles still hold?**
A: Yes, all principles unchanged.

**Q: What changes do you want to make?**
A: Two things: (1) remove the manually created hooks in ~/.claude/ and switch to testing the plugin hooks instead; (2) add hamlet to the plugin marketplace at ~/code/claude-marketplace.

**Q: Should the plugin hooks be async (non-blocking)?**
A: Yes, async: true — same behavior as the current inline hooks — unless there's a compelling reason not to. There isn't one.

**Scope boundary**: Hook script implementations (pre_tool_use.py, post_tool_use.py, notification.py, stop.py), MCP server, daemon, TUI, and all world-state logic are unchanged. This cycle touches only hooks.json, ~/.claude/settings.json, and the marketplace manifest.
