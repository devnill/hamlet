# Domain Registry

current_cycle: 17

## Domains

### architecture
System architecture, technology choices, async patterns, MCP integration, module decomposition, hook script contracts, daemon lifecycle, settings CLI.
Files: domains/architecture/policies.md, decisions.md, questions.md

### visualization
Agent representation, world building, animations, ASCII iconography, UI layout, color schemes, rendering backends.
Files: domains/visualization/policies.md, decisions.md, questions.md

### data-model
State management, persistence, entity relationships, SQLite schema, write-behind patterns, inference engine state lifecycle.
Files: domains/data-model/policies.md, decisions.md, questions.md

### terrain
Terrain generation, biome regions, water features, forest clustering, terrain configuration, map viewer.
Files: domains/terrain/policies.md, decisions.md, questions.md

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
- Terrain parameter exposure gap (cycle 012): Ten TerrainConfig parameters added in WI-254/255/256 are not in TERRAIN_PARAMS list for parameter panel. WI-252 acceptance criterion "Parameter panel displays all configurable terrain parameters with current values" not met. **Resolved in cycle 013** — WI-259 added all 10 missing parameters. See terrain Q-7.
- Settings CLI and daemon config reload (cycle 014): min_village_distance promoted to Settings (data-model D-12), settings get/set CLI added with dot notation for terrain sub-keys (architecture D-25), periodic daemon reload at 30s with restart-required fields excluded (architecture D-27, D-28, P-13). Three pre-existing bugs in service.py/daemon.py fixed as rework (architecture D-29, P-14). Spans architecture (CLI, daemon lifecycle) and data-model (Settings field).
- Notcurses graphical backend (cycle 015): Optional notcurses renderer added (WI-267–274). ASCII/Textual remains universal fallback; notcurses selected by --renderer flag or settings.renderer. Core subsystems untouched (architecture D-30). Three gaps carried forward: ROAD symbol missing from SymbolConfig (visualization Q-10, crash path), terrain endpoint not connected to NotcursesApp (visualization Q-11, deferred), legend toggle no-op (visualization Q-15). Architecture.md component map not updated to include gui/ module (architecture Q-20). Spans architecture (rendering layer boundary, optional dependency pattern) and visualization (new backend, policies, design conventions).
- Notcurses → Kitty pivot (cycle 016): notcurses 3.0.17 segfaults with Python 3.14 on ARM64 macOS due to mimalloc allocator corruption in the internal input_thread. All mitigations failed. The notcurses backend (gui/notcurses/ and all associated tests) was deleted entirely (WI-275) and replaced with a pure Python Kitty graphics protocol implementation (WI-276–282). Design Constraint 1 updated with pure Python requirement; GP-3 updated to reference Kitty. All five cycle 015 gaps (visualization Q-10, Q-11, Q-12, Q-15, architecture Q-20) resolved within the pivot scope. Sprite pipeline exists in code but is not wired end-to-end — no PNG assets exist and system degrades correctly to character rendering (visualization Q-16, Q-20). Three sprite-pipeline defects carried forward (visualization Q-17, Q-18, Q-19). Process Constraint 3 inconsistency identified (architecture Q-21). Spans architecture (pure Python rendering constraint, terminal routing D-32) and visualization (backend replacement, P-6 amended, D-16 through D-20).
- Kitty viewer runtime crash fix (cycle 017): `hamlet view --renderer kitty` crashed post-cycle-016 with `'dict' object has no attribute 'position'`. Root cause: StateFetcher returned raw JSON dicts; KittyApp expected typed dataclasses. Fixed by parsing at the fetch layer (WI-283) and removing defensive dict patterns from app.py (WI-284). Integration tests added using live-daemon fixtures, mocking only the HTTP transport boundary (WI-285, architecture P-15). Manual smoke test confirmed working (WI-286). Three new open questions: agent @ symbol assertion missing (visualization Q-21), empty-state pipeline test absent (visualization Q-22), TUI/Kitty degradation asymmetry (visualization Q-23). Parse helpers cross-module import risk flagged by all three reviewers (architecture Q-22). Spans architecture (module decomposition, integration test policy P-15) and visualization (Kitty render pipeline correctness, D-21 through D-23).
