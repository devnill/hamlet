# Domain Registry

current_cycle: 9

## Domains

### architecture
System architecture, technology choices, async patterns, MCP integration, module decomposition, hook script contracts.
Files: domains/architecture/policies.md, decisions.md, questions.md

### visualization
Agent representation, world building, animations, ASCII iconography, UI layout, color schemes.
Files: domains/visualization/policies.md, decisions.md, questions.md

### data-model
State management, persistence, entity relationships, SQLite schema, write-behind patterns, inference engine state lifecycle.
Files: domains/data-model/policies.md, decisions.md, questions.md

## Cross-Cutting Concerns
- Performance: Debouncing for high event throughput, 30 FPS render loop
- Graceful degradation: Silent failure on errors, no blocking
- Modularity: Iterable mappings for tool-to-structure, agent type inference
- Hook script defect cluster (cycle 003): Hooks never read stdin, use fabricated environment variables, omit required fields. Root cause of agent inference, work unit accumulation, project identity, and structure progression all being non-functional. Highest priority for cycle 004. Spans architecture (contract), data-model (inference state), and visualization (agent types always GENERAL). **Resolved in cycle 004** — all four hooks rewritten (WI-113).
- Notification/Stop pipeline (cycles 004–006): Both non-tool hook types fire correctly. Typed InternalEvent fields (notification_message, stop_reason) were added in cycle 005 (WI-120). Downstream consumption added in cycle 006 (WI-122): engine logs both fields, event log shows prefixed summaries. **Extraction and logging resolved.** Behavioral differentiation on stop_reason remains deferred (architecture Q-13). Spans architecture and data-model.
- Dual color maps (cycles 005–006): TYPE_COLORS (inference/types.py) and AGENT_BASE_COLORS (animation.py) were independent authoritative maps. **Resolved in cycle 006** — AGENT_BASE_COLORS removed by WI-123; TYPE_COLORS is now the sole color authority. See visualization D-11, P-5.
- Symbol removal without test-tree audit (cycles 005–006): Two consecutive cycles deleted or removed a symbol from src/ without checking tests/ for imports. Cycle 005: inference/colors.py deletion broke test_zombie_detection.py. Cycle 006: AGENT_BASE_COLORS removal broke test_animation.py. Both caught and fixed during review. Architecture P-10 amended in cycle 006 to broaden scope from module deletion to any symbol removal. Spans architecture (process) and visualization (affected tests).
- tool_output schema for Bash strings (cycles 004–006): EVENT_SCHEMA constrains tool_output to object|null; Bash tool returns plain strings which are silently discarded. Pre-existing, explicitly deferred each cycle. Architecture Q-10 remains open.
- Full hook coverage (cycle 008): 11 new hook scripts added (WI-179, WI-180), bringing total to 15 hook types. hooks.json, event schema, daemon handler, and install.py all updated. Two cross-cutting issues found and fixed during review: WI-180 hooks missing os.chdir (architecture P-6 amended), HOOK_SCRIPTS dict incomplete (architecture P-11 established). Test coverage for new hooks remains absent (architecture Q-15). Spans architecture (hook contracts, install sync) and data-model (new event handling branches).
