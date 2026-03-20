## Verdict: Pass

All five acceptance criteria are satisfied. The `command -v python3` guard is correctly placed before the import check, both diagnostics go to stderr, `python3 -m pip` is used in the mcp not-found message, and the script is POSIX sh compatible.

## Critical Findings

None.

## Significant Findings

None.

## Minor Findings

None.

## Unmet Acceptance Criteria

None.
