"""CSV export utilities for timesheet entries."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence


def render_csv(rows: Iterable[dict[str, object]], fieldnames: Sequence[str]) -> str:
    """Render an iterable of dict rows to a CSV string with given headers.

    - Unknown keys are ignored to keep output stable.
    - Values are stringified via the csv module.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(fieldnames), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row or {})
    return buf.getvalue()
