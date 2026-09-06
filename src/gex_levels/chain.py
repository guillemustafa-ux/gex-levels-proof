"""Option chain model and loaders."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class OptionQuote:
    strike: float
    expiry: date
    right: str  # "C" or "P"
    open_interest: int
    iv: float

    def __post_init__(self) -> None:
        if self.right not in ("C", "P"):
            raise ValueError(f"right must be 'C' or 'P', got {self.right!r}")


@dataclass
class Chain:
    spot: float
    # When the open-interest snapshot was taken. This is the field the naive
    # pipeline throws away.
    oi_as_of: datetime
    quotes: list[OptionQuote] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.oi_as_of.tzinfo is None:
            raise ValueError("oi_as_of must be timezone-aware")


def parse_utc(value: str) -> datetime:
    """Accepts '2026-09-04T20:00:00Z' or any ISO-8601 with an offset."""
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp has no timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def from_json(path: str | Path) -> Chain:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    quotes = [
        OptionQuote(
            strike=float(q["strike"]),
            expiry=date.fromisoformat(q["expiry"]),
            right=q["right"],
            open_interest=int(q["open_interest"]),
            iv=float(q["iv"]),
        )
        for q in raw["quotes"]
    ]
    return Chain(spot=float(raw["spot"]), oi_as_of=parse_utc(raw["oi_as_of"]), quotes=quotes)


def to_json(chain: Chain, path: str | Path) -> None:
    payload = {
        "spot": chain.spot,
        "oi_as_of": chain.oi_as_of.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quotes": [
            {
                "strike": q.strike,
                "expiry": q.expiry.isoformat(),
                "right": q.right,
                "open_interest": q.open_interest,
                "iv": q.iv,
            }
            for q in chain.quotes
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")


def from_yfinance(ticker: str, expiries: int = 2) -> Chain:
    """Load the nearest ``expiries`` expirations from Yahoo Finance.

    Yahoo does not expose when its open-interest figure was captured. OI on
    Yahoo reflects the previous session's settlement, so the snapshot time is
    taken as the most recent 20:00 UTC (16:00 New York during daylight time)
    strictly before now. That is an assumption, and it is stamped as such in
    the reason text downstream; a vendor that publishes the snapshot time
    should replace this.
    """
    try:
        import yfinance  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "yfinance is not installed. Install the optional extra: pip install -e '.[live]'"
        ) from exc

    tk = yfinance.Ticker(ticker)
    spot = float(tk.fast_info["last_price"])
    now = datetime.now(timezone.utc)
    as_of = now.replace(hour=20, minute=0, second=0, microsecond=0)
    if as_of >= now:
        as_of -= timedelta(days=1)

    quotes: list[OptionQuote] = []
    for expiry_text in list(tk.options)[:expiries]:
        expiry = date.fromisoformat(expiry_text)
        chain = tk.option_chain(expiry_text)
        for right, frame in (("C", chain.calls), ("P", chain.puts)):
            for row in frame.itertuples(index=False):
                oi = getattr(row, "openInterest", 0)
                iv = getattr(row, "impliedVolatility", 0.0)
                if oi != oi or iv != iv:  # NaN guard without numpy
                    continue
                quotes.append(
                    OptionQuote(
                        strike=float(row.strike),
                        expiry=expiry,
                        right=right,
                        open_interest=int(oi),
                        iv=float(iv),
                    )
                )
    return Chain(spot=spot, oi_as_of=as_of, quotes=quotes)
