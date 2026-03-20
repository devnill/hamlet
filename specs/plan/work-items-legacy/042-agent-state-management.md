# 042: Implement Agent State Management

## Objective
Implement agent state transitions for idle/zombie detection based on last-seen timestamps.

## Acceptance Criteria
- [ ] File `src/hamlet/simulation/agent_updater.py` exists
- [ ] `AgentUpdater` class with `__init__(config)`
- [ ] `async update_agents(agents, world_state)` method
- [ ] Agents with `time_since_seen > zombie_threshold` (default 5 min) become zombie
- [ ] Agents with `time_since_seen > 1 minute` but below threshold become idle
- [ ] Agents below 1 minute are active
- [ ] State transitions call `world_state.update_agent`

## File Scope
- `src/hamlet/simulation/agent_updater.py` (create)

## Dependencies
- Depends on: 041
- Blocks: none

## Implementation Notes
Threshold constants from SimulationConfig. Zombie threshold is configurable, idle threshold is fixed at 1 minute.

## Complexity
Low