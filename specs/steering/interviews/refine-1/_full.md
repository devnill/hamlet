# Refinement Interview — 2026-03-16

**Context:** Post-review correction. Cycle 002 comprehensive review returned Fail verdict with 4 critical findings blocking application functionality and 20+ significant findings. This refinement addresses all critical/significant findings and adds new capabilities.

---

**Q: Should PLANNER be a valid agent type? It's in `world_state/types.py` but not in `inference/types.py`, causing type conversion failures.**

A: Yes, it should be a valid type.

---

**Q: The hook-to-MCP protocol mismatch is critical. Hooks use HTTP POST to localhost:8080, but the MCP server uses stdio transport. Should we add an HTTP endpoint to the server, or change hooks to use MCP stdio?**

A: HTTP makes the most sense here. The user was also curious about the architecture pattern — hooks are fire-and-exit processes, so they can't maintain a persistent stdio channel. HTTP POST is the correct model for ephemeral callers. Adding an HTTP listener to MCPServer alongside the existing stdio transport.

---

**Q: Should `Agent.project_id` be persisted to SQLite? It's currently in-memory only and empty after restart.**

A: Yes, make sure this ends up in the database.

---

**Q: TESTER agent type — automatic inference from tool patterns, or manual-only for MVP?**

A: Inference is a good option. Also: use the small fast model (usually haiku, but configurable via Settings override) to ask the LLM for a summary of what's being done. Doesn't need to be overengineered.

---

**Summary of decisions:**
- PLANNER added to inference/types.py (7-member enum matching world_state)
- HTTP endpoint added to MCPServer (aiohttp on port 8080)
- Agent.project_id persisted via SQLite migration v2
- TESTER inference: Bash content inspection (pytest/unittest keywords)
- LLM summarization: ActivitySummarizer using anthropic SDK, configurable model (default haiku), max 20 tokens, 5s timeout, graceful degradation
- New dependencies: aiohttp, anthropic
