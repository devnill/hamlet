# 041: Implement SimulationEngine Core

## Objective
Create SimulationEngine class that runs the game loop at 30 FPS, managing tick timing and state.

## Acceptance Criteria
- [ ] File `src/hamlet/simulation/engine.py` exists
- [ ] `SimulationEngine.__init__(world_state, config)` constructor
- [ ] `async start()` creates and starts tick loop task
- [ ] `async stop()` cancels task and awaits cleanup
- [ ] `set_tick_rate(rate)` updates tick rate
- [ ] `_tick_loop()` runs while running flag, sleeps between iterations
- [ ] `SimulationState` dataclass with tick_count, last_tick_at, running
- [ ] `SimulationConfig` dataclass with tick_rate (default 30.0), work_unit_scale, zombie_threshold, expansion_threshold

## File Scope
- `src/hamlet/simulation/__init__.py` (create)
- `src/hamlet/simulation/engine.py` (create)
- `src/hamlet/simulation/config.py` (create)
- `src/hamlet/simulation/state.py` (create)

## Dependencies
- Depends on: World State module (interface)
- Blocks: 042, 043, 044, 045

## Implementation Notes
Use `asyncio.create_task` for background loop. Catch exceptions in tick loop, continue running.

## Complexity
Medium