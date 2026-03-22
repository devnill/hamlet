# WI-248 Review: Document Ridge Boundary Behavior

## Verdict: Pass

Clarifying comment added to explain ridge truncation behavior.

## Acceptance Criteria Status

- [x] Comment added at `terrain.py:974-977` explaining ridge truncation behavior
- [x] Comment explains that ridge positions extending outside bounds are skipped

## Implementation Summary

Added clarifying comment in the ridge integration section of `get_terrain_in_bounds()`:

```python
# Step 4: Mark ridge positions as MOUNTAIN
for ridge in ridges:
    for pos in ridge:
        # Only mark positions within bounds; ridges extending outside
        # bounds are truncated at the boundary
        if pos in terrain:
            terrain[pos] = TerrainType.MOUNTAIN
```

The comment explains that ridge chains may extend outside the requested bounds, and the `if pos in terrain` check ensures only positions within bounds are marked as MOUNTAIN.
