"""Type inference rules for AgentType classification from tool usage patterns."""
from __future__ import annotations

from hamlet.inference.types import AgentType

# Each rule is a tuple of:
#   (tool_patterns: list[str], minimum_ratio: float, agent_type: AgentType)
#
# Rules are evaluated in order; the first rule whose tool-frequency ratio
# meets or exceeds minimum_ratio wins.  Tool frequency is computed as
# count(events matching any pattern) / total_events in the sliding window.
TYPE_RULES: list[tuple[list[str], float, AgentType]] = [
    (["Read", "Grep", "Glob"], 0.6, AgentType.RESEARCHER),
    (["Write", "Edit"], 0.6, AgentType.CODER),
    (["Bash"], 0.5, AgentType.EXECUTOR),
    (["Task"], 0.4, AgentType.ARCHITECT),
    # NOTE: AgentType.PLANNER is defined (inference/types.py) but intentionally
    # has no TYPE_RULE entry in this list. It is reserved for a future rule
    # (e.g., high ratio of coordination/planning tool calls). Do not add a
    # PLANNER rule without a corresponding interview/refinement cycle.
]

__all__ = ["TYPE_RULES"]
