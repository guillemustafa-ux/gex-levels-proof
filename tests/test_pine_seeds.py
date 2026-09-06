from __future__ import annotations

import re
from datetime import timedelta

from gex_levels.chain import Chain
from gex_levels.output import levels, to_pine_seeds

from .conftest import NEXT_0935, OPEN_0935

ROW = re.compile(r"^\d{8}T,(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),0$")


def test_one_csv_per_series_in_pine_seeds_row_format(chain, tmp_path):
    d = levels(chain, OPEN_0935)
    written = to_pine_seeds(d, tmp_path)

    assert sorted(p.name for p in written) == ["CALLWALL.csv", "FLIP.csv", "PUTWALL.csv"]
    expected = {"FLIP": d["flip"], "CALLWALL": d["call_wall"], "PUTWALL": d["put_wall"]}
    for path in written:
        rows = path.read_text(encoding="utf-8").splitlines()
        assert len(rows) == 1
        match = ROW.match(rows[0])
        assert match, rows[0]
        assert rows[0].startswith("20260904T,")  # the OI snapshot date, not the run date
        assert {float(v) for v in match.groups()} == {expected[path.stem]}


def test_a_second_day_appends_and_the_same_day_replaces(chain, tmp_path):
    to_pine_seeds(levels(chain, OPEN_0935), tmp_path)
    later = Chain(chain.spot, chain.oi_as_of + timedelta(days=1), chain.quotes)
    to_pine_seeds(levels(later, NEXT_0935), tmp_path)
    to_pine_seeds(levels(later, NEXT_0935), tmp_path)

    rows = (tmp_path / "FLIP.csv").read_text(encoding="utf-8").splitlines()
    assert [r.split(",")[0] for r in rows] == ["20260904T", "20260905T"]


def test_missing_flip_writes_no_row_instead_of_a_fake_zero(chain, tmp_path):
    d = levels(chain, OPEN_0935)
    d["flip"] = None
    to_pine_seeds(d, tmp_path)
    assert (tmp_path / "FLIP.csv").read_text(encoding="utf-8") == ""
    assert (tmp_path / "CALLWALL.csv").read_text(encoding="utf-8").startswith("20260904T,5500,")
