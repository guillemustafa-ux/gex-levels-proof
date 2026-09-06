from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from gex_levels.chain import Chain, from_json

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "spx_synthetic_chain.json"

# The fixture's OI snapshot: after the close of 2026-09-04.
OI_AS_OF = datetime(2026, 9, 4, 20, 0, tzinfo=timezone.utc)
NEW_YORK = timezone(timedelta(hours=-4), "EDT")
OPEN_0935 = datetime(2026, 9, 5, 9, 35, tzinfo=NEW_YORK)  # 13:35 UTC, snapshot 17.58h old
CLOSE_1555 = datetime(2026, 9, 5, 15, 55, tzinfo=NEW_YORK)  # 19:55 UTC, snapshot 23.92h old
NEXT_0935 = datetime(2026, 9, 6, 9, 35, tzinfo=NEW_YORK)  # 13:35 UTC next day, 41.58h old

# Pinned from scripts/make_fixture.py; see the docstring there for why these
# three strikes are unambiguous.
FIXTURE_CALL_WALL = 5500.0
FIXTURE_PUT_WALL = 5300.0
FIXTURE_FLIP_BRACKET = (5425.0, 5450.0)


@pytest.fixture
def chain() -> Chain:
    return from_json(FIXTURE)
