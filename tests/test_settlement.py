"""previous_settlement(): the OI snapshot time assumed for a vendor that does not publish it."""

from datetime import datetime, timezone

import pytest

from gex_levels.chain import previous_settlement


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def test_weekday_after_close_is_same_day() -> None:
    # Tuesday 21:00 UTC -> Tuesday 20:00 UTC
    assert previous_settlement(utc(2026, 9, 1, 21, 0)) == utc(2026, 9, 1, 20, 0)


def test_weekday_before_close_is_previous_day() -> None:
    # Tuesday 14:00 UTC -> Monday 20:00 UTC
    assert previous_settlement(utc(2026, 9, 1, 14, 0)) == utc(2026, 8, 31, 20, 0)


def test_exactly_at_close_is_previous_day() -> None:
    assert previous_settlement(utc(2026, 9, 1, 20, 0)) == utc(2026, 8, 31, 20, 0)


def test_sunday_rolls_back_to_friday() -> None:
    # Sunday 18:49 UTC -> Friday 20:00 UTC, not Saturday
    assert previous_settlement(utc(2026, 9, 6, 18, 49)) == utc(2026, 9, 4, 20, 0)


def test_saturday_rolls_back_to_friday() -> None:
    assert previous_settlement(utc(2026, 9, 5, 3, 0)) == utc(2026, 9, 4, 20, 0)


def test_monday_before_close_rolls_back_to_friday() -> None:
    assert previous_settlement(utc(2026, 9, 7, 12, 0)) == utc(2026, 9, 4, 20, 0)


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError):
        previous_settlement(datetime(2026, 9, 6, 18, 49))
