from typing import Any

from examples.timesheet_agent.cli import _upsert_entry


def test_upsert_updates_in_place_and_deduplicates_notes():
    entries: list[dict[str, Any]] = []
    # First insert without project
    _upsert_entry(
        entries, employee="Alice", date="2025-09-09", hours=8.0, project=None, notes="Setting units"
    )
    assert len(entries) == 1
    assert entries[0]["project"] is None
    # Second call with project provided should update the existing row, not append
    _upsert_entry(
        entries,
        employee="Alice",
        date="2025-09-09",
        hours=8.0,
        project="HQP",
        notes="Setting units",
    )
    assert len(entries) == 1
    assert entries[0]["project"] == "HQP"
    # Notes should be merged without duplication
    assert entries[0]["notes"] == "Setting units"
