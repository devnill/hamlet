"""RendererProtocol definition for hamlet GUI renderers.

Any renderer (TUI, headless, etc.) must satisfy this protocol
to be usable as a drop-in rendering backend.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, Sequence

if TYPE_CHECKING:
    from hamlet.viewport.state import ViewportState
    from hamlet.world_state.types import Agent, Structure


class RendererProtocol(Protocol):
    """Structural protocol for hamlet renderers.

    Implementors must provide render_frame() and cleanup().  The protocol
    uses structural subtyping (typing.Protocol) so no explicit inheritance
    is required.
    """

    def render_frame(
        self,
        viewport_state: "ViewportState",
        agents: Sequence["Agent"],
        structures: Sequence["Structure"],
        terrain_data: dict,
        event_log: list[str],
    ) -> None:
        """Render a single frame of the world view.

        Args:
            viewport_state: Current viewport center, size, and follow mode.
            agents: All agents to render in this frame.
            structures: All structures to render in this frame.
            terrain_data: Mapping from world positions (or keys) to terrain info.
            event_log: Recent event strings to display in a log panel.
        """
        ...

    def cleanup(self) -> None:
        """Release any resources held by the renderer (terminal state, etc.)."""
        ...


__all__ = ["RendererProtocol"]
