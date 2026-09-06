"""The level string is the contract between Python and the Pine parser."""

from __future__ import annotations

import pytest

from gex_levels.output import levels, parse_level_string, to_level_string

from .conftest import OPEN_0935

README_EXAMPLE = "v1;asof=20260904T2000Z;spot=5400.00;FLIP=5387.5;CW=5450;PW=5300;L=5425:1.2e9,5375:-8.01e8"


def test_round_trip_is_lossless(chain):
    d = levels(chain, OPEN_0935)
    s = to_level_string(d)
    parsed = parse_level_string(s)

    assert to_level_string(parsed) == s
    for key in ("version", "oi_as_of", "spot", "flip", "call_wall", "put_wall", "levels"):
        assert parsed[key] == d[key]


def test_readme_example_parses_as_documented():
    parsed = parse_level_string(README_EXAMPLE)
    assert parsed["oi_as_of"] == "2026-09-04T20:00:00Z"
    assert parsed["spot"] == 5400.0
    assert parsed["flip"] == 5387.5
    assert parsed["call_wall"] == 5450.0
    assert parsed["put_wall"] == 5300.0
    assert parsed["levels"] == [{"strike": 5425.0, "gex": 1.2e9}, {"strike": 5375.0, "gex": -8.01e8}]


def test_absent_flip_travels_as_na():
    s = README_EXAMPLE.replace("FLIP=5387.5", "FLIP=na")
    parsed = parse_level_string(s)
    assert parsed["flip"] is None
    assert "FLIP=na" in to_level_string(parsed)


def test_string_has_no_whitespace_and_fits_a_tradingview_input(chain):
    s = to_level_string(levels(chain, OPEN_0935, top_n=10))
    assert " " not in s and "\n" not in s
    assert s.startswith("v1;asof=20260904T2000Z;spot=5400.00;")
    assert len(s) < 1000


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "v2;asof=20260904T2000Z;spot=5400.00;FLIP=na;CW=5450;PW=5300;L=",
        "v1;asof=20260904T2000Z;spot=5400.00;FLIP=na;CW=5450;PW=5300",  # missing L
        "v1;asof=2026-09-04;spot=5400.00;FLIP=na;CW=5450;PW=5300;L=",  # wrong asof shape
        "v1;asof=20260904T2000Z;spot=abc;FLIP=na;CW=5450;PW=5300;L=",
        "v1;asof=20260904T2000Z;spot=5400.00;FLIP=na;CW=5450;PW=5300;L=5425-1e9",  # no ':'
        "v1;asof=20260904T2000Z;spot=5400.00;FLIP=na;CW=5450;PW=5300;L=5425:1.2e9, 5375:-8e8",
        "v1;asof=20260904T2000Z;spot=5400.00;FLIP=na;CW=5450;PW=5300;L=5425:1.2e9;junk",
    ],
)
def test_malformed_input_is_rejected(bad):
    with pytest.raises(ValueError):
        parse_level_string(bad)
