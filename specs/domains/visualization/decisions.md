# Decisions: Visualization

## D-1: ASCII-Only Rendering
- **Decision:** Use ASCII characters for all entities and terrain. No tile graphics.
- **Rationale:** Terminal UI, follows Dwarf Fortress/ADOM/Nethack conventions, easy to iterate.
- **Assumes:** Target terminal supports Unicode block characters for progress.
- **Source:** steering/interview.md
- **Status:** superseded by D-12

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

## D-12: ASCII rendering is the universal fallback; optional graphical backend selected by renderer setting
- **Decision:** ASCII/Textual rendering remains the default and universal fallback. A graphical backend is an opt-in renderer selected by `--renderer` CLI flag or `settings.renderer` field. `"auto"` detects terminal capability at runtime.
- **Rationale:** Preserves accessibility (tmux users, remote sessions) while enabling the SNES/16-bit aesthetic for capable terminals. GP-7 (Graceful Degradation) requires the system to work without the optional backend.
- **Source:** archive/cycles/015/decision-log.md (D1, D3, D5)
- **Status:** settled
- **Note:** Originally specified notcurses as the graphical backend; superseded by D-16 which replaces notcurses with Kitty protocol.

## D-13: Notcurses integrated via custom ctypes bindings
- **Decision:** Notcurses was bound via `ctypes.util.find_library()` at runtime. A `NOTCURSES_AVAILABLE` flag gated all notcurses code paths.
- **Rationale:** Avoids forcing users who don't need graphical rendering to install system libraries. Consistent with GP-7 and GP-11.
- **Source:** archive/cycles/015/decision-log.md (D4)
- **Status:** superseded by D-16
- **Note:** Notcurses deleted entirely in cycle 016 (WI-275) due to segfault with Python 3.14. See D-16.

## D-14: Three zoom levels in notcurses renderer with blitter modes
- **Decision:** NotcursesRenderer supported three zoom levels: CLOSE (16x16 cells, NCBLIT_PIXEL), MEDIUM (8x8 cells, NCBLIT_2x1), FAR (character cells, NCBLIT_1x1). Blitter mode was determined by zoom level.
- **Rationale:** Discrete levels avoid fractional positioning. Blitter-per-zoom ties visual fidelity to zoom context.
- **Source:** archive/cycles/015/decision-log.md (D6)
- **Status:** superseded by D-16
- **Note:** Notcurses deleted in cycle 016. Kitty backend inherits the three-zoom-level design; blitter modes replaced by Kitty protocol upload/display.

## D-15: Sprite PNG assets deliberately absent from initial delivery
- **Decision:** The sprite assets directory ships without PNG files. The system degrades to character rendering at all zoom levels (GP-7). The SNES/16-bit visual experience cannot be evaluated until sprites are created.
- **Rationale:** Sprite authoring is a separate design activity from renderer infrastructure. Delivering infrastructure first allows integration testing without blocking on art assets.
- **Source:** archive/cycles/015/decision-log.md (D12)
- **Status:** settled

## D-16: Notcurses abandoned; Kitty graphics protocol adopted as graphical backend
- **Decision:** The notcurses ctypes backend (gui/notcurses/ and all associated tests) was deleted entirely and replaced with a pure Python Kitty graphics protocol implementation using terminal escape sequences.
- **Rationale:** notcurses 3.0.17 segfaults with Python 3.14 on ARM64 macOS. The internal `input_thread` corrupts the mimalloc allocator after 2-5 seconds. All mitigations failed. No recovery path exists. Kitty protocol requires no C library — pure Python escape sequences.
- **Source:** archive/cycles/016/decision-log.md (D1, D6)
- **Policy:** Amends visualization P-6 (backend name); triggers architecture D-32.
- **Status:** settled

## D-17: Renderer infrastructure carried forward unchanged through backend pivot
- **Decision:** RendererProtocol, SymbolConfig, ZoomLevel enum, and the detect/resolve pattern all remain unchanged. KittyRenderer satisfies RendererProtocol via structural subtyping.
- **Rationale:** GP-4 (Modularity) validated — swapping from notcurses to Kitty required only the backend layer to change. The abstraction boundary held.
- **Source:** archive/cycles/016/decision-log.md (D2)
- **Status:** settled

## D-18: Sprite lifecycle via Kitty protocol numeric IDs
- **Decision:** Sprites are uploaded once and assigned a numeric image ID. The renderer displays them by ID reference and deletes by ID. `SpriteHandle` is a frozen dataclass — handles cannot be invalidated after issue. `SpriteManager.is_uploaded(image_id)` is the canonical check for upload state.
- **Rationale:** Fixes cycle 015 Q-12 (SpriteSheet mutation-after-cleanup hazard). Frozen handle cannot be silently invalidated. Replaces the ncvisual/plane lifecycle model.
- **Source:** archive/cycles/016/decision-log.md (D3, D8)
- **Status:** settled

## D-19: KittyApp fetches state in-process via urllib; no subprocess isolation
- **Decision:** `KittyApp` fetches world state directly via `urllib` HTTP calls. No subprocess wrapper is used.
- **Rationale:** Pure Python means no C library memory corruption risk. Subprocess isolation was a notcurses-specific mitigation and does not apply to the Kitty backend.
- **Source:** archive/cycles/016/decision-log.md (D4)
- **Status:** settled

## D-20: Kitty protocol pixel coordinates require multiplication by tile_pixels
- **Decision:** Cell coordinates `sx`/`sy` must be multiplied by `tile_pixels` before passing to `encode_image_display`. Kitty protocol X/Y parameters are pixel offsets, not cell indices.
- **Rationale:** Caught by incremental review (C1) during cycle 016 rework of WI-278. Pixel-offset semantics differ from character-cell semantics used internally.
- **Source:** archive/cycles/016/decision-log.md (D7)
- **Status:** settled

## D-21: Fixture data for rendering integration tests captured from live daemon
- **Decision:** JSON fixture files for Kitty integration tests were captured from a live running daemon rather than constructed synthetically. The state fixture contains 2 agents, 17 structures, and 16 villages; the terrain fixture has 10,201 cells.
- **Rationale:** Synthetic fixtures may not match the exact shape of real API responses — the same mismatch that caused the cycle 016 crash. Live-captured data guarantees the fixture matches what `StateFetcher` receives in production.
- **Assumes:** Fixture agents happen to be all GENERAL/idle type. Zombie and non-general type paths are not covered at integration level (see Q-23).
- **Source:** archive/cycles/017/decision-log.md (D6)
- **Status:** settled

## D-22: All dict-access patterns removed from KittyApp after StateFetcher typed correctly
- **Decision:** All `isinstance(v, dict)` checks and `.get()` calls on agent, structure, and village objects in `app.py` were removed after WI-283 ensured `StateFetcher.fetch_snapshot()` returns typed dataclasses. Direct attribute access replaces all defensive patterns.
- **Rationale:** Once the parse layer is correct, defensive guards at access sites are unnecessary and mask future type regressions. An `AttributeError` is the correct failure signal for a type mismatch; a `.get()` fallback silently hides it.
- **Source:** archive/cycles/017/decision-log.md (D4)
- **Status:** settled

## D-23: Manual smoke test added as explicit gated work item for Kitty viewer
- **Decision:** A fourth work item (WI-286) required manual verification: running `hamlet view --renderer kitty` against a live daemon and confirming no crash, keyboard response, and clean exit. User confirmed the app renders (slight flicker noted, deferred).
- **Rationale:** Automated tests verify parse correctness but cannot substitute for observing the viewer launch, render, and accept keyboard input in a real terminal. The cycle 016 crash occurred in exactly this live scenario, not in tests.
- **Source:** archive/cycles/017/decision-log.md (D7)
- **Status:** settled
