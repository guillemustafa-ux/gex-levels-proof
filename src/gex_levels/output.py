"""The two payloads under test, and the two delivery formats for TradingView.

Level string format (version 1), one line, no whitespace:

    v1;asof=20260904T2000Z;spot=5400.00;FLIP=5387.5;CW=5450;PW=5300;L=5425:1.2e9,5375:-8.01e8

Fields, separated by ';', each 'KEY=value':

    v1      format version, always first
    asof    open-interest snapshot time, UTC, YYYYMMDDTHHMMZ
    spot    underlying price used for the computation, two decimals
    FLIP    gamma-flip level (interpolated), or 'na' when cumulative GEX
            never crosses zero
    CW      call wall: strike with the largest positive GEX
    PW      put wall: strike with the most negative GEX
    L       top-N strikes by |GEX| in descending order, 'strike:gex' pairs
            separated by ','; gex is signed, 4 significant digits, exponent
            notation without '+' or leading zeros ('1.234e9', '-8.01e8')

Numbers carry no thousands separators. The Pine indicator splits on ';', '=',
',' and ':' and parses the mantissa and exponent of the gex separately, so the
grammar is deliberately tiny. parse_level_string() below is the Python mirror
of that Pine parser and is what the tests hold to the contract.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

from .chain import Chain, parse_utc
from .compute import compute_levels
from .freshness import verdict

VERSION = "v1"
_ASOF_FORMAT = "%Y%m%dT%H%MZ"
_ASOF_RE = re.compile(r"^\d{8}T\d{4}Z$")
_SEEDS_SERIES = ("FLIP", "CALLWALL", "PUTWALL")


def _sig4(x: float) -> float:
    """Round to 4 significant digits so the dict and the string agree exactly."""
    return float(f"{x:.3e}")


def _fmt_num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else repr(float(x))


def _fmt_sci(x: float) -> str:
    if x == 0:
        return "0"
    mantissa, exponent = f"{x:.3e}".split("e")
    return f"{mantissa}e{int(exponent)}"


def _fmt_level(x: float | None) -> str:
    return "na" if x is None else _fmt_num(x)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _core(chain: Chain, top_n: int) -> dict:
    lv = compute_levels(chain, top_n=top_n)
    return {
        "spot": float(f"{chain.spot:.2f}"),
        "flip": None if lv.flip is None else round(lv.flip, 2),
        "call_wall": lv.call_wall,
        "put_wall": lv.put_wall,
        "levels": [{"strike": k, "gex": _sig4(g)} for k, g in lv.top],
    }


def naive_levels(chain: Chain, top_n: int = 10) -> dict:
    """The tutorial-shaped payload: levels and nothing about when the OI was taken.

    This is the anti-pattern. It is kept on purpose so the tests can show that
    it is byte-identical at 09:35 and at 15:55 on the same stale snapshot.
    """
    return _core(chain, top_n)


def levels(chain: Chain, computed_at: datetime, top_n: int = 10, max_age_hours: float = 24.0) -> dict:
    """Same levels, plus when the OI was captured, when this ran, and a verdict."""
    fresh = verdict(chain.oi_as_of, computed_at, max_age_hours)
    out = {"version": VERSION, "oi_as_of": _iso_z(chain.oi_as_of)}
    out.update(_core(chain, top_n))
    out.update(
        {
            "computed_at": _iso_z(computed_at),
            "age_hours": fresh.age_hours,
            "freshness": fresh.status,
            "freshness_reason": fresh.reason,
        }
    )
    return out


def to_level_string(d: dict) -> str:
    as_of = parse_utc(d["oi_as_of"]).strftime(_ASOF_FORMAT)
    pairs = ",".join(f"{_fmt_num(l['strike'])}:{_fmt_sci(l['gex'])}" for l in d["levels"])
    return ";".join(
        [
            VERSION,
            f"asof={as_of}",
            f"spot={d['spot']:.2f}",
            f"FLIP={_fmt_level(d['flip'])}",
            f"CW={_fmt_level(d['call_wall'])}",
            f"PW={_fmt_level(d['put_wall'])}",
            f"L={pairs}",
        ]
    )


def _num(text: str, field: str) -> float:
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{field}: not a number: {text!r}") from exc


def _level(text: str, field: str) -> float | None:
    return None if text == "na" else _num(text, field)


def parse_level_string(s: str) -> dict:
    """Python mirror of the Pine parser. Raises ValueError on anything malformed."""
    if not s or re.search(r"\s", s):
        raise ValueError("level string must be non-empty and contain no whitespace")
    fields = s.split(";")
    if fields[0] != VERSION:
        raise ValueError(f"unsupported version prefix: {fields[0]!r}")
    kv: dict[str, str] = {}
    for f in fields[1:]:
        if "=" not in f:
            raise ValueError(f"field without '=': {f!r}")
        key, value = f.split("=", 1)
        kv[key] = value
    missing = {"asof", "spot", "FLIP", "CW", "PW", "L"} - kv.keys()
    if missing:
        raise ValueError(f"missing fields: {sorted(missing)}")
    if not _ASOF_RE.match(kv["asof"]):
        raise ValueError(f"asof must be YYYYMMDDTHHMMZ, got {kv['asof']!r}")
    as_of = datetime.strptime(kv["asof"], _ASOF_FORMAT).replace(tzinfo=timezone.utc)

    levels_out = []
    if kv["L"]:
        for item in kv["L"].split(","):
            if item.count(":") != 1:
                raise ValueError(f"level entry must be strike:gex, got {item!r}")
            strike, gex = item.split(":")
            levels_out.append({"strike": _num(strike, "L.strike"), "gex": _num(gex, "L.gex")})

    return {
        "version": VERSION,
        "oi_as_of": _iso_z(as_of),
        "spot": _num(kv["spot"], "spot"),
        "flip": _level(kv["FLIP"], "FLIP"),
        "call_wall": _level(kv["CW"], "CW"),
        "put_wall": _level(kv["PW"], "PW"),
        "levels": levels_out,
    }


def to_pine_seeds(d: dict, out_dir: str | Path) -> list[Path]:
    """Write one Pine Seeds CSV per series: FLIP.csv, CALLWALL.csv, PUTWALL.csv.

    Row format is the one Pine Seeds ingests, ``YYYYMMDDT,open,high,low,close,volume``,
    with all four prices equal to the level and volume 0. The row date is the
    OI snapshot date, not the run date: the level describes positioning as of
    that settlement. Existing rows for other dates are kept and the file is
    re-sorted, so a daily cron produces a proper series. A series whose level
    is None for the day gets no row rather than a fake zero.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    day = parse_utc(d["oi_as_of"]).strftime("%Y%m%dT")
    values = {"FLIP": d["flip"], "CALLWALL": d["call_wall"], "PUTWALL": d["put_wall"]}
    written: list[Path] = []
    for series in _SEEDS_SERIES:
        level = values[series]
        path = out / f"{series}.csv"
        rows: dict[str, list[str]] = {}
        if path.exists():
            with path.open(newline="", encoding="utf-8") as fh:
                for row in csv.reader(fh):
                    if row:
                        rows[row[0]] = row
        if level is not None:
            v = _fmt_num(level)
            rows[day] = [day, v, v, v, v, "0"]
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            for key in sorted(rows):
                writer.writerow(rows[key])
        written.append(path)
    return written
