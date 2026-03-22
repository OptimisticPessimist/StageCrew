from datetime import UTC, datetime

from src.services.deadline_reminder import _days_remaining


def test_days_remaining_uses_calendar_day_boundaries_for_same_day():
    now = datetime(2026, 3, 22, 9, 0, tzinfo=UTC)
    due_date = datetime(2026, 3, 22, 23, 59, tzinfo=UTC)

    assert _days_remaining(due_date, now) == 0


def test_days_remaining_does_not_floor_partial_days():
    now = datetime(2026, 3, 22, 9, 0, tzinfo=UTC)
    due_date = datetime(2026, 3, 24, 8, 0, tzinfo=UTC)

    assert _days_remaining(due_date, now) == 2


def test_days_remaining_handles_overdue_items_by_calendar_day():
    now = datetime(2026, 3, 22, 9, 0, tzinfo=UTC)
    due_date = datetime(2026, 3, 21, 23, 59, tzinfo=UTC)

    assert _days_remaining(due_date, now) == -1
