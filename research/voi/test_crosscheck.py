"""Tests for crosscheck.py (PREREGISTRATION_V2.md). Run: python3 research/voi/test_crosscheck.py"""
import json
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crosscheck as x  # noqa: E402
import voi_screen as v  # noqa: E402

DAY = x.DAY


def test_align_drops_gappy_asset_and_never_fills():
    t0 = 1_700_000_000 // DAY * DAY
    s = {"LINK": {t0 + i * DAY: 10.0 + i for i in range(10)},
         "BTC": {t0 + i * DAY: 100.0 + i for i in range(10)},
         "GAP": {t0 + i * DAY: 1.0 for i in range(10) if i != 4}}
    kept, dropped, C, grid = x.align(s, t0, t0 + 9 * DAY, ["LINK", "BTC", "GAP", "NONE"])
    assert kept == ["LINK", "BTC"] and dropped == ["GAP", "NONE"]
    assert C.shape == (2, 10) and len(grid) == 10


def test_align_window_excludes_bars_after_end():
    t0 = 1_700_000_000 // DAY * DAY
    s = {"LINK": {t0 + i * DAY: 1.0 + i for i in range(12)}}   # bars 10, 11 beyond END (partial)
    _, _, C, _ = x.align(s, t0, t0 + 9 * DAY, ["LINK"])
    assert C.shape[1] == 10 and C[0, -1] == 10.0


def test_params_invariant_to_asset_order():
    rng = np.random.default_rng(1)
    C = np.exp(np.cumsum(rng.normal(0, 0.04, (5, 300)), axis=1))
    names = ["LINK", "A", "B", "C", "D"]
    p1 = x.params(names, C)
    perm = [3, 0, 4, 1, 2]
    p2 = x.params([names[i] for i in perm], C[perm])
    assert abs(p1["sigma_x"] - p2["sigma_x"]) < 1e-12 and abs(p1["rho"] - p2["rho"]) < 1e-12


def test_params_matches_f4_estimator_on_kraken_file():
    """The aligned-matrix estimator must equal voi_screen.ledger_params on F4's own data."""
    f4 = v.ledger_params()
    data = x.load_venue("kraken")
    first = min(data["LINK"])
    last = max(data["LINK"])
    kept, dropped, C, _ = x.align(data, first, last, [x.BASE[k] for k in x.KRAKEN])
    assert not dropped
    p = x.params(kept, C)
    assert abs(p["sigma_x"] - f4["sigma_x"]) < 1e-12, (p["sigma_x"], f4["sigma_x"])
    assert abs(p["rho"] - f4["rho"]) < 1e-12
    assert abs(p["link_daily_sd"] - f4["link_daily_sd"]) < 1e-12


def test_rerun_reproduces_f4_results_with_f4_params():
    f4 = json.load(open(os.path.join(os.path.dirname(v.OUT), "voi.json")))
    r = x.rerun(f4["ledger"], {"H20": 20, "H365": 365})
    for cand, row in f4["candidates"].items():
        for hz in ("H20", "H365"):
            for s in v.SCEN:
                for k in ("evpi", "evsi"):
                    assert abs(r[cand][hz][s][k] - row[hz][s][k]) < 1e-12, (cand, hz, s, k)


def test_load_venue_reads_raw_rows():
    with tempfile.TemporaryDirectory() as d:
        json.dump({"meta": {}, "rows": [[86400, 1, 2, 0.5, 1.5, 9]]},
                  open(os.path.join(d, "coinbase_LINK_1d.json"), "w"))
        out = x.load_venue("coinbase", raw=d)
    assert out == {"LINK": {86400: 1.5}}


if __name__ == "__main__":
    tests = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    for n, f in tests:
        f()
        print("ok ", n)
    print(f"{len(tests)}/{len(tests)} passed")
