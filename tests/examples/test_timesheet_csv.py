from examples.timesheet_agent.backend.exporters.csv import render_csv


def test_render_csv_basic():
    rows = [{"employee": "Alice", "date": "2025-09-01", "hours": 8}]
    fields = ["employee", "date", "hours"]
    out = render_csv(rows, fields)
    assert "employee,date,hours" in out
    assert "Alice,2025-09-01,8" in out


def test_render_csv_escaping_commas_and_quotes():
    rows = [
        {"employee": "A,B", "date": "2025-09-01", "hours": 8},
        {"employee": 'Bob "The Builder"', "date": "2025-09-02", "hours": 7.5},
    ]
    fields = ["employee", "date", "hours"]
    out = render_csv(rows, fields)
    # CSV module quotes fields containing commas or quotes.
    assert '"A,B"' in out
    assert '"Bob ""The Builder"""' in out


def test_render_csv_unknown_keys_ignored():
    rows = [{"employee": "Alice", "date": "2025-09-01", "hours": 8, "extra": 123}]
    fields = ["employee", "date", "hours"]
    out = render_csv(rows, fields)
    assert ",123" not in out
