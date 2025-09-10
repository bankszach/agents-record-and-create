"""Server stub for streaming updates to a UI.

Intended to evolve into an SSE/WebSocket publisher of AgentEvent streams. This
keeps the example self-contained and avoids adding runtime dependencies until
the protocol stabilizes.
"""

from __future__ import annotations

from collections.abc import Iterable

from .agent import AgentEvent


def iter_events(events: Iterable[AgentEvent]) -> Iterable[str]:
    """Yield server-sent events from AgentEvent objects (placeholder)."""
    for e in events:
        # Minimal SSE framing; real impl should escape and chunk properly.
        yield f"event: {e.type}\n"
        yield f"data: {e.payload}\n\n"
