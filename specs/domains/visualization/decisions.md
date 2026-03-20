# Decisions: Visualization

## D-1: ASCII-Only Rendering
- **Decision:** Use ASCII characters for all entities and terrain. No tile graphics.
- **Rationale:** Terminal UI, follows Dwarf Fortress/ADOM/Nethack conventions, easy to iterate.
- **Assumes:** Target terminal supports Unicode block characters for progress.
- **Source:** steering/interview.md
- **Status:** settled

## D-2: Agent Type Colors
- **Decision:** Researcher=cyan, Coder=yellow, Executor=green, Architect=magenta, Tester=blue, General=white.
- **Rationale:** Roguelike conventions, deterministic from inferred type, visually distinct.
- **Source:** plan/architecture.md
- **Status:** superseded by D-4

## D-3: Structure Evolution Path
- **Decision:** Structures progress through stages: foundation → frame → complete. Materials evolve: wood → stone → brick.
- **Rationale:** Visual progression indicates work investment, matches roguelike crafting metaphors.
- **Source:** plan/modules/world-state.md
- **Status:** settled

## D-4: EXECUTOR color changed to red; PLANNER to dark_green
- **Decision:** EXECUTOR changed from cyan/green to red in both `TYPE_COLORS` and `AGENT_COLORS`. PLANNER changed from green to dark_green. Amends P-1.
- **Rationale:** EXECUTOR's prior green color collided with zombie tint (GP-6 violation). PLANNER's green also collided. New colors restore visual distinctness.
- **Source:** archive/cycles/003/decision-log.md (D47)
- **Policy:** Amends visualization P-1
- **Status:** settled
- **Note:** The legend overlay (`legend.py`) was not updated to reflect this change — still shows EXECUTOR as green. Tracked in Q-3.

## D-5: Legend EXECUTOR color is incorrect
- **Decision:** `legend.py` renders EXECUTOR as green, but the actual render color is now red (per D-4). This is a known display bug entering Cycle 004.
- **Rationale:** WI-107 changed the color maps but did not update the legend overlay.
- **Source:** archive/cycles/003/gap-analysis.md (G8)
- **Status:** superseded by D-6

## D-6: EXECUTOR legend entry corrected to red
- **Decision:** `legend.py` EXECUTOR entry updated from green to red, matching `symbols.py` and `inference/types.py`. The `animation.py` AGENT_BASE_COLORS table was not updated in the same work item and still omits EXECUTOR.
- **Rationale:** Aligns legend with the canonical EXECUTOR color established in D-4.
- **Source:** archive/cycles/004/decision-log.md (D13)
- **Status:** settled
- **Note:** animation.py omission tracked in Q-5.

## D-7: PLANNER agent type marked reserved — no inference rule added
- **Decision:** `AgentType.PLANNER` remains in both enum modules with colors assigned but has no `TYPE_RULES` entry. A comment was added in `inference/rules.py` documenting it as reserved. No clear tool-use heuristic identified.
- **Rationale:** No distinct tool-usage pattern reliably distinguishes planning activity from general activity.
- **Source:** archive/cycles/004/decision-log.md (D3)
- **Status:** settled

## D-8: EXECUTOR added to animation.py AGENT_BASE_COLORS; PLANNER added to legend
- **Decision:** WI-119 added `AgentType.EXECUTOR: "red"` to `AGENT_BASE_COLORS` in `animation.py`, closing the omission from D-6. PLANNER was also added to `LegendOverlay` with `dark_green` color.
- **Rationale:** EXECUTOR was the most common inferred type. Its absence from AGENT_BASE_COLORS caused all EXECUTOR agents to render with the white fallback color during zombie animation. PLANNER legend entry documents the reserved type before its inference rule exists.
- **Source:** archive/cycles/005/decision-log.md (D2); archive/cycles/005/summary.md (WI-119)
- **Status:** settled

## D-9: inference/colors.py deleted as dead code
- **Decision:** `inference/colors.py` (exporting `blend_color` and `get_display_color`) was deleted. No callers exist in `src/hamlet/`. Zombie color logic is handled by `simulation/animation.py` exclusively.
- **Rationale:** Dead code removed per GP-4 (modularity). The file was from a superseded approach to zombie rendering.
- **Assumes:** Caller audit was performed against `src/hamlet/` only. The test tree was not audited — see D-10 and architecture P-10.
- **Source:** archive/cycles/005/decision-log.md (D3); archive/cycles/005/code-quality.md (C1)
- **Status:** settled

## D-10: Dual color map deduplication deferred (TYPE_COLORS vs AGENT_BASE_COLORS)
- **Decision:** `TYPE_COLORS` in `inference/types.py` and `AGENT_BASE_COLORS` in `animation.py` both remain as independent authoritative color maps. Deduplication deferred because resolving requires unifying the `AgentType` enums used by each module.
- **Rationale:** WI-119 was scoped to visualization fixes; enum unification is a larger architectural change. Both tables currently agree on all values.
- **Source:** archive/cycles/005/decision-log.md (D4); archive/cycles/005/gap-analysis.md (SG3); archive/cycles/005/code-quality.md (M1)
- **Status:** superseded by D-11
- **Note:** Resolved in cycle 006 by WI-123. AGENT_BASE_COLORS removed entirely.

## D-11: AGENT_BASE_COLORS removed; animation.py imports TYPE_COLORS as sole color authority
- **Decision:** `AGENT_BASE_COLORS` deleted from `animation.py`. `animation.py` imports `TYPE_COLORS` and `InfAgentType` from `inference/types.py` and uses a value-based round-trip (`InfAgentType(agent.inferred_type.value)`) to look up colors. `TYPE_COLORS` in `inference/types.py` is now the single source of truth for agent colors.
- **Rationale:** Dual independent color tables created silent divergence risk — any future color change or new agent type had to be applied to both with no enforcement. Consolidation satisfies GP-3 (thematic consistency) and GP-4 (modularity).
- **Source:** archive/cycles/006/decision-log.md (D-E8, D-R2, CR2); archive/cycles/006/spec-adherence.md
- **Status:** settled
