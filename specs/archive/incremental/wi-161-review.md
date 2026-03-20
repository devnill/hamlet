## Verdict: Pass

`get_or_create_project` in manager.py calls `_seed_initial_structures(village)` at line 186–187, OUTSIDE the asyncio.Lock (domain policy P-7 satisfied). The method seeds LIBRARY, WORKSHOP, FORGE using offsets from village center, skips occupied positions, and logs warnings without blocking village creation. The seeding path in `get_or_create_agent` (line 372–373) also calls `_seed_initial_structures` outside the lock for the agent-triggers-project path.

## Critical Findings

None.

## Significant Findings

None.

## Minor Findings

None.

## Unmet Acceptance Criteria

None.
