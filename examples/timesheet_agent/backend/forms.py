"""Schemas and validation for timesheet entries.

Dependencies are intentionally avoided for now. This module provides simple
dataclasses and validation helpers. We can migrate to pydantic once the shape
stabilizes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TimesheetEntry:
    """A minimal timesheet entry representation."""

    employee: str
    date: str
    hours: float
    project: str | None = None
    notes: str | None = None


def from_dict(data: dict[str, Any]) -> TimesheetEntry:
    """Convert a dictionary to a `TimesheetEntry` with basic coercion."""
    return TimesheetEntry(
        employee=str(data.get("employee", "")),
        date=str(data.get("date", "")),
        hours=float(data.get("hours", 0) or 0),
        project=(str(data["project"]) if data.get("project") is not None else None),
        notes=(str(data["notes"]) if data.get("notes") is not None else None),
    )


def validate(entry: TimesheetEntry) -> list[str]:
    """Return a list of human-readable issues if validation fails."""
    issues: list[str] = []
    if not entry.employee.strip():
        issues.append("Employee is required.")
    if not entry.date.strip():
        issues.append("Date is required.")
    if entry.hours <= 0:
        issues.append("Hours must be greater than zero.")
    return issues
