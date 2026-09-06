from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from gex_levels.freshness import FRESH, STALE, verdict

from .conftest import CLOSE_1555, NEXT_0935, OI_AS_OF, OPEN_0935


def test_under_24h_is_fresh_and_says_how_old():
    f = verdict(OI_AS_OF, OPEN_0935)
    assert f.status == FRESH
    assert f.age_hours == 17.58
    assert "17.58h old" in f.reason


def test_still_fresh_minutes_before_the_window_closes():
    f = verdict(OI_AS_OF, CLOSE_1555)
    assert f.status == FRESH
    assert f.age_hours == 23.92


def test_past_24h_is_stale_with_the_instruction_in_words():
    f = verdict(OI_AS_OF, NEXT_0935)
    assert f.status == STALE
    assert f.age_hours == 41.58
    assert "Do not present these levels as live" in f.reason


def test_exactly_at_the_window_is_stale():
    assert verdict(OI_AS_OF, OI_AS_OF + timedelta(hours=24)).status == STALE


def test_naive_datetimes_are_refused():
    with pytest.raises(ValueError):
        verdict(OI_AS_OF, datetime(2026, 9, 5, 13, 35))
