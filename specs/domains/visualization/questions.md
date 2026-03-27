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

## Q-10: StructureType.ROAD has no symbol in SymbolConfig — crash path in renderer
- **Question:** `StructureType.ROAD` existed in `world_state/types.py` but was absent from `StructureVisual.symbols` in `gui/symbol_config.py`. Roads are auto-generated by village growth. The renderer accessed the symbol config dict directly (no fallback), so the first road in any active session would produce a KeyError.
- **Source:** archive/cycles/015/spec-adherence.md (M2); archive/cycles/015/decision-log.md (OQ-2, CR1)
- **Impact:** Guaranteed crash in renderer once any village expands enough to generate roads.
- **Status:** resolved
- **Resolution:** Fixed in cycle 016 rework. renderer.py uses `.get(struct.type, "?")` fallback; test_road_renders passes.
- **Resolved in:** cycle 016

## Q-11: KittyApp / NotcursesApp does not integrate with daemon terrain endpoint
- **Question:** The graphical viewer constructed `terrain_data` as an empty dict in the render loop. The daemon exposes terrain via `GET /hamlet/terrain/bounds/...`. Should the graphical viewer be connected to the terrain endpoint?
- **Source:** archive/cycles/015/gap-analysis.md (G1); archive/cycles/015/decision-log.md (OQ-1)
- **Impact:** Terrain features (water, mountains, forests) were invisible in the graphical viewer.
- **Status:** resolved
- **Resolution:** Fixed in cycle 016. `StateFetcher.fetch_snapshot` now fetches `/hamlet/terrain/bounds/...`.
- **Resolved in:** cycle 016

## Q-12: SpriteSheet references silently invalidated after cleanup
- **Question:** `SpriteSheet` was a mutable dataclass; `cleanup()` set `sheet.ncvisual = None`. Callers holding a reference could blit a None visual after cleanup without any error.
- **Source:** archive/cycles/015/code-quality.md (M1); archive/cycles/015/decision-log.md (OQ-3, CR2)
- **Impact:** Was dormant while no sprite PNGs existed; would become an active hazard when sprites were added.
- **Status:** resolved
- **Resolution:** Fixed in cycle 016. `SpriteHandle` is now a frozen dataclass; `SpriteManager.is_uploaded(image_id)` is the canonical upload-state check. Mutation-after-cleanup cannot occur on a frozen handle. See D-18.
- **Resolved in:** cycle 016

## Q-13: destroy_plane return value not checked in notcurses bindings
- **Question:** `ncplane_destroy` returned an int (0 on success) but the ctypes wrapper discarded the return value. Silent failure on plane destruction could leak native plane resources.
- **Source:** archive/cycles/015/code-quality.md (M2); archive/cycles/015/decision-log.md (OQ-4)
- **Impact:** Plane resource leaks on destroy failure with no diagnostic.
- **Status:** resolved
- **Resolution:** Notcurses deleted entirely in cycle 016 (WI-275). The ctypes bindings no longer exist. See D-16.
- **Resolved in:** cycle 016

## Q-14: No sprite PNG assets — SNES visual experience cannot be evaluated
- **Question:** The `assets/` directory contains only `README.md`. No PNG sprites exist. The SNES/16-bit visual experience described in GP-3 cannot be evaluated until sprite files are created.
- **Source:** archive/cycles/015/gap-analysis.md (G2); archive/cycles/015/decision-log.md (D12, OQ-5, CR2)
- **Impact:** The graphical backend currently produces character-mode rendering identical to the ASCII backend at FAR zoom. Sprite infrastructure is complete and validated; only the art assets are missing.
- **Status:** deferred
- **Deferred rationale:** Absence is by design (D-15). System degrades gracefully. Sprite authoring is a separate activity from renderer infrastructure delivery. Carried into cycle 016 as OQ-2.

## Q-15: Legend toggle is a no-op in graphical viewer
- **Question:** The `/` keybinding in the graphical viewer toggled `self._show_legend` but no legend rendering code existed. Pressing `/` had no visible effect.
- **Source:** archive/cycles/015/gap-analysis.md (G3); archive/cycles/015/decision-log.md (OQ-6, CR3)
- **Impact:** Users could not view the terrain/structure legend in the graphical viewer.
- **Status:** resolved
- **Resolution:** Fixed in cycle 016. `KittyApp._render_legend()` renders a bordered box with key bindings and symbols; test exists.
- **Resolved in:** cycle 016

## Q-16: Sprite upload pipeline not wired — sprites never display
- **Question:** `SpriteManager.get_upload_sequence()` is never called from `KittyApp` or `KittyRenderer`. The renderer checks `is_uploaded()` (always False) and falls back to character rendering. When sprite PNG assets are added, someone must wire `get_upload_sequence` into the render loop before sprites will appear.
- **Source:** archive/cycles/016/decision-log.md (OQ-1); archive/cycles/016/code-quality.md (S1); archive/cycles/016/gap-analysis.md (G1)
- **Impact:** Sprites never display at MEDIUM/CLOSE zoom regardless of asset availability. No runtime impact currently since no PNG assets exist, but wiring is required before sprite art work begins.
- **Status:** open
- **Reexamination trigger:** Before or during the first work item that adds sprite PNG assets.

## Q-17: SpriteHandle.uploaded field is always False and misleading
- **Question:** `SpriteHandle` is a frozen dataclass constructed with `uploaded=False`. The actual upload state is tracked in `SpriteManager._uploaded_ids`. The `uploaded` field is never True and misleads callers. `is_uploaded()` is the correct API. Should the field be removed?
- **Source:** archive/cycles/016/decision-log.md (OQ-3); archive/cycles/016/code-quality.md (M1)
- **Impact:** Callers checking `handle.uploaded` always see False, which is consistent with actual behavior but semantically wrong. Should be removed before the sprite pipeline is wired to avoid confusion.
- **Status:** open
- **Reexamination trigger:** Next sprites.py work item; must be resolved before sprite upload pipeline is wired (Q-16).

## Q-18: get_upload_sequence raises KeyError on stale handle after cleanup
- **Question:** After `SpriteManager.cleanup()` clears `_png_data`, calling `get_upload_sequence(handle)` with a retained handle raises `KeyError`. The method should return an empty string for graceful degradation.
- **Source:** archive/cycles/016/decision-log.md (OQ-4); archive/cycles/016/code-quality.md (M2)
- **Impact:** Crash after a cleanup/reload cycle. Fix is `self._png_data.get(handle.image_id)` with early return on None.
- **Status:** open
- **Reexamination trigger:** Next sprites.py work item or before sprite pipeline is wired (Q-16).

## Q-19: encode_image_display hardcodes placement_id p=1
- **Question:** The Kitty protocol uses `(image_id, placement_id)` pairs to uniquely identify placements. `encode_image_display` hardcodes `p=1`, meaning the same image displayed at two locations simultaneously will have the second placement replace the first.
- **Source:** archive/cycles/016/decision-log.md (OQ-5); archive/cycles/016/code-quality.md (M3)
- **Impact:** Multi-placement rendering of the same sprite (e.g., the same terrain tile in two viewport positions) is broken. Must be fixed when sprites are in active use.
- **Status:** open
- **Reexamination trigger:** When sprite rendering is activated (i.e., after Q-16 is resolved).

## Q-20: No sprite PNG assets — SNES visual experience not evaluable (continued from Q-14)
- **Question:** No PNG sprites exist in the Kitty backend assets directory. The SNES/16-bit visual experience described in GP-3 cannot be evaluated.
- **Source:** archive/cycles/016/decision-log.md (OQ-2); archive/cycles/016/gap-analysis.md (G2)
- **Impact:** The Kitty backend currently produces identical visual output to the ASCII backend at all zoom levels. Sprite infrastructure is complete; upload pipeline exists but is not wired (see Q-16).
- **Status:** deferred
- **Deferred rationale:** Sprite authoring is a separate activity from renderer infrastructure. System degrades gracefully to character rendering. Blocked on Q-16 and Q-17 being resolved first.

## Q-21: Agent @ symbol assertion missing from render pipeline integration test
- **Question:** Does `render_frame` produce agent `@` symbols in output when agents are present? The WI-285 acceptance criterion "output contains agent @ symbols" is not verified by any assertion. `test_render_frame_produces_terrain_symbols` checks terrain symbols only. An agent-symbol rendering regression would not be caught automatically.
- **Source:** archive/cycles/017/gap-analysis.md (G1); archive/cycles/017/decision-log.md (OQ-3)
- **Impact:** A bug that silently drops agent rendering would pass all 103 current Kitty tests. The fixture contains 2 agents; centering the viewport on their position should produce `@` in output.
- **Status:** open
- **Reexamination trigger:** Next work item touching `test_kitty_integration.py` or `KittyRenderer` render path.

## Q-22: No integration test covers empty agents/structures/villages through full pipeline
- **Question:** Does `fetch_snapshot()` followed by `render_frame()` handle empty lists without error when the daemon has no agents, structures, or villages? All integration tests use the full fixture; the fresh-install code path is untested.
- **Source:** archive/cycles/017/gap-analysis.md (G2); archive/cycles/017/decision-log.md (OQ-2)
- **Impact:** An empty-list crash (divide-by-zero, index error, or None dereference) in the renderer would affect all new users on first launch before any agent activity exists.
- **Status:** open
- **Reexamination trigger:** Next work item touching `test_kitty_integration.py` or Kitty renderer edge cases.

## Q-23: TUI per-category degradation is coarser than Kitty per-item degradation
- **Question:** `RemoteWorldState.refresh()` in the TUI path discards an entire category (all agents, or all structures, or all villages) when one item fails to parse. The Kitty `StateFetcher` uses `_try_parse` per item, so valid items survive when a neighbor is malformed. Should the TUI path be updated for consistency?
- **Source:** archive/cycles/017/spec-adherence.md (M1); archive/cycles/017/decision-log.md (OQ-6)
- **Impact:** With malformed data, TUI users lose all items of a type while Kitty users lose only the malformed item. The behavioral difference is invisible and undocumented. Not a regression from this cycle — the TUI path was out of scope for WI-283.
- **Status:** open
- **Reexamination trigger:** Next work item touching `tui/remote_world_state.py` or general graceful-degradation pass across rendering backends.
