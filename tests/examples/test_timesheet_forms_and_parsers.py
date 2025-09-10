from examples.timesheet_agent.backend.forms import TimesheetEntry, from_dict, validate
from examples.timesheet_agent.backend.parsers import parse_freeform


def test_from_dict_and_validate_ok():
    entry = from_dict(
        {
            "employee": "Alice Doe",
            "date": "2025-09-01",
            "hours": 7.5,
            "project": "Project A",
            "notes": "Regular shift.",
        }
    )
    assert isinstance(entry, TimesheetEntry)
    problems = validate(entry)
    assert problems == []


def test_validate_requires_fields():
    entry = from_dict({"employee": "", "date": "", "hours": 0})
    problems = validate(entry)
    # Should surface 3 distinct issues for missing employee/date and non-positive hours.
    assert any("Employee is required" in p for p in problems)
    assert any("Date is required" in p for p in problems)
    assert any("Hours must be" in p for p in problems)


def test_parse_freeform_basic():
    text = "Alex Doe 7.5 hours on 2025-09-01 for Project A"
    data = parse_freeform(text)
    assert data["employee"] in ("Alex", "Alex Doe")  # heuristic may capture 1-2 tokens
    assert data["date"] == "2025-09-01"
    assert data["hours"] == 7.5
    assert (data["project"] or "").lower().startswith("project a")
