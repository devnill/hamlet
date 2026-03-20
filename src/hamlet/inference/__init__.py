"""Agent inference module — infers agent type and lifecycle from hook events."""

from .types import (
    AgentType,
    InferenceAction,
    InferenceResult,
    InferenceState,
    PendingTool,
    SessionState,
    ToolWindow,
    TYPE_COLORS,
)
from .engine import AgentInferenceEngine

__all__ = [
    "AgentType",
    "InferenceAction",
    "InferenceResult",
    "PendingTool",
    "SessionState",
    "ToolWindow",
    "InferenceState",
    "TYPE_COLORS",
    "AgentInferenceEngine",
]
