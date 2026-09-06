"""Naive vs stamped output, side by side, at two moments of the same session.

The open interest is one snapshot taken after the previous close. Nothing in
the chain changes between the two moments; only the clock does.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gex_levels.chain import from_json  # noqa: E402
from gex_levels.output import levels, naive_levels, to_level_string  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "spx_synthetic_chain.json"
NEW_YORK = timezone(timedelta(hours=-4), "EDT")  # fixed offset on purpose: no tz database needed

MOMENTS = [
    ("09:35 New York, five minutes after the open", datetime(2026, 9, 5, 9, 35, tzinfo=NEW_YORK)),
    ("15:55 New York, five minutes before the close", datetime(2026, 9, 5, 15, 55, tzinfo=NEW_YORK)),
    ("09:35 New York the next day, nightly refresh failed", datetime(2026, 9, 6, 9, 35, tzinfo=NEW_YORK)),
]


def main() -> None:
    chain = from_json(FIXTURE)
    print(f"Open interest snapshot taken: {chain.oi_as_of:%Y-%m-%d %H:%M} UTC (after the previous close)")
    print("The chain never changes below. Only the clock moves.\n")
    naive_first = None
    for title, when in MOMENTS:
        print(f"=== {title} ({when.astimezone(timezone.utc):%H:%M} UTC) ===")
        naive = json.dumps(naive_levels(chain, top_n=3))
        naive_first = naive_first or naive
        stamped = levels(chain, when, top_n=3)
        print(f"  naive     -> {naive}")
        print(f"  stamped   -> {to_level_string(stamped)}")
        print(f"  verdict   -> {stamped['freshness'].upper()}, age {stamped['age_hours']}h")
        print(f"               {stamped['freshness_reason']}")
        print(f"  naive line identical to the first one: {'yes' if naive == naive_first else 'no'}\n")
    print("The naive line carries nothing a reader could use to notice it is describing")
    print("yesterday's positioning. The stamped line ages, and says so in words.")


if __name__ == "__main__":
    main()
