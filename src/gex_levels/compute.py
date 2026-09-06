"""Gamma exposure per strike and the levels derived from it."""

from __future__ import annotations

from dataclasses import dataclass

from .bs import gamma
from .chain import Chain

CONTRACT_MULTIPLIER = 100
ONE_PERCENT_MOVE = 0.01


@dataclass
class Levels:
    spot: float
    by_strike: dict[float, float]  # strike -> net dollar GEX
    total: float
    flip: float | None  # None when cumulative GEX never crosses zero
    call_wall: float | None
    put_wall: float | None
    top: list[tuple[float, float]]  # (strike, gex) by descending |gex|


def quote_gex(spot: float, strike: float, t_years: float, iv: float, open_interest: int, right: str) -> float:
    """Dollar gamma exposure of one line of the chain.

    GEX = gamma * OI * S^2 * 0.01 * 100

    i.e. the dollar change in dealers' delta hedge for a 1% move, with the
    100-share contract multiplier. Sign follows the standard dealer-positioning
    convention: dealers are assumed long the calls customers sell (positive
    gamma, hedged by selling into strength) and short the puts customers buy
    (negative gamma, hedged by selling into weakness). Getting this sign wrong
    does not produce a slightly different flip; it produces a flip on the
    wrong side of spot.
    """
    sign = 1.0 if right == "C" else -1.0
    return sign * gamma(spot, strike, t_years, iv) * open_interest * spot * spot * ONE_PERCENT_MOVE * CONTRACT_MULTIPLIER


def gex_by_strike(chain: Chain) -> dict[float, float]:
    valuation = chain.oi_as_of.date()
    out: dict[float, float] = {}
    for q in chain.quotes:
        days = (q.expiry - valuation).days
        if days <= 0 or q.open_interest <= 0:
            continue
        out[q.strike] = out.get(q.strike, 0.0) + quote_gex(
            chain.spot, q.strike, days / 365.0, q.iv, q.open_interest, q.right
        )
    return out


NOISE_FLOOR = 0.005  # cumulative GEX must be >= 0.5% of sum(|GEX|) before a crossing counts


def gamma_flip(
    by_strike: dict[float, float], spot: float | None = None, noise_floor: float = NOISE_FLOOR
) -> float | None:
    """Level at which cumulative GEX (ascending strikes) crosses zero.

    Linear interpolation between the two bracketing strikes. When ``spot`` is
    given the crossing nearest to spot is the flip, otherwise the first one.
    None when there is no sign change, which is a legitimate outcome (a chain
    that is net positive, or net negative, at every strike) and must not be
    reported as a level.

    A crossing only counts when the cumulative had already reached at least
    ``noise_floor`` of sum(|GEX|) before it: a flip is positive gamma
    overtaking accumulated negative gamma (or the reverse), so something must
    have accumulated first. Without that floor the far wing, where the
    cumulative starts near zero and wobbles (a few thousand dollars of gamma
    against hundreds of millions near spot), is reported as the flip. Seen
    live on SPY in a net-negative regime: the only zero crossing was 200
    points below spot and drifted further away as more expiries were loaded.
    """
    floor = noise_floor * sum(abs(v) for v in by_strike.values())
    crossings: list[float] = []
    cumulative = 0.0
    prev_strike: float | None = None
    prev_cum = 0.0
    for k in sorted(by_strike):
        cumulative += by_strike[k]
        significant = abs(prev_cum) >= floor
        if prev_strike is not None and prev_cum != 0.0 and (prev_cum < 0) != (cumulative < 0):
            if significant:
                crossings.append(prev_strike + (0.0 - prev_cum) * (k - prev_strike) / (cumulative - prev_cum))
        elif cumulative == 0.0 and prev_strike is not None and significant:
            crossings.append(k)
        prev_strike, prev_cum = k, cumulative
    if not crossings:
        return None
    if spot is None:
        return crossings[0]
    return min(crossings, key=lambda x: abs(x - spot))


def compute_levels(chain: Chain, top_n: int = 10) -> Levels:
    by_strike = gex_by_strike(chain)
    if not by_strike:
        raise ValueError("chain has no live quotes with open interest")
    positives = {k: v for k, v in by_strike.items() if v > 0}
    negatives = {k: v for k, v in by_strike.items() if v < 0}
    ranked = sorted(by_strike.items(), key=lambda kv: abs(kv[1]), reverse=True)
    return Levels(
        spot=chain.spot,
        by_strike=by_strike,
        total=sum(by_strike.values()),
        flip=gamma_flip(by_strike, chain.spot),
        call_wall=max(positives, key=positives.__getitem__) if positives else None,
        put_wall=min(negatives, key=negatives.__getitem__) if negatives else None,
        top=ranked[:top_n],
    )
