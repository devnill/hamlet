# Gap Analysis — Cycle 012 (Terrain Generation Refinement)

## Critical Gaps

None.

## Significant Gaps

### G1: Legend Not Accessible in Map Viewer Mode

- **Requirement**: User requested "legend showing terrain types" (WI-249). The legend was implemented for the main game TUI but is not accessible in the map viewer mode where terrain exploration and parameter adjustment occur.
- **Impact**: Users exploring terrain parameters in `hamlet map-viewer` cannot see what terrain symbols represent. The `/` key (legend toggle in main app) has no binding in `MapApp`.
- **Current state**: `LegendOverlay` exists in `/Users/dan/code/hamlet/src/hamlet/tui/legend.py` with terrain symbols (`~` water, `^` mountain, `♣` forest, `"` meadow, `.` plain), but `MapApp` in `/Users/dan/code/hamlet/src/hamlet/tui/map_app.py` does not include this widget or binding.
- **Suggested resolution**: Add legend toggle (`/` key) to `MapApp` with the same `LegendOverlay` widget used in the main app. Alternatively, embed terrain symbol information in the parameter panel or status bar.

### G2: Terrain Parameter Validation Missing

- **Requirement**: Implicit requirement that configuration parameters should be validated to prevent extreme or nonsensical values.
- **Impact**: Users can set `region_scale=1` (producing tiny fragmented regions), `octaves=20` (excessive computation), or negative thresholds. The system accepts any numeric value without error or warning.
- **Current state**: `TerrainConfig` in `/Users/dan/code/hamlet/src/hamlet/world_state/terrain.py` (lines 59-106) is a dataclass with no `__post_init__` validation. Parameters like `region_scale` (comment says "50-200 cells"), `octaves` (typically 1-8), and threshold values are unchecked.
- **Suggested resolution**: Add `__post_init__` validation to `TerrainConfig` that logs warnings or raises errors for values outside reasonable ranges. Define acceptable ranges based on noise generation constraints.

## Minor Gaps

### G3: Empty Help Toggle in Map Viewer

- **File**: `/Users/dan/code/hamlet/src/hamlet/tui/map_app.py:299-301`
- **Requirement**: Implicit expectation that bound key actions do something visible.
- **Impact**: Pressing `?` in map viewer does nothing. The `action_toggle_help()` method is a no-op with a comment "For now, just display a message."
- **Current state**: Method body is `pass`.
- **Suggested resolution**: Implement a help overlay showing available keybindings (arrows/hjkl to scroll, +/- to zoom, R for random seed, S to save) or remove the binding if not needed.

### G4: Noise Library Fallback Produces Incoherent Terrain

- **File**: `/Users/dan/code/hamlet/src/hamlet/world_state/terrain.py:270-284` and `1969-1981`
- **Requirement**: Implicit requirement that terrain generation should produce coherent regions regardless of library availability.
- **Impact**: When the `noise` library is unavailable, `_generate_with_random()` produces scattered random terrain cells, not the coherent biome regions requested by the user. The "too busy scattered terrain cells" problem reappears.
- **Current state**: Fallback uses seeded random without region generation, smoothing, or water features. The `get_terrain_in_bounds()` method checks `HAS_NOISE` and falls back to basic generation with smoothing only.
- **Suggested resolution**: Document that the `noise` library is required for coherent terrain. Consider adding a check at startup with a warning, or implement a simplified coherent region algorithm that doesn't require Perlin noise.

### G5: River Minimum Length Hardcoded

- **File**: `/Users/dan/code/hamlet/src/hamlet/world_state/terrain.py:1261`
- **Requirement**: Implicit requirement that tunable parameters should be exposed in the configuration system.
- **Impact**: Rivers shorter than 3 cells are silently discarded. This threshold is not configurable, limiting user control over terrain appearance.
- **Current state**: Hardcoded check `if len(path) >= 3:` in `generate_rivers()`.
- **Suggested resolution**: Add `min_river_length` parameter to `TerrainConfig` with default value of 3, matching the pattern of other terrain parameters.

### G6: Map Viewer Does Not Show Saved Configuration Status

- **Requirement**: Implicit expectation that users should know whether their changes are saved or unsaved.
- **Impact**: Users cannot see if their parameter changes have been saved. The `_dirty` flag tracks this internally but is not displayed.
- **Current state**: `StatusBar` in `/Users/dan/code/hamlet/src/hamlet/tui/map_app.py` shows zoom level and controls, but not save status.
- **Suggested resolution**: Add a dirty indicator (e.g., `*` or `[unsaved]`) to the status bar when `_dirty` is True, similar to text editors.

## No Gaps Found

### User Requirements Coverage

The following user requirements from the original feedback are fully addressed:

1. **"Too busy" scattered cells to coherent biome regions**: WI-254 implements `region_scale` and `region_blending` parameters with low-frequency fBm noise for macro-scale terrain patterns.

2. **Larger biome regions**: The `region_scale` parameter (default 100) allows biome regions spanning 50-200 cells. Higher values create larger regions.

3. **Realistic transitions**: WI-257 implements CA smoothing rules for gradual boundaries between forests, meadows, and plains. WI-254's `region_blending` parameter controls transition sharpness.

4. **Water features (rivers, ponds, lakes)**: WI-255 implements:
   - `generate_rivers()` following elevation gradients
   - `generate_ponds()` in lowland areas
   - `detect_lakes()` and `expand_lake()` for connected water bodies
   - `water_percentage_target` for configurable water coverage

5. **Forests clustering near water**: WI-256 implements `forest_water_adjacency_bonus` for preferential seeding near water, `forest_region_bias_strength` for density variation, and `forest_percentage_target` for coverage control.

6. **Configurable parameters**: WI-250 adds 15+ configurable parameters to `TerrainConfig`. WI-251 persists configuration to `~/.hamlet/config.json`. WI-252 provides real-time parameter adjustment in the map viewer.

7. **Map viewer mode**: WI-252 implements `MapApp` with terrain-only rendering, parameter panel for adjustment, and save functionality.

8. **Zoom capability**: WI-253 implements zoom levels 1x, 2x, 4x, 8x in `MapViewer`.

9. **Legend showing terrain types**: WI-249 implements `LegendOverlay` with terrain symbols in the main game TUI (toggle with `/` key).

### Integration Completeness

- **Terrain to Village Placement**: `WorldStateManager` uses `TerrainGrid.is_passable()` for village placement.
- **Terrain to Structure Placement**: `WorldStateManager.create_structure()` validates terrain before placing structures.
- **Terrain to Agent Spawn**: `WorldStateManager._find_spawn_position()` validates terrain for agent positions.
- **Config Persistence**: `Settings.load()` loads terrain config, `app_factory.py` builds `TerrainConfig`, and `MapApp._on_save()` persists changes.
- **Terrain Pipeline**: `TerrainGrid.get_terrain_in_bounds()` correctly integrates all steps: heightmap generation, region bias, ridges, classification, smoothing, lakes, rivers, ponds, water percentage, and forest groves.
