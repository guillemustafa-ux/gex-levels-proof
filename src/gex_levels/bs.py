"""Black-Scholes gamma. Pure function, no dependencies."""

from __future__ import annotations

import math

_SQRT_2PI = math.sqrt(2.0 * math.pi)


def gamma(spot: float, strike: float, t_years: float, iv: float, r: float = 0.0) -> float:
    """Gamma of a European option per unit of underlying.

    gamma = N'(d1) / (S * sigma * sqrt(T)), with
    d1 = (ln(S/K) + (r + sigma^2 / 2) T) / (sigma sqrt(T)).

    Calls and puts share the same gamma, which is why the sign of a position's
    exposure comes from who holds it (see compute.py), not from the formula.
    Dividends are ignored: for an index-level proof the effect on the location
    of the levels is well inside the noise of the OI snapshot itself.
    """
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if t_years <= 0 or iv <= 0:
        return 0.0
    vol_t = iv * math.sqrt(t_years)
    d1 = (math.log(spot / strike) + (r + 0.5 * iv * iv) * t_years) / vol_t
    pdf = math.exp(-0.5 * d1 * d1) / _SQRT_2PI
    return pdf / (spot * vol_t)
