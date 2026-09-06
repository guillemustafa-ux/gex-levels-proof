from __future__ import annotations

import json
import os
import subprocess
import sys

from .conftest import FIXTURE, ROOT

ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"}


def run(*args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "gex_levels", "compute", "--fixture", str(FIXTURE), *args]
    return subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True)


def test_cli_prints_the_level_string_and_the_verdict():
    result = run("--as-of", "2026-09-05T13:35:00Z")
    assert result.returncode == 0, result.stderr
    first, second = result.stdout.splitlines()[:2]
    assert first.startswith("v1;asof=20260904T2000Z;spot=5400.00;FLIP=5430.34;CW=5500;PW=5300;L=")
    assert second.startswith("freshness: FRESH (age 17.58h)")


def test_cli_naive_prints_a_payload_with_no_temporal_field():
    result = run("--naive")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload) == {"spot", "flip", "call_wall", "put_wall", "levels"}


def test_cli_writes_pine_seeds_when_asked(tmp_path):
    result = run("--as-of", "2026-09-05T13:35:00Z", "--seeds-out", str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "FLIP.csv").read_text(encoding="utf-8") == "20260904T,5430.34,5430.34,5430.34,5430.34,0\n"
