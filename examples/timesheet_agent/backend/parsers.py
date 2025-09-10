"""Natural-language to structured timesheet parsing (placeholder).

This module exposes a function that accepts a freeform input and returns a
dictionary suitable for validation and eventual conversion to a TimesheetEntry.
"""

from __future__ import annotations

import re
from datetime import date as _date, datetime, timedelta, tzinfo as _tzinfo
from typing import Any
from zoneinfo import ZoneInfo


def parse_freeform(text: str) -> dict[str, Any]:
    """Parse a freeform timesheet line into structured fields.

    Heuristics (simple but practical):
    - Date: first YYYY-MM-DD match.
    - Hours: first number optionally followed by hour markers (h/hr/hrs/hour/hours) not part of a date.
    - Employee: leading tokens until a date/number/hour-marker/stop-word (on/for/at) is encountered.
    - Project: if "for <project>" appears, capture the remainder as project (until a "notes:" marker if present).
    - Notes: if "notes:" appears, capture the remainder after it.

    All fields are optional; missing values are left empty/None for validation to catch.
    """
    s = text.strip()
    if not s:
        return {"employee": "", "date": "", "hours": None, "project": None, "notes": None}

    # Date.
    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", s)
    date = date_match.group(1) if date_match else ""

    # Notes: capture after explicit marker.
    notes: str | None = None
    notes_match = re.search(r"\bnotes:\s*(.+)$", s, flags=re.IGNORECASE)
    if notes_match:
        notes = notes_match.group(1).strip()

    # Project: capture after "for ". If notes are present, stop before notes.
    project: str | None = None
    # Build a truncated string without notes for simpler capture.
    s_wo_notes = s
    if notes_match:
        s_wo_notes = s[: notes_match.start()].strip()
    proj_match = re.search(r"\bfor\s+([^\n]+)$", s_wo_notes, flags=re.IGNORECASE)
    if proj_match:
        project = proj_match.group(1).strip()

    # Hours: find a numeric value that is not part of a date.
    hours: float | None = None
    hours_match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours)?\b",
        s,
        flags=re.IGNORECASE,
    )
    if hours_match:
        num_str = hours_match.group(1)
        # Skip if this number is the year of the date (e.g., 2025 in 2025-09-01).
        if not (date and num_str and date.startswith(num_str) and len(num_str) == 4):
            try:
                hours = float(num_str)
            except ValueError:
                hours = None

    # Employee: take leading tokens until date/number/hour-marker/stop-word.
    stop_words = {"on", "for", "at"}
    hour_markers = {"h", "hr", "hrs", "hour", "hours"}
    employee_tokens: list[str] = []
    for tok in s.split():
        low = tok.lower().strip(",.;:")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", tok):
            break
        if any(ch.isdigit() for ch in tok):
            break
        if low in stop_words or low in hour_markers:
            break
        employee_tokens.append(tok)
        # Heuristic: cap to first 3 tokens for names like "Alex J Doe".
        if len(employee_tokens) >= 3:
            break
    employee = " ".join(employee_tokens).strip()

    return {
        "employee": employee,
        "date": date,
        "hours": hours,
        "project": project if project else None,
        "notes": notes if notes else None,
    }


_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def resolve_date_phrase(
    phrase: str,
    *,
    timezone: str | None = None,
    base_date: str | None = None,
) -> str:
    """Resolve relative or natural-language dates to ISO YYYY-MM-DD.

    Supported:
    - Relative: today, yesterday, tomorrow.
    - ISO: YYYY-MM-DD (returned as-is if valid).
    - Month/day names: "September 9 2025", "9 September 2025" (commas/ordinals tolerated).
    - Numeric with year: MM/DD/YYYY.
    - Weekday phrases (limited): "this monday", "next tuesday", "last friday".

    Args:
        phrase: The user-provided date phrase.
        timezone: Optional IANA timezone (e.g., "America/Los_Angeles"). Defaults to system tz or UTC.
        base_date: Optional YYYY-MM-DD to anchor relative phrases (useful for tests). Defaults to today.
    """
    s = (phrase or "").strip().lower()
    if not s:
        return ""

    # Timezone: prefer explicit IANA name; otherwise use local tzinfo; fallback to UTC.
    tzinfo: _tzinfo | None = None
    if timezone:
        try:
            tzinfo = ZoneInfo(timezone)
        except Exception:
            tzinfo = None
    if tzinfo is None:
        tzinfo = datetime.now().astimezone().tzinfo
    if tzinfo is None:
        tzinfo = ZoneInfo("UTC")

    # Base date
    today = _parse_iso_date(base_date) or datetime.now(tzinfo).date()

    # ISO
    if _is_iso_date(s):
        return s

    # Relative
    if s in {"today", "todays date", "today's date"}:
        return today.isoformat()
    if s == "yesterday":
        return (today - timedelta(days=1)).isoformat()
    if s == "tomorrow":
        return (today + timedelta(days=1)).isoformat()

    # Month name formats
    mdy = re.search(r"\b([a-zA-Z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})\b", s)
    if mdy:
        m = _MONTHS.get(mdy.group(1).lower())
        d = int(mdy.group(2))
        y = int(mdy.group(3))
        if m and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}"

    dmy = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+)\s*(\d{4})\b", s)
    if dmy:
        d = int(dmy.group(1))
        m = _MONTHS.get(dmy.group(2).lower())
        y = int(dmy.group(3))
        if m and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}"

    # Numeric MM/DD/YYYY
    mdy_num = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", s)
    if mdy_num:
        m = int(mdy_num.group(1))
        d = int(mdy_num.group(2))
        y = int(mdy_num.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}"

    # Weekday phrases: this/next/last <weekday>
    wk = re.search(
        r"\b(this|next|last)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", s
    )
    if wk:
        rel, wd = wk.group(1), wk.group(2)
        target = _WEEKDAYS[wd]
        offset = (target - today.weekday()) % 7
        if rel == "this":
            days = offset
        elif rel == "next":
            days = offset + 7
        else:  # last
            days = offset - 7
        return (today + timedelta(days=days)).isoformat()

    # Fallback: no match
    return ""


def _is_iso_date(s: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s))


def _parse_iso_date(s: str | None) -> _date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None
