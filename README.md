# gex-levels-proof

Gamma-exposure levels for TradingView, built around the failure that makes
most GEX overlays quietly wrong: **open interest is published once a day, and a
naive pipeline presents yesterday's OI as "live" all session long -- while a
sloppy sign convention puts the gamma flip on the wrong side of spot.**

## What this proves

Two functions compute the same levels from the same option chain:

* `naive_levels()` returns spot, flip, call wall, put wall and the top strikes.
  Nothing else. It is the tutorial-shaped payload.
* `levels()` returns the same numbers plus `oi_as_of`, `computed_at`,
  `age_hours` and a `freshness` verdict (`fresh` / `stale`) with the reason
  in words.

`test_naive_output_presents_stale_oi_as_live` asserts that the naive payload
carries **no temporal field at all** and is **byte-identical at 09:35 and at
15:55** on a snapshot taken before the session opened. A chart, a model or a
person reading it cannot tell whether the positioning it describes is one hour
or one weekend old. `test_stamped_output_changes_verdict_over_time` asserts the
other payload ages, and flips to `stale` once a settlement has happened since.

Everything runs offline: no TradingView account, no vendor key, no network.
The chain is a committed synthetic fixture.

## Run it

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -v
python scripts/drill.py
```

```text
tests/test_bs.py::test_gamma_is_positive_at_the_money PASSED
tests/test_bs.py::test_gamma_peaks_near_the_money PASSED
tests/test_bs.py::test_gamma_vanishes_far_out_of_the_money PASSED
tests/test_bs.py::test_expired_or_zero_vol_has_no_gamma PASSED
tests/test_bs.py::test_non_positive_prices_are_rejected PASSED
tests/test_cli.py::test_cli_prints_the_level_string_and_the_verdict PASSED
tests/test_cli.py::test_cli_naive_prints_a_payload_with_no_temporal_field PASSED
tests/test_cli.py::test_cli_writes_pine_seeds_when_asked PASSED
tests/test_compute.py::test_calls_are_positive_and_puts_are_negative_with_equal_magnitude PASSED
tests/test_compute.py::test_same_strike_across_rights_and_expiries_aggregates_into_one_level PASSED
tests/test_compute.py::test_expired_and_zero_oi_quotes_do_not_contribute PASSED
tests/test_compute.py::test_fixture_call_wall_and_put_wall_are_the_planted_strikes PASSED
tests/test_compute.py::test_fixture_flip_sits_between_the_two_bracketing_strikes PASSED
tests/test_compute.py::test_top_levels_are_ranked_by_absolute_gex PASSED
tests/test_flip.py::test_flip_is_interpolated_between_the_bracketing_strikes PASSED
tests/test_flip.py::test_flip_interpolation_is_not_the_midpoint_by_default PASSED
tests/test_flip.py::test_no_sign_change_means_no_flip PASSED
tests/test_flip.py::test_with_several_crossings_the_one_nearest_spot_wins PASSED
tests/test_freshness.py::test_under_24h_is_fresh_and_says_how_old PASSED
tests/test_freshness.py::test_still_fresh_minutes_before_the_window_closes PASSED
tests/test_freshness.py::test_past_24h_is_stale_with_the_instruction_in_words PASSED
tests/test_freshness.py::test_exactly_at_the_window_is_stale PASSED
tests/test_freshness.py::test_naive_datetimes_are_refused PASSED
tests/test_level_string.py::test_round_trip_is_lossless PASSED
tests/test_level_string.py::test_readme_example_parses_as_documented PASSED
tests/test_level_string.py::test_absent_flip_travels_as_na PASSED
tests/test_level_string.py::test_string_has_no_whitespace_and_fits_a_tradingview_input PASSED
tests/test_level_string.py::test_malformed_input_is_rejected[...] PASSED  (8 cases)
tests/test_naive_ab.py::test_naive_output_presents_stale_oi_as_live PASSED
tests/test_naive_ab.py::test_stamped_output_changes_verdict_over_time PASSED
tests/test_pine_seeds.py::test_one_csv_per_series_in_pine_seeds_row_format PASSED
tests/test_pine_seeds.py::test_a_second_day_appends_and_the_same_day_replaces PASSED
tests/test_pine_seeds.py::test_missing_flip_writes_no_row_instead_of_a_fake_zero PASSED

40 passed
```

The drill prints the naive and the stamped output side by side at 09:35 and
15:55 New York on the same OI snapshot, then the next morning after a failed
nightly refresh. The naive line never changes. The stamped line ages, and says
so.

## The two delivery paths into TradingView

Pine Script cannot call an external API at runtime. There are exactly two
supported ways to get externally computed numbers onto a chart, and this repo
produces both from one computation:

| Path | Cadence | Human step | What it is good for |
|------|---------|------------|---------------------|
| **Level string** pasted into an indicator input | whenever you paste | yes, one paste per refresh | intraday levels from the freshest OI you have |
| **Pine Seeds** CSVs in a GitHub repo, read with `request.seed()` | end of day (TradingView ingests once a day) | none after setup | an automatic daily baseline |

The honest limitation: **Seeds is EOD-only** and **the string is a paste
step**. Anything that promises fully automatic intraday updates inside Pine is
a browser hack (an extension typing into the input box, an unofficial API) and
is not something a client should depend on. Since OI itself is refreshed
overnight by the exchange, the daily Seeds path is not as limiting as it
sounds: it delivers exactly what the data vendor delivers. The string path
exists for the case where the client pays for an intraday OI source.

```bash
# level string + freshness verdict, and the three Seeds CSVs into out/
python -m gex_levels compute --fixture data/spx_synthetic_chain.json --as-of 2026-09-05T13:35:00Z --seeds-out out/
# the anti-pattern, for comparison
python -m gex_levels compute --fixture data/spx_synthetic_chain.json --naive
```

`to_pine_seeds()` writes `FLIP.csv`, `CALLWALL.csv` and `PUTWALL.csv` in the
row format Seeds ingests (`YYYYMMDDT,open,high,low,close,volume`, all four
prices equal to the level, volume 0). The row is dated by the **OI snapshot**,
not by the run: the level describes positioning as of that settlement.
Registering the repo with Pine Seeds and the `symbol_info` JSON are TradingView
setup steps outside this repo.

## Level string format

```text
v1;asof=20260904T2000Z;spot=5400.00;FLIP=5387.5;CW=5450;PW=5300;L=5425:1.2e9,5375:-8.01e8
```

One line, no whitespace, fields separated by `;`, each `KEY=value`:

| Field | Meaning |
|-------|---------|
| `v1` | format version, always first |
| `asof` | OI snapshot time, UTC, `YYYYMMDDTHHMMZ` |
| `spot` | underlying price used for the computation, two decimals |
| `FLIP` | gamma flip (interpolated), or `na` when cumulative GEX never crosses zero |
| `CW` | call wall: strike with the largest positive GEX |
| `PW` | put wall: strike with the most negative GEX |
| `L` | top-N strikes by \|GEX\|, descending, as `strike:gex` pairs separated by `,`; gex is signed, 4 significant digits, `1.234e9` / `-8.01e8` |

Top-10 levels fit in about 200 characters, comfortably inside a TradingView
string input. `parse_level_string()` is the Python mirror of the Pine parser;
`test_level_string.py` holds it to a lossless round trip and rejects malformed
input with `ValueError`. The Pine side splits on `;`, `=`, `,` and `:` and
parses the mantissa and exponent of each gex separately, so nothing depends on
`str.tonumber()` accepting exponent notation.

## Sign convention and formula

Per line of the chain:

```text
GEX = gamma * OI * S^2 * 0.01 * 100
```

`gamma` is Black-Scholes gamma per unit of underlying, `OI` the open interest
in contracts, `S` spot, `0.01` scales to a 1% move and `100` is the contract
multiplier. The result is the dollar change in dealers' delta hedge for a 1%
move.

```text
gamma = N'(d1) / (S * sigma * sqrt(T))
d1    = (ln(S/K) + (r + sigma^2 / 2) T) / (sigma sqrt(T))
```

**Calls count positive, puts negative.** This is the standard dealer
positioning convention: dealers are assumed long the calls customers sell
(positive gamma, they sell strength and buy weakness) and short the puts
customers buy (negative gamma, they do the opposite). Calls and puts share the
same Black-Scholes gamma, so the sign comes entirely from this assumption.
Getting it wrong does not shift the flip a little; it puts it on the wrong side
of spot, which is why `test_calls_are_positive_and_puts_are_negative_with_equal_magnitude`
exists.

Derived levels:

* **by strike**: sum of signed GEX over rights and expiries at that strike;
* **gamma flip**: where cumulative GEX over ascending strikes crosses zero,
  linearly interpolated between the two bracketing strikes. With more than one
  crossing (a thin, noisy wing can produce one) the crossing nearest spot is
  used. No crossing means no flip, reported as `na`, never as a number;
* **call wall**: strike with the largest positive GEX;
* **put wall**: strike with the most negative GEX;
* **extra levels**: the top-N strikes by absolute GEX.

`r` defaults to 0 and dividends are ignored; for the location of these levels
both effects are well inside the noise of the OI snapshot itself.

## Pine indicator

`pine/gex_levels.pine` is a Pine v6 overlay:

1. Paste the CLI's first output line into the **Level string** input.
2. The indicator draws the flip (yellow), call wall (green), put wall (red)
   and the extra levels (teal for positive, orange for negative, opacity by
   \|GEX\| rank), each extended to the right with a label.
3. A small table shows the OI snapshot time and its age against `timenow`,
   and turns red with a **STALE** notice past the configurable threshold
   (default 24h). A string without `asof` is treated as stale.
4. Three `alertcondition()`s fire when price crosses the flip, the call wall
   or the put wall.
5. An optional **Pine Seeds** overlay draws yesterday's flip and walls from the
   CSVs written by `to_pine_seeds()`, as step lines. It is off by default and
   commented as EOD-only in the source.

All drawing objects are deleted and recreated on the last bar only, so the
live object count stays at 3 + N, well under TradingView's 500 cap.

The Pine file is **validated by hand on TradingView, not in CI**: paste it
into the Pine editor and check it on a chart before relying on it. What CI
does pin is the contract it depends on: the level string grammar, via the
Python mirror parser. If the string round-trips in Python, the Pine parser has
nothing surprising to handle.

## Data sources

* **Synthetic fixture (committed).** `data/spx_synthetic_chain.json` is a
  deterministic SPX-like chain from `scripts/make_fixture.py`: spot 5400,
  strikes 5000 to 5800 in steps of 25, two expiries (7 and 30 days from
  2026-09-05), a put-skewed IV smile, OI concentrated near the money and on
  round strikes, with a planted call wall at 5500 and put wall at 5300 so the
  expected levels are unambiguous. `oi_as_of` is `2026-09-04T20:00:00Z`.
* **yfinance (optional).** `pip install -e ".[live]"` and
  `python -m gex_levels compute --ticker SPY`. Yahoo does not expose when its
  OI figure was captured; the loader assumes the most recent weekday 20:00 UTC
  before now (a Sunday run stamps Friday's settlement, not Saturday's) and
  documents that assumption in code. The assumption is unit-tested; the
  network call is not.
* **Most vendors refresh OI overnight.** That is the whole reason the
  freshness stamp exists. An intraday OI source is a paid subscription and the
  client's decision; this repo makes the age of whatever source is used
  visible, it does not manufacture freshness.

## Deliberately out of scope

* **No dealer-positioning model beyond the standard convention.** No
  customer-flow inference, no per-strike sign heuristics, no vanna/charm. The
  convention is documented and tested; refinements are a modelling decision
  for the client.
* **No intraday open interest.** The freshness verdict measures the age of the
  snapshot; it cannot make the snapshot younger.
* **No vendor integration.** yfinance is an optional convenience for a
  smoke run, not a data source anyone should trade from. Loading from a paid
  chain is a `Chain(...)` constructor call.
* **No automatic push into TradingView.** The string is pasted, Seeds is
  pulled daily by TradingView. Anything else is not a supported path.
* **No market calendar.** The 24h threshold is a proxy for "one settlement has
  happened"; weekends and holidays make a Friday snapshot legitimately older
  on Monday morning. Deciding what to do with that is the operator's call.

## Status

Built as a proof, not operated in production. The Python side is tested
offline on Linux and Windows, Python 3.11 and 3.12. The Pine indicator is not
compiled anywhere in this repo; it is kept deliberately small and commented so
that a manual check on TradingView is a five-minute job, not a debugging
session.

## Licence

MIT.
