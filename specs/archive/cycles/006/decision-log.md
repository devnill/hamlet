# Decision Log — Cycle 006

## Cycle Summary

Cycle 006 addressed the three significant open questions carried from Cycle 005: `notification_message` and `stop_reason` consumed nowhere downstream (OQ3, OQ4), dual authoritative color maps at risk of silent divergence (OQ5), and `find_config()` traversal colliding with the global `~/.hamlet/config.json` written by the install command (OQ2). All three work items passed their incremental reviews with minor rework. The final review found no critical or significant findings. One test-breakage pattern — deleting a symbol without auditing the test tree — recurred from Cycle 005 and was caught and fixed by the gap analyst during review.

---

## Planning Phase Decisions

### D-P1: All four Claude Code hook types implemented
- **When**: Planning — interview Q1 (2026-03-12)
- **Decision**: PreToolUse, PostToolUse, Notification, and Stop hooks are all implemented.
- **Rationale**: User stated "I want every single hook to be implemented, both for a variety of animations and maximum observability."
- **Implications**: Agent lifecycle (spawn, idle, zombie) must be inferred from hook patterns; no dedicated agent lifecycle hooks exist in Claude Code.

### D-P2: Python with Textual for TUI
- **When**: Planning — research recommendation, interview Q5 (2026-03-12)
- **Decision**: Python/Textual selected as the TUI and runtime framework.
- **Rationale**: Research found Textual to be async-native (aligns with MCP SDK requirements), supports hot reload for iteration, and has official Python MCP SDK integration. User approved: "Lets do it."
- **Alternatives considered**: Go/bubbletea, Rust/ratatui.
- **Implications**: All module code is Python 3.11+. asyncio is the concurrency model throughout.

### D-P3: Single persistent MCP server receiving events from multiple Claude Code sessions
- **When**: Planning — interview Q14 (2026-03-12)
- **Decision**: One MCP server process handles all sessions. Sessions connect via HTTP/JSON-RPC.
- **Rationale**: User specified: "multiple sessions must be able to call into the single tool."
- **Implications**: World state is shared across all active Claude Code sessions. MCP server must be a long-running process, not session-scoped.

### D-P4: SQLite for world state persistence
- **When**: Planning — interview Q14 (2026-03-12)
- **Decision**: SQLite stores all persistent world state (projects, villages, agents, structures, events).
- **Rationale**: User specified "SQLite is ideal." Write-behind queue pattern chosen to prevent blocking event processing.
- **Implications**: Crash recovery loses at most one checkpoint interval of events. Schema defined in architecture.md.

### D-P5: Visual interest prioritized over accuracy
- **When**: Planning — guiding principles (2026-03-12)
- **Decision**: When tradeoffs arise, choose the option that makes the screen more visually interesting (GP-1).
- **Rationale**: User stated "more work in claude code to yield a more visually interesting and frenetic screen."
- **Implications**: Debouncing is permitted for spam prevention, but overall event throughput drives visual activity.

### D-P6: Lean hook scripts — no business logic in client
- **When**: Planning — guiding principles and constraints (2026-03-12)
- **Decision**: Hook scripts extract minimal telemetry only. All inference and state management is server-side (GP-2, Constraint D4).
- **Rationale**: User stated "the client should be as lean as possible."
- **Implications**: Hook scripts use stdlib only. No retry logic, no local state.

### D-P7: Deterministic agent color from agent type
- **When**: Planning — interview Q8–Q9 (2026-03-12)
- **Decision**: Color assigned from a hash of agent type (GP-6, Constraint D7). A legend is available via menu.
- **Rationale**: User specified "deterministic" and "type makes the most sense."
- **Implications**: All agents of the same inferred type share a color. Zombie state overrides to greenish hue.

### D-P8: Project-based villages with global persistent map
- **When**: Planning — interview Q11–Q12 (2026-03-12)
- **Decision**: Each project maps to one village (GP-5, Constraint D6). Map persists across restarts. New projects create new villages.
- **Rationale**: User specified "a single codebase should be a single village that grows out" and "a global map that has lots of little villages."
- **Implications**: Project identity must be configured via `.hamlet/config.json` (project_id + project_name). Villages can expand and connect via roads.

### D-P9: Agent type inferred from tool usage patterns
- **When**: Planning — interview Q16 (2026-03-12)
- **Decision**: Agent type (researcher, coder, executor, etc.) inferred from frequency of tool calls over a sliding window. No dedicated type information in hooks.
- **Rationale**: Claude Code provides no agent type or agent identity in hook events. User accepted minimal processing.
- **Implications**: Inference accuracy improves with event volume. First call type defaults to GENERAL.

### D-P10: Tool-to-structure mappings are modular and iterable
- **When**: Planning — guiding principles (2026-03-12)
- **Decision**: Mappings from tool names to structure types defined in a data structure, not hardcoded logic (GP-4).
- **Rationale**: "It doesn't need to be a perfect mapping as long as the screen is visually interesting" and design "should be modular."
- **Implications**: `TOOL_TO_STRUCTURE` defined in `world_state/rules.py` as the single authoritative location (after WI-117).

### D-P11: Graceful degradation — discard events on failure
- **When**: Planning — guiding principles and constraints (2026-03-12)
- **Decision**: Hook scripts exit cleanly on MCP server unavailability. No retry, no blocking (GP-7, Constraint P2).
- **Rationale**: User stated "We can discard messages for now."
- **Implications**: At most one checkpoint interval of events lost on crash. Hook scripts use `sys.exit(0)` on all paths.

### D-P12: 30 FPS simulation loop, frame-based rendering
- **When**: Planning — architecture tension resolution (2026-03-12)
- **Decision**: Simulation runs on a timer at configurable tick rate (default 30 FPS). Events queued between frames, all processed each tick.
- **Rationale**: Balances visual interest goal (GP-1) with performance.

---

## Execution Phase Decisions

### D-E1: HookEvent fields sent flat in params, not nested under "data"
- **When**: Execution — Cycle 004 refinement planning (2026-03-16)
- **Decision**: Architecture.md updated to document flat field format in `params` as canonical.
- **Rationale**: Implementation sends fields flat; changing to nested would add cost with no functional benefit.
- **Implications**: EventProcessor reads `params` directly; validation schema validates flat fields.

### D-E2: PLANNER agent type marked reserved — no inference rule
- **When**: Execution — Cycle 004 refinement planning (2026-03-16)
- **Decision**: `PLANNER` marked reserved in `inference/rules.py`. No `TYPE_RULE` added.
- **Rationale**: No tool pattern reliably distinguishes planner agents from general agents.
- **Implications**: PLANNER agents will not be inferred.

### D-E3: Viewport center persistence deferred
- **When**: Execution — Cycle 004 refinement planning (2026-03-16)
- **Decision**: Deferred. Viewport resets to first village center on restart.
- **Rationale**: Acceptable for MVP; critical path was hook script correctness and village mechanics.

### D-E4: EXECUTOR color set to red
- **When**: Execution — WI-107 (Cycle 003 refinement, 2026-03-16)
- **Decision**: EXECUTOR color changed to red in `TYPE_COLORS` and `tui/symbols.py`. PLANNER changed to dark_green.
- **Rationale**: RESEARCHER and EXECUTOR both mapped to cyan — collision. EXECUTOR and zombie both mapped to green — collision.
- **Implications**: Tests asserting EXECUTOR=cyan or EXECUTOR=green required updating.

### D-E5: `inference/colors.py` deleted as dead code
- **When**: Execution — WI-119 (Cycle 005 refinement, 2026-03-16)
- **Decision**: `inference/colors.py` (containing `blend_color` and `get_display_color`) deleted entirely.
- **Rationale**: No callers in `src/hamlet/`. GP-4 — dead code removed promptly.
- **Implications**: `tests/test_zombie_detection.py` imported `blend_color` — import failure at collection. Fixed during Cycle 005 review. Pattern recurred in Cycle 006 (see D-E8).

### D-E6: Hook server URL written to global config by install command
- **When**: Execution — Cycle 005 refinement, WI-121 (2026-03-16)
- **Decision**: `install_command` writes `server_url` to `~/.hamlet/config.json`. Hook scripts read `server_url` via `find_server_url()`.
- **Rationale**: Satisfies GP-11 (low-friction setup). Full fix chosen over targeted port substitution.
- **Implications**: Introduced a `find_config()` traversal side-effect fixed in Cycle 006 via WI-124.

### D-E7: `notification_message` and `stop_reason` consumed in engine and event log (WI-122)
- **When**: Execution — Cycle 006 (2026-03-16)
- **Decision**: `engine._handle_notification()` logs `notification_message` when non-None. `engine._handle_stop()` logs `stop_reason` when non-None. `manager.handle_event()` builds event log summary unconditionally using `or ''` fallback.
- **Rationale**: Closes OQ3 and OQ4 from Cycle 005. Fields extracted in WI-120 but consumed nowhere.
- **Implications**: Notification and Stop content now appears in event log. Behavioral differentiation on `stop_reason` value remains deferred (see OQ1).

### D-E8: `animation.py` uses `TYPE_COLORS` — `AGENT_BASE_COLORS` removed (WI-123)
- **When**: Execution — Cycle 006 (2026-03-16)
- **Decision**: `AGENT_BASE_COLORS` deleted from `animation.py`. `animation.py` imports `TYPE_COLORS` and `InfAgentType` from `inference/types.py`.
- **Rationale**: Closes OQ5 from Cycle 005. Dual tables created silent divergence risk on any future color change.
- **Implications**: Broke `tests/test_animation.py` at import. Fixed during review (see D-R2). Stale EXECUTOR assertion also corrected.

### D-E9: `find_config()` skips configs lacking `project_id` key (WI-124)
- **When**: Execution — Cycle 006 (2026-03-16)
- **Decision**: Guard `if "project_id" not in data: continue` added in all four hook scripts.
- **Rationale**: Closes OQ2 from Cycle 005. `~/.hamlet/config.json` contains `server_url` but no `project_id`, causing home directory name to appear as project name.
- **Implications**: Global `~/.hamlet/config.json` is now transparent to project config lookup.

### D-E10: Replace `data.get("project_id", _cwd_hash())` with `data["project_id"]` (WI-124 rework)
- **When**: Execution — Cycle 006, incremental review M1 (2026-03-16)
- **Decision**: `.get()` fallback replaced with direct key access in all four hook scripts.
- **Rationale**: The `if "project_id" not in data: continue` guard guarantees key presence. The fallback was dead code.
- **Implications**: None functionally. Removes a misleading code pattern.

---

## Review Phase Decisions

### D-R1: `handle_event()` summary uses unconditional hook-type routing with `or ''` fallback (WI-122 rework)
- **When**: Review — Cycle 006 incremental review, WI-122 S1 (2026-03-16)
- **Decision**: Summary branches changed from field-presence guards to unconditional hook-type routing with `or ''` fallback.
- **Rationale**: Field-presence guard meant a Notification event with empty message produced no "Notification:" prefix.
- **Implications**: All Notification and Stop events produce a correctly-prefixed summary.

### D-R2: Fix `test_animation.py` broken import during review (gap-analysis SG1)
- **When**: Review — Cycle 006 gap analysis (2026-03-16)
- **Decision**: `test_animation.py` updated during review: `TYPE_COLORS` and `InfAgentType` imported from `hamlet.inference.types`. `AGENT_BASE_COLORS` references replaced. EXECUTOR assertion corrected from "white" to "red".
- **Rationale**: WI-123 deleted `AGENT_BASE_COLORS` without auditing the test tree. Same deletion-without-test-audit pattern as Cycle 005.
- **Implications**: Test suite passes for animation module. Pattern flagged as recurring process gap.

### D-R3: Defer `stop_reason` behavioral differentiation (gap-analysis MG1)
- **When**: Review — Cycle 006 gap analysis (2026-03-16)
- **Decision**: Deferred. "stop" and "tool" values receive identical treatment in `_handle_stop()`.
- **Rationale**: Behavioral differentiation requires a design decision on interrupted-session state semantics.
- **Implications**: Zombie detection handles both via TTL eviction regardless of stop reason.

### D-R4: Defer `tool_output` schema plain-string Bash fix (gap-analysis MG2, pre-existing)
- **When**: Review — Cycle 006 gap analysis (2026-03-16)
- **Decision**: Deferred again. `tool_output` schema continues to require object type; Bash string output is discarded.
- **Rationale**: Not targeted in Cycle 006 scope.
- **Implications**: Bash-heavy agents contribute no work units to forge structures.

---

## Open Questions

### OQ1: `stop_reason` logs but does not branch behavior
- **Question**: Should "tool" (mid-tool interruption) and "stop" (clean termination) produce different agent state transitions?
- **Source**: Gap-analysis MG1, Cycle 006; carried from Cycle 005 OQ4 (partial resolution: field now logged).
- **Impact**: Interrupted sessions accumulate stale `pending_tools` entries until zombie TTL fires.
- **Consequence of inaction**: Stale pending tools delay accurate agent state reflection by up to `ZOMBIE_THRESHOLD_SECONDS`.

### OQ2: `tool_output` schema rejects plain-string Bash responses
- **Question**: Should the validation schema widen `tool_output` to `["object", "string", "null"]`, or should `post_tool_use.py` wrap string responses in a dict?
- **Source**: Gap-analysis MG2, Cycle 006; pre-existing from Cycles 004 and 005.
- **Impact**: Every Bash `PostToolUse` event with string output is silently discarded. Forge structures are never built from Bash activity.
- **Consequence of inaction**: EXECUTOR-type agents contribute no construction progress to the world.

### OQ3: `handle_event()` uses string comparison instead of enum identity
- **Question**: Should `manager.handle_event()` compare `event.hook_type == HookType.Notification` (enum identity) rather than `event.hook_type.value == "Notification"` (string)?
- **Source**: Code-quality M1, Cycle 006.
- **Impact**: If a `HookType` enum value is renamed, the Notification and Stop branches silently fall through to the else branch.
- **Consequence of inaction**: Two dispatch sites diverge in idiom; future HookType renaming produces silent wrong summaries.

### OQ4: Repeated pattern — symbol deletion does not audit the test tree
- **Question**: Should the execution process include an explicit step requiring grep of `tests/` for any symbol being deleted before completing a work item?
- **Source**: Gap-analysis SG1, Cycle 006; Decision D-E5, Cycle 005; both cycles broke a test file at collection.
- **Impact**: Each recurrence silently disables all tests in the affected file until caught by a reviewer.
- **Consequence of inaction**: A behavioral regression could go undetected until a comprehensive review.

### OQ5: Viewport center not persisted across restarts
- **Question**: Should the viewport center position be saved to `world_metadata` in SQLite and restored on startup?
- **Source**: Cycle 004 refinement planning (deferred); Cycle 005 decision-log D8.
- **Impact**: Users lose viewport position on every restart.
- **Consequence of inaction**: Multi-village maps become increasingly inconvenient to navigate after restarts.

---

## Cross-References

### CR1: Symbol deletion without test tree audit — recurring process gap
- **Code review**: No finding (not a code correctness issue within the changed files).
- **Spec review**: No related finding.
- **Gap analysis**: SG1 — `test_animation.py` failed at import after WI-123 removed `AGENT_BASE_COLORS`.
- **Connection**: Second consecutive cycle in which a symbol was deleted from `src/hamlet/` without checking `tests/`. Cycle 005 deleted `inference/colors.py` and broke `test_zombie_detection.py`. Cycle 006 WI-123 deleted `AGENT_BASE_COLORS` and broke `test_animation.py`. OQ4 surfaces this as a process question.

### CR2: Color map consolidation — three cycles to full resolution
- **Code review**: Confirmed value-based round-trip `InfAgentType(agent.inferred_type.value)` is safe for all 7 AgentType members after WI-123.
- **Spec review**: Confirmed GP-3 and GP-4 satisfied — `TYPE_COLORS` is the single source of truth. `AGENT_BASE_COLORS` absent from entire source tree.
- **Gap analysis**: SG1 caught the test breakage introduced by the consolidation.
- **Connection**: OQ5 from Cycle 005 is fully resolved by D-E8 and D-R2 together. Three complementary reviewer perspectives were needed to confirm complete resolution.

### CR3: `notification_message` and `stop_reason` — extraction-then-consumption across two cycles
- **Code review**: Confirmed event log shows correctly prefixed summary for Notification and Stop events. Also identified string-vs-enum dispatch inconsistency (M1, now OQ3).
- **Spec review**: Confirmed GP-7 exception boundaries respected, GP-8 satisfied by unconditional routing.
- **Gap analysis**: MG1 — `stop_reason` logged but never branches behavior; behavioral differentiation deferred as OQ1.
- **Connection**: OQ3 and OQ4 from Cycle 005 are partially resolved. `notification_message` content now reaches the event log (OQ3 closed). `stop_reason` is logged but does not alter state transitions (OQ4 partially closed, differentiation deferred).
