# Questions: Visualization

## Q-1: Animation Timing Constants
- **Question:** What are the exact animation timings (spin cycle speed, pulse frequency, celebration duration)?
- **Source:** steering/interview.md
- **Impact:** Affects perceived polish. Designer judgment deferred to implementation.
- **Status:** open
- **Reexamination trigger:** User feedback on visual feel.

## Q-2: Structure Type Mapping
- **Question:** Complete mapping of tools to structure types. Current mapping is placeholder (Read→library, Write→workshop, Bash→forge).
- **Source:** steering/interview.md
- **Impact:** Determines what gets built. Mapping is modular and can be iterated.
- **Status:** open
- **Reexamination trigger:** Visual variety feedback.

## Q-3: PLANNER agent type — add inference rule or mark reserved?
- **Question:** `AgentType.PLANNER` is defined in both enum modules with colors assigned, but `TYPE_RULES` has no entry that can produce PLANNER. Should a PLANNER inference rule be added (e.g., high ratio of planning/coordination tools), or should the type be explicitly documented as reserved for future use?
- **Source:** archive/cycles/003/code-quality.md (M2); archive/cycles/003/spec-adherence.md (S2); archive/cycles/003/summary.md
- **Impact:** PLANNER is currently dead code in the inference pipeline. Future maintainers may be confused by its presence without a rule.
- **Status:** resolved
- **Resolution:** PLANNER marked as reserved with no inference rule. Comment added in inference/rules.py. See D-7.
- **Resolved in:** cycle 004

## Q-4: Viewport center persistence priority
- **Question:** The architecture specifies `world_metadata` stores `viewport_center_x/y` for cross-restart persistence, but nothing writes or reads these values. Should viewport persistence be addressed in Cycle 004, or is resetting to first village center acceptable for MVP?
- **Source:** archive/cycles/003/gap-analysis.md (G6); archive/cycles/003/summary.md
- **Impact:** Users lose scroll position on every restart. On a large multi-village world this is a significant usability regression.
- **Status:** resolved
- **Resolution:** Viewport center persistence deferred to post-MVP. Resetting to first village center is acceptable for now.
- **Resolved in:** cycle 004

## Q-5: EXECUTOR absent from animation.py AGENT_BASE_COLORS
- **Question:** `AGENT_BASE_COLORS` in `simulation/animation.py` omits `AgentType.EXECUTOR`. Fallback produces white during zombie animation instead of red. EXECUTOR is the most common inferred type. Should `AgentType.EXECUTOR: "red"` be added?
- **Source:** archive/cycles/004/code-quality.md (S1); archive/cycles/004/spec-adherence.md (D2, N2)
- **Impact:** All EXECUTOR agents are visually indistinguishable from GENERAL agents during animation. Violates P-5.
- **Status:** resolved
- **Resolution:** `AgentType.EXECUTOR: "red"` added to `AGENT_BASE_COLORS` in animation.py by WI-119. See D-8.
- **Resolved in:** cycle 005

## Q-6: PLANNER color inconsistent across color tables
- **Question:** PLANNER is `"dark_green"` in `inference/types.py` and `symbols.py` but `"green"` in `animation.py` AGENT_BASE_COLORS. When a PLANNER inference rule is eventually added, zombie pulse will use wrong base color.
- **Source:** archive/cycles/004/spec-adherence.md (N1)
- **Impact:** Latent color inconsistency; surfaces only when PLANNER inference rule is added.
- **Status:** resolved
- **Resolution:** `AGENT_BASE_COLORS` was removed entirely by WI-123 (cycle 006). `animation.py` now imports `TYPE_COLORS` from `inference/types.py`, eliminating the inconsistency source. See D-11.
- **Resolved in:** cycle 006

## Q-7: PLANNER absent from LegendOverlay
- **Question:** `LegendOverlay` lists six agent types but omits PLANNER. Should PLANNER be added to the legend now (documents the reserved type) or wait until an inference rule is added?
- **Source:** archive/cycles/004/code-quality.md (M1); archive/cycles/004/decision-log.md (OQ7)
- **Impact:** When PLANNER inference rule is added, agents will render with an unlisted color.
- **Status:** resolved
- **Resolution:** PLANNER added to LegendOverlay with dark_green color by WI-119. Documents the reserved type before its inference rule exists. See D-8.
- **Resolved in:** cycle 005

## Q-8: inference/colors.py potentially dead code
- **Question:** `inference/colors.py` exports `blend_color` and `get_display_color` but is not referenced in any spec and may not be called from the TUI render path. Zombie color logic is split between this module (`"green"`) and `simulation/animation.py` (`"bright_green"`). Is this module dead code from a superseded approach?
- **Source:** archive/cycles/004/spec-adherence.md (U1)
- **Impact:** If dead, misleads future developers about the zombie rendering path.
- **Status:** resolved
- **Resolution:** Confirmed dead. `inference/colors.py` deleted by WI-119. Zombie rendering handled exclusively by `simulation/animation.py`. See D-9.
- **Resolved in:** cycle 005

## Q-9: Dual authoritative color maps will diverge silently
- **Question:** `TYPE_COLORS` in `inference/types.py` and `AGENT_BASE_COLORS` in `animation.py` are both in-use, independent color maps with no shared source. Any future color change or new agent type must be applied to both. If one table is updated without the other, stored agent color diverges from rendered color with no error. Should these be consolidated to a single source of truth?
- **Source:** archive/cycles/005/decision-log.md (D4, OQ5, CR2); archive/cycles/005/gap-analysis.md (SG3); archive/cycles/005/code-quality.md (M1)
- **Impact:** Silent visual bugs when color changes are applied to one table but not the other. Adding a new AgentType requires two edits with no enforcement.
- **Status:** resolved
- **Resolution:** `AGENT_BASE_COLORS` removed from `animation.py`. `animation.py` imports `TYPE_COLORS` from `inference/types.py` as sole color authority. See D-11.
- **Resolved in:** cycle 006
