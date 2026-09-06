"""Gamma flip on hand-built cumulative profiles, independent of Black-Scholes."""

from __future__ import annotations

from gex_levels.compute import gamma_flip


def test_flip_is_interpolated_between_the_bracketing_strikes():
    # cumulative: -10 at 100, -5 at 110, +5 at 120 -> zero halfway between 110 and 120
    assert gamma_flip({100.0: -10.0, 110.0: 5.0, 120.0: 10.0}) == 115.0


def test_flip_interpolation_is_not_the_midpoint_by_default():
    # cumulative: -8 at 100, +2 at 110 -> 100 + 8/10 * 10
    assert gamma_flip({100.0: -8.0, 110.0: 10.0}) == 108.0


def test_no_sign_change_means_no_flip():
    assert gamma_flip({100.0: 1.0, 110.0: 2.0, 120.0: 3.0}) is None


def test_with_several_crossings_the_one_nearest_spot_wins():
    # cumulative: -1, +1, -1, +9 -> crossings at 105, 115 and 121
    profile = {100.0: -1.0, 110.0: 2.0, 120.0: -2.0, 130.0: 10.0}
    assert gamma_flip(profile) == 105.0
    assert gamma_flip(profile, spot=124.0) == 121.0
