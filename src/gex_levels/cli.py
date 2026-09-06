"""python -m gex_levels compute --fixture data/spx_synthetic_chain.json"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from .chain import from_json, from_yfinance, parse_utc
from .output import levels, naive_levels, to_level_string, to_pine_seeds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gex_levels")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compute", help="compute levels and print the TradingView level string")
    src = c.add_mutually_exclusive_group(required=True)
    src.add_argument("--fixture", help="path to a chain JSON (see data/)")
    src.add_argument("--ticker", help="load the chain from Yahoo Finance (requires the 'live' extra)")
    c.add_argument("--as-of", help="computed_at, ISO-8601 with offset (default: now UTC)")
    c.add_argument("--top", type=int, default=10, help="extra levels to carry in the string")
    c.add_argument("--seeds-out", help="directory to write Pine Seeds CSVs into")
    c.add_argument("--naive", action="store_true", help="print the payload without temporal fields")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    chain = from_json(args.fixture) if args.fixture else from_yfinance(args.ticker)
    if args.naive:
        print(json.dumps(naive_levels(chain, top_n=args.top)))
        return 0
    computed_at = parse_utc(args.as_of) if args.as_of else datetime.now(timezone.utc)
    d = levels(chain, computed_at, top_n=args.top)
    print(to_level_string(d))
    print(f"freshness: {d['freshness'].upper()} (age {d['age_hours']}h) - {d['freshness_reason']}")
    if args.seeds_out:
        for path in to_pine_seeds(d, args.seeds_out):
            print(f"seeds: wrote {path}")
    return 0
