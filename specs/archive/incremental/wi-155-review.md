## Verdict: Fail

The zombie frame formula is correctly implemented, but the changeset ships with no tests for the modified `get_frames()` method or the updated `serialize_state()` call path.

## Critical Findings

None.

## Significant Findings

### S1: No tests for `get_frames()` zombie/non-zombie branching
- **File**: `/Users/dan/code/hamlet/tests/test_animation.py`
- **Issue**: `get_frames()` is the primary subject of WI-155, yet the test file contains zero calls to it. The zombie branch, non-zombie branch, `None` default, and frame range guarantees are all untested.
- **Impact**: The acceptance criteria explicitly list correct formula application and valid frame ranges. Neither is verified by any automated test. A future regression in either branch would go undetected.
- **Suggested fix**: Add a `TestGetFrames` class with at minimum: (1) a test that an agent_id in `zombie_ids` produces `ticks // TICKS_PER_PULSE_FRAME % 2` in range `[0, 1]`; (2) a test that an agent_id not in `zombie_ids` produces `ticks // TICKS_PER_SPIN_FRAME % 4` in range `[0, 3]`; (3) a test that calling `get_frames(zombie_ids=None)` treats all agents as non-zombie (no KeyError, all spin formula).

### S2: No tests for `serialize_state()` zombie_ids extraction
- **File**: `/Users/dan/code/hamlet/src/hamlet/mcp_server/serializers.py`
- **Issue**: The `serialize_state()` function was modified to extract `zombie_ids` and pass it to `get_frames()`. There are no tests verifying that ZOMBIE-state agents are correctly identified and routed, or that the `animation_frames` key in the response reflects the correct formula per agent type.
- **Impact**: The serializer is the integration point between the world state and the animation subsystem. Without tests, an error in the `AgentState.ZOMBIE` filter or in the `animation_manager is None` guard would be invisible.
- **Suggested fix**: Add an async test using a mock `world_state` and a real `AnimationManager`. Populate the manager with one active and one zombie agent tick count. Assert that `animation_frames` in the returned dict applies the spin formula to the active agent and the pulse formula to the zombie agent.

## Minor Findings

### M1: Docstring in `get_frames()` describes wrong formula notation
- **File**: `/Users/dan/code/hamlet/src/hamlet/simulation/animation.py:74`
- **Issue**: The docstring says `(TICKS_PER_PULSE_FRAME % 2)` and `(TICKS_PER_SPIN_FRAME % 4)`, omitting the integer division by the tick constant. The actual formulas are `ticks // TICKS_PER_PULSE_FRAME % 2` and `ticks // TICKS_PER_SPIN_FRAME % 4`.
- **Suggested fix**: Correct the docstring to `(ticks // TICKS_PER_PULSE_FRAME) % 2` and `(ticks // TICKS_PER_SPIN_FRAME) % 4` to match what is actually computed.

### M2: Implicit parenthesization in `get_frames()` differs from `get_animation_state()`
- **File**: `/Users/dan/code/hamlet/src/hamlet/simulation/animation.py:81-83`
- **Issue**: `get_animation_state()` uses explicit parentheses — `(raw // TICKS_PER_SPIN_FRAME) % 4` (line 38) and `(raw // TICKS_PER_PULSE_FRAME) % 2` (line 42). `get_frames()` writes the same expressions without parentheses: `ticks // TICKS_PER_PULSE_FRAME % 2` and `ticks // TICKS_PER_SPIN_FRAME % 4`. Python's left-associativity makes them numerically identical, but the inconsistency creates unnecessary reading friction.
- **Suggested fix**: Add parentheses to match the style used in `get_animation_state()`: `(ticks // TICKS_PER_PULSE_FRAME) % 2` and `(ticks // TICKS_PER_SPIN_FRAME) % 4`.

### M3: `zombie_ids or set()` masks an explicitly passed empty set
- **File**: `/Users/dan/code/hamlet/src/hamlet/simulation/animation.py:77`
- **Issue**: `zombie_ids = zombie_ids or set()` treats an explicitly passed empty set as equivalent to `None`. This is functionally harmless here because an empty zombie set and `None` should produce the same result, but it is a less precise guard than `if zombie_ids is None: zombie_ids = set()`.
- **Suggested fix**: Replace with `if zombie_ids is None: zombie_ids = set()` or use `zombie_ids if zombie_ids is not None else set()`.

## Unmet Acceptance Criteria

- [ ] Frame values remain in valid range (spin: 0-3, pulse: 0-1) — The formula is mathematically correct, but no test asserts these bounds for `get_frames()`. The acceptance criterion is not verified by the test suite.
