from examples.timesheet_agent.backend.utils import classify_hours


def test_classify_hours_full_day():
    assert classify_hours(8.0, full_day=8.0) is None


def test_classify_hours_partial_and_overtime():
    assert classify_hours(6.5, full_day=8.0) == "Partial day — 1.5h short of 8h"
    assert classify_hours(8.5, full_day=8.0) == "Overtime — +0.5h over 8h"
