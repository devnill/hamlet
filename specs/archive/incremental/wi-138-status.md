# WI-138 Status — Fix animation_manager wiring and frame serialization

## Status: Complete

## Changes Made

### 1. `src/hamlet/simulation/animation.py`
Added public `get_frames()` method to `AnimationManager`:
- Returns `dict[str, int]` mapping agent_id to display frame index
- Converts raw tick counts using `ticks // TICKS_PER_SPIN_FRAME % 4`
- Uses the file's existing constants (`TICKS_PER_SPIN_FRAME = 8`, 4 frames for spin)

### 2. `src/hamlet/__main__.py`
- Passed `animation_manager=animation_manager` to `MCPServer(...)` constructor
- `animation_manager` was already constructed on line 96 but not passed to MCPServer

### 3. `src/hamlet/cli/commands/daemon.py`
- Passed `animation_manager=animation_manager` to `MCPServer(...)` constructor
- Same issue as `__main__.py` — constructed but not wired

### 4. `src/hamlet/mcp_server/serializers.py`
- Replaced `dict(animation_manager._frames)` (raw tick counts, private attr access) with
  `animation_manager.get_frames()` (display frame indices, public API)
- Used the conditional one-liner form as specified

## Acceptance Criteria Met
- [x] MCPServer receives `animation_manager` in both `__main__.py` and `daemon.py`
- [x] `AnimationManager.get_frames()` exists and returns display frame indices (not raw ticks)
- [x] `serializers.py` calls `get_frames()` not `_frames`
