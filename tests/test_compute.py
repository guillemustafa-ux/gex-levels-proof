"""Sign convention, aggregation and the three headline levels on the fixture."""

from __future__ import annotations

from datetime import date

import pytest

from gex_levels.chain import Chain, OptionQuote
from gex_levels.compute import compute_levels, gex_by_strike, quote_gex

from .conftest import FIXTURE_CALL_WALL, FIXTURE_FLIP_BRACKET, FIXTURE_PUT_WALL, OI_AS_OF


def test_calls_are_positive_and_puts_are_negative_with_equal_magnitude():
    call = quote_gex(5400.0, 5450.0, 30 / 365, 0.15, 1000, "C")
    put = quote_gex(5400.0, 5450.0, 30 / 365, 0.15, 1000, "P")
    assert call > 0
    assert put < 0
    assert call == -put


def test_same_strike_across_rights_and_expiries_aggregates_into_one_level():
    quotes = [
        OptionQuote(5400.0, date(2026, 9, 12), "C", 1000, 0.15),
        OptionQuote(5400.0, date(2026, 10, 5), "C", 500, 0.15),
        OptionQuote(5400.0, date(2026, 9, 12), "P", 300, 0.15),
    ]
    chain = Chain(5400.0, OI_AS_OF, quotes)
    by_strike = gex_by_strike(chain)
    expected = sum(
        quote_gex(5400.0, 5400.0, (q.expiry - OI_AS_OF.date()).days / 365, q.iv, q.open_interest, q.right)
        for q in quotes
    )
    assert list(by_strike) == [5400.0]
    assert by_strike[5400.0] == pytest.approx(expected)


def test_expired_and_zero_oi_quotes_do_not_contribute():
    chain = Chain(
        5400.0,
        OI_AS_OF,
        [
            OptionQuote(5400.0, date(2026, 9, 4), "C", 1000, 0.15),  # expires on the snapshot day
            OptionQuote(5450.0, date(2026, 10, 5), "C", 0, 0.15),
            OptionQuote(5500.0, date(2026, 10, 5), "C", 10, 0.15),
        ],
    )
    assert list(gex_by_strike(chain)) == [5500.0]


def test_fixture_call_wall_and_put_wall_are_the_planted_strikes(chain):
    lv = compute_levels(chain)
    assert lv.call_wall == FIXTURE_CALL_WALL
    assert lv.put_wall == FIXTURE_PUT_WALL
    assert lv.by_strike[FIXTURE_CALL_WALL] > 0
    assert lv.by_strike[FIXTURE_PUT_WALL] < 0


def test_fixture_flip_sits_between_the_two_bracketing_strikes(chain):
    lv = compute_levels(chain)
    low, high = FIXTURE_FLIP_BRACKET
    assert low < lv.flip < high
    assert round(lv.flip, 2) == 5430.34
    # Net long gamma overall, with the flip a little above spot; distinct
    # from both walls so no level hides another.
    assert lv.total > 0
    assert lv.put_wall < lv.spot < lv.flip < lv.call_wall


def test_top_levels_are_ranked_by_absolute_gex(chain):
    lv = compute_levels(chain, top_n=5)
    magnitudes = [abs(g) for _, g in lv.top]
    assert len(lv.top) == 5
    assert magnitudes == sorted(magnitudes, reverse=True)
    assert lv.top[0][0] == FIXTURE_CALL_WALL
    assert lv.top[1][0] == FIXTURE_PUT_WALL
