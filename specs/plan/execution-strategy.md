# Execution Strategy — Refinement 2026-03-19 (refine-6: Open Items)

## Mode
**Full parallel** — All four items are independent with no shared file scope.

## Parallelism
Max concurrent agents: 4

## Worktrees
Enabled: no
Reason: Items touch different files with no overlap. No isolation needed.

## Review Cadence
Incremental review after each item completes. Comprehensive review after all four.

## Work Item Groups

### Group 1 — All parallel

| ID  | Title                                           | Complexity | Files                                                        |
|-----|-------------------------------------------------|------------|--------------------------------------------------------------|
| 174 | Extract hook utilities to hamlet_hook_utils.py  | low        | hooks/hamlet_hook_utils.py (create), hooks/*.py (modify x4) |
| 175 | Remove dead .sh wrapper files from hooks/       | low        | hooks/*.sh (delete x4)                                       |
| 176 | Improve mcp import check in start.sh            | low        | mcp/start.sh (modify)                                        |
| 177 | Add server_url parameter to hamlet_init         | low        | mcp/server.py (modify)                                       |

## Dependency Graph

```
174 ─── (independent)
175 ─── (independent)
176 ─── (independent)
177 ─── (independent)
```

## Agent Configuration
Model for workers: sonnet
Model for reviewers: sonnet
Permission mode: acceptEdits
