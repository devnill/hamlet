# 062: Symbol and Color Mappings

## Objective
Define agent symbols, colors, and structure symbols with material-based coloring.

## Acceptance Criteria
- [ ] File `src/hamlet/tui/symbols.py` exists
- [ ] `AGENT_SYMBOL = "@"` constant
- [ ] `AGENT_COLORS` dict maps `AgentType` enum to color names (researcher=cyan, coder=yellow, executor=green, architect=magenta, tester=blue, general=white)
- [ ] `get_agent_color(agent: Agent) -> str` returns color, blending with green for zombie state
- [ ] `STRUCTURE_SYMBOLS` dict maps `StructureType` to symbols (HOUSE=∩, WORKSHOP=◊, LIBRARY=⌂, FORGE=▲, TOWER=⎔, ROAD=#, WELL=○)
- [ ] `MATERIAL_COLORS` dict maps material names to colors (wood=brown, stone=gray, brick=red)
- [ ] `STAGE_SYMBOLS` dict maps stage (0-3) to shade symbols (░, ▒, ▓, █)
- [ ] `get_structure_symbol(structure: Structure) -> str` returns type symbol or stage symbol for roads
- [ ] `get_structure_color(structure: Structure) -> str` returns material color

## File Scope
- `src/hamlet/tui/symbols.py` (create)

## Dependencies
- Depends on: none
- Blocks: 063, 066

## Implementation Notes
For zombie agents, blend the base color with green using a 50/50 ratio. Structure type symbols are Unicode characters; roads use stage progression symbols instead of type symbols. Colors are Rich/Textual color names.

## Complexity
Low