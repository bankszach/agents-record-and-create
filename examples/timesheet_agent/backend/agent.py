"""Agent orchestration for the timesheet example.

This module defines the high-level interaction loop:
    ask → parse → validate → confirm/revise → finalize.

No model calls are implemented yet. The public interface is designed so that a
CLI or server can drive the loop and stream events to a UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .forms import from_dict as entry_from_dict, validate as validate_entry
from .parsers import parse_freeform


@dataclass
class AgentEvent:
    """A simple event structure suitable for streaming to a UI."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentState:
    """Holds session state for the agent while collecting entries."""

    entries: list[dict[str, Any]] = field(default_factory=list)
    current: dict[str, Any] = field(default_factory=dict)
    confirmed: bool = False


class TimesheetAgent:
    """Interactive timesheet agent skeleton."""

    def __init__(self) -> None:
        self.state = AgentState()

    def start(self) -> AgentEvent:
        """Start the session and request initial input."""
        return AgentEvent(
            type="started",
            payload={
                "message": "Hello! Let's record a timesheet entry. Who worked, on what date, and for how many hours?",
            },
        )

    def provide_input(self, text: str) -> list[AgentEvent]:
        """Handle user-provided natural language text and advance the flow.

        For now this performs placeholder parsing and validation.
        """
        events: list[AgentEvent] = []
        events.append(AgentEvent(type="user_input", payload={"text": text}))

        # Parse freeform input into a tentative entry dictionary.
        parsed = self._parse(text)
        events.append(AgentEvent(type="parsed", payload={"entry": parsed}))

        # Validate the tentative entry.
        ok, problems = self._validate(parsed)
        if ok:
            self.state.current = parsed
            events.append(
                AgentEvent(
                    type="needs_confirmation",
                    payload={
                        "message": "Please confirm this entry.",
                        "proposed": parsed,
                    },
                )
            )
        else:
            events.append(
                AgentEvent(
                    type="needs_revision",
                    payload={
                        "message": "I need a bit more detail.",
                        "problems": problems,
                    },
                )
            )

        return events

    def confirm(self) -> list[AgentEvent]:
        """Confirm the current entry and add it to the list."""
        if not self.state.current:
            return [AgentEvent(type="error", payload={"message": "Nothing to confirm yet."})]
        self.state.entries.append(self.state.current)
        added = self.state.current
        self.state.current = {}
        return [
            AgentEvent(type="confirmed", payload={"entry": added}),
            AgentEvent(
                type="ready_for_next",
                payload={
                    "message": "Recorded. Add another entry or say 'done' to finish.",
                    "count": len(self.state.entries),
                },
            ),
        ]

    def finalize(self) -> AgentEvent:
        """Finish the session and return a final summary event."""
        return AgentEvent(
            type="finalized",
            payload={
                "message": "Session complete.",
                "entries": list(self.state.entries),
            },
        )

    # --- Internal helpers ---

    def _parse(self, text: str) -> dict[str, Any]:
        """Placeholder parser that extracts trivial fields.

        Expected improvements: natural-language parsing, date normalization, and
        project/task identification.
        """
        # Delegate to the shared parser to keep behavior consistent.
        return parse_freeform(text)

    def _validate(self, entry: dict[str, Any]) -> tuple[bool, list[str]]:
        """Placeholder validation returning problems for missing required fields."""
        # Use the shared validation against a normalized TimesheetEntry.
        candidate = entry_from_dict(entry)
        problems = validate_entry(candidate)
        return (len(problems) == 0, problems)
