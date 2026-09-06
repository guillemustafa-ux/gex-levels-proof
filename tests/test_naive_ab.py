"""The failure this repo exists for: yesterday's open interest presented as live."""

from __future__ import annotations

import json

from gex_levels.freshness import FRESH, STALE, verdict
from gex_levels.output import levels, naive_levels

from .conftest import CLOSE_1555, NEXT_0935, OI_AS_OF, OPEN_0935

TEMPORAL_MARKERS = ("time", "age", "as_of", "asof", "stale", "fresh", "computed")


def test_naive_output_presents_stale_oi_as_live(chain):
    # 09:35: the snapshot is 17.6h old. 15:55: 23.9h old. Same chain, same OI.
    at_open = json.dumps(naive_levels(chain))
    at_close = json.dumps(naive_levels(chain))

    assert verdict(OI_AS_OF, OPEN_0935).age_hours != verdict(OI_AS_OF, CLOSE_1555).age_hours
    # Byte for byte the same payload, six hours apart, on data that was taken
    # before the session even opened. Nothing in it lets a reader notice.
    assert at_open == at_close
    for marker in TEMPORAL_MARKERS:
        assert marker not in at_open.lower()


def test_stamped_output_changes_verdict_over_time(chain):
    at_open = levels(chain, OPEN_0935)
    at_close = levels(chain, CLOSE_1555)
    next_day = levels(chain, NEXT_0935)

    # The levels themselves are identical: the OI did not move.
    for key in ("spot", "flip", "call_wall", "put_wall", "levels"):
        assert at_open[key] == at_close[key] == next_day[key]

    # The context is not.
    assert at_open["oi_as_of"] == "2026-09-04T20:00:00Z"
    assert at_open["computed_at"] == "2026-09-05T13:35:00Z"
    assert at_close["computed_at"] == "2026-09-05T19:55:00Z"
    assert at_open["age_hours"] < at_close["age_hours"] < next_day["age_hours"]
    assert at_open["freshness"] == FRESH
    assert at_close["freshness"] == FRESH
    assert next_day["freshness"] == STALE
    assert "Do not present these levels as live" in next_day["freshness_reason"]
