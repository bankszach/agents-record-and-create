from __future__ import annotations

import os
from collections.abc import Iterable


def get_full_day_hours() -> float:
    """Return the configured full-day hours (default 8.0)."""
    try:
        val = float(os.environ.get("TIMESHEET_FULL_DAY_HOURS", "8") or 8)
        return val if val > 0 else 8.0
    except Exception:
        return 8.0


def classify_hours(hours: float, full_day: float | None = None) -> str | None:
    """Return a standardized note for partial day or overtime.

    - If hours == full_day: returns None.
    - If hours < full_day: "Partial day — Xh short of {full_day}h".
    - If hours > full_day: "Overtime — +Xh over {full_day}h".
    """
    full = full_day if full_day is not None else get_full_day_hours()
    delta = round(hours - full, 2)
    if abs(delta) < 1e-9:
        return None
    if delta < 0:
        short = _strip_trailing_zero(-delta)
        return f"Partial day — {short}h short of {full:g}h"
    over = _strip_trailing_zero(delta)
    return f"Overtime — +{over}h over {full:g}h"


def merge_notes(base: str | None, *extras: Iterable[str | None]) -> str | None:
    """Merge non-empty notes with ' | ' delimiter, de-duplicating while preserving order."""
    parts: list[str] = []
    seen: set[str] = set()

    def _add(s: str | None) -> None:
        if not s:
            return
        t = str(s).strip()
        if not t:
            return
        if t in seen:
            return
        seen.add(t)
        parts.append(t)

    _add(base)
    for group in extras:
        for e in group or []:
            _add(e)
    return " | ".join(parts) if parts else None


def _strip_trailing_zero(x: float) -> str:
    s = f"{x:.2f}"
    if s.endswith(".00"):
        return s[:-3]
    if s.endswith("0"):
        return s[:-1]
    return s
