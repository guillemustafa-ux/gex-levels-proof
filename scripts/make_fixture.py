"""Deterministic synthetic SPX-like chain. Regenerate with: python scripts/make_fixture.py

Designed so the three headline levels are unambiguous:
  * call wall at 5500: a large call OI block on a round strike above spot;
  * put wall at 5300: the mirror block below spot;
  * gamma flip a little above spot, where put-dominated negative GEX below
    gives way to call-dominated positive GEX above.
Round strikes carry double the base OI, as they do on the real board.
"""

from __future__ import annotations

import math
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gex_levels.chain import Chain, OptionQuote, to_json  # noqa: E402

SEED = 20260905
BASE_DATE = date(2026, 9, 5)
OI_AS_OF = datetime(2026, 9, 4, 20, 0, tzinfo=timezone.utc)
SPOT = 5400.0
STRIKES = [float(k) for k in range(5000, 5801, 25)]
EXPIRIES = [BASE_DATE + timedelta(days=7), BASE_DATE + timedelta(days=30)]
CALL_WALL, CALL_WALL_OI = 5500.0, 6000
PUT_WALL, PUT_WALL_OI = 5300.0, 2000
# Below spot puts carry less OI than calls above it, so the chain is net long
# gamma and the cumulative sum crosses zero once, just above spot.
PUT_WEIGHT_BELOW_SPOT = 0.35


def smile(strike: float, days: int) -> float:
    m = (strike - SPOT) / SPOT
    # Put skew: lower strikes trade richer; the front expiry a touch richer still.
    return round(0.14 + 0.4 * abs(m) + 2.0 * m * m - 0.15 * m + (0.02 if days <= 7 else 0.0), 4)


def base_oi(strike: float) -> float:
    oi = 800.0 * math.exp(-(((strike - SPOT) / 150.0) ** 2)) + 100.0
    return oi * 2.0 if strike % 100 == 0 else oi


def build() -> Chain:
    rng = random.Random(SEED)
    quotes: list[OptionQuote] = []
    for expiry in EXPIRIES:
        days = (expiry - BASE_DATE).days
        for k in STRIKES:
            iv = smile(k, days)
            call = base_oi(k) * (1.0 if k >= SPOT else 0.3) + (CALL_WALL_OI if k == CALL_WALL else 0)
            put = base_oi(k) * (PUT_WEIGHT_BELOW_SPOT if k <= SPOT else 0.3) + (PUT_WALL_OI if k == PUT_WALL else 0)
            quotes.append(OptionQuote(k, expiry, "C", int(call * rng.uniform(0.85, 1.15)), iv))
            quotes.append(OptionQuote(k, expiry, "P", int(put * rng.uniform(0.85, 1.15)), iv))
    return Chain(spot=SPOT, oi_as_of=OI_AS_OF, quotes=quotes)


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "data" / "spx_synthetic_chain.json"
    target.parent.mkdir(exist_ok=True)
    to_json(build(), target)
    print(f"wrote {target}")
