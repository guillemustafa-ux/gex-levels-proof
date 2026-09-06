from __future__ import annotations

import pytest

from gex_levels.bs import gamma

SPOT, T, IV = 5400.0, 30 / 365, 0.15


def test_gamma_is_positive_at_the_money():
    assert gamma(SPOT, SPOT, T, IV) > 0


def test_gamma_peaks_near_the_money():
    atm = gamma(SPOT, SPOT, T, IV)
    assert atm > gamma(SPOT, SPOT * 1.03, T, IV)
    assert atm > gamma(SPOT, SPOT * 0.97, T, IV)


def test_gamma_vanishes_far_out_of_the_money():
    assert gamma(SPOT, SPOT * 1.5, T, IV) < 1e-12
    assert gamma(SPOT, SPOT * 0.5, T, IV) < 1e-12


def test_expired_or_zero_vol_has_no_gamma():
    assert gamma(SPOT, SPOT, 0.0, IV) == 0.0
    assert gamma(SPOT, SPOT, T, 0.0) == 0.0


def test_non_positive_prices_are_rejected():
    with pytest.raises(ValueError):
        gamma(0.0, SPOT, T, IV)
