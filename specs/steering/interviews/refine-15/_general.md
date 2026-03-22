# Refinement Interview — refine-15

**Date**: 2026-03-22
**Context**: Post-terrain-generation user feedback — terrain too busy, needs realistic biomes and configurability

---

## Q: What changes do you want to make?

A: Two main changes:
1. Add terrain types to the legend overlay
2. Refine terrain generation for realistic, coherent biomes

---

## Q: What specifically about terrain generation needs improvement?

A: The terrain is much too busy. I want something more realistic where biomes smoothly shift into each other without scattered terrain elements.

---

## Q: What scale should biomes be?

A: Larger seems better. The current noise makes it look too busy. Biomes should span larger areas (50+ cells).

---

## Q: How should biome transitions work?

A: Realistic biome zones — sometimes there are sharp borders, sometimes gradual. The generation code should be able to create variety to build a realistic looking map.

---

## Q: Should some terrain types be rarer or more localized?

A: Yes, having some regions more abundant in different resources makes sense. Forests should cluster near water/features rather than being randomly scattered.

---

## Q: What water features should be generated?

A: Variety: rivers, ponds, large lakes. Maybe oceans with islands later, but that's deferred for now due to incidental complexity.

---

## Q: What about mountain ranges?

A: Ridge lines are great — keep those. Can also have occasional scattered peaks.

---

## Q: How should forests be distributed?

A: They should cluster around water/features, modeling after how biomes interact in nature. Not randomly scattered.

---

## Q: Since this is highly subjective, how should parameters be tuned?

A:
- Have editable parameters that can be altered in real-time
- Create a map viewer mode in hamlet for parameter adjustment
- Save parameters to config
- Still use random seed, but parameters also affect generation
- Zoom out capability to see large areas and verify biome variety

---

## Q: How should zoom work?

A: Discrete levels for now (1x, 2x, 4x, 8x). The TUI makes smooth zoom not look great. Future GUI can have smooth zooming.

---

## Q: How should the map viewer be launched?

A: As a flag. `hamlet --map-viewer` or similar. The existing app already has scroll capability. The map viewer is specifically for terrain generation parameter tuning.

---

## Q: Should terrain generation remain deterministic?

A: Yes — same seed + same parameters should always produce identical terrain.

---

## Scope Confirmation

**In scope:**
- Legend enhancement: terrain types with symbols/colors
- Terrain generation refactor: biome regions, water features, forest clustering, smoothing
- Configurable parameters: all generation parameters exposed
- Map viewer mode: parameter adjustment UI, zoom functionality
- Config persistence: save/load parameters

**Out of scope:**
- Oceans/islands (deferred)
- Agent behavior changes
- Structure rendering changes
- Persistence of generated terrain (still on-demand)

**Guiding principles:** All still apply. No changes needed.

**Constraints:** No changes needed. Technology constraints remain (Python, Textual, SQLite, MCP).