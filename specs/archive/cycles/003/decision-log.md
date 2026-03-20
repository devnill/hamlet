# Decision Log — Cycle 3

## D1: python3 PATH check is a significant gap requiring a new work item

The gap analyst identified that a missing `command -v python3` guard causes WI-171's new diagnostic to misfire with a misleading message when python3 is absent. This is the direct structural companion to the `command -v uv` check already in the script. Promoting to significant and creating WI-172.

## D2: `pip install mcp` vs `python3 -m pip install mcp` deferred to WI-172 scope

Code quality M2 (pip environment mismatch) will be addressed as part of WI-172's message improvements.

## D3: Dead .sh wrapper files deferred

MG1 (dead hook .sh wrappers) deferred — no runtime impact.

## D4: hamlet_init CLI references deferred

MG2 (hamlet_init success message references non-existent CLI) deferred — CLI is a future scope item.
