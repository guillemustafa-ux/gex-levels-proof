"""Age of the open-interest snapshot, as a verdict rather than a timestamp."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

FRESH = "fresh"
STALE = "stale"


@dataclass(frozen=True)
class Freshness:
    status: str
    age_hours: float
    reason: str


def verdict(oi_as_of: datetime, computed_at: datetime, max_age_hours: float = 24.0) -> Freshness:
    """Fresh while the snapshot is younger than ``max_age_hours``; stale after.

    24h is the default because exchanges publish open interest once per day.
    Anything older means at least one settlement has happened since, so the
    positioning the levels describe is no longer the positioning on the tape.
    """
    if oi_as_of.tzinfo is None or computed_at.tzinfo is None:
        raise ValueError("both timestamps must be timezone-aware")
    age = (computed_at - oi_as_of).total_seconds() / 3600.0
    if age < 0:
        raise ValueError("computed_at is earlier than the OI snapshot")
    age = round(age, 2)
    if age < max_age_hours:
        return Freshness(
            FRESH,
            age,
            f"open interest snapshot is {age}h old, inside the {max_age_hours:g}h window; "
            "it still describes intraday positioning only as of the last settlement",
        )
    return Freshness(
        STALE,
        age,
        f"open interest snapshot is {age}h old, past the {max_age_hours:g}h window; "
        "at least one settlement has happened since. Do not present these levels as live.",
    )
