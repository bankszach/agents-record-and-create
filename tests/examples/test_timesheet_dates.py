from examples.timesheet_agent.backend.parsers import resolve_date_phrase


def test_resolve_relative_today_and_yesterday():
    base = "2025-09-09"  # Tuesday
    assert resolve_date_phrase("today", base_date=base) == "2025-09-09"
    assert resolve_date_phrase("yesterday", base_date=base) == "2025-09-08"
    assert resolve_date_phrase("tomorrow", base_date=base) == "2025-09-10"


def test_resolve_month_name_formats():
    assert resolve_date_phrase("September 9 2025") == "2025-09-09"
    assert resolve_date_phrase("9 September 2025") == "2025-09-09"


def test_resolve_numeric_mdy():
    assert resolve_date_phrase("09/09/2025") == "2025-09-09"
