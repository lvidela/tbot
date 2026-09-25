"""Tests for X4 evaluate.py on a synthetic archive. Run: python3 research/x4_lowvol/test_x4.py"""
import json
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("x4_evaluate", os.path.join(HERE, "evaluate.py"))
e4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e4)

x1 = e4.x1
DAY = x1.DAY
T0 = x1.ts(2020, 1, 6) - 203 * DAY


def make_raw(d, n=30, days=900, drift_per_vol=0.0, seed=0, peg=None):
    rng = np.random.default_rng(seed)
    os.makedirs(os.path.join(d, "funding")); os.makedirs(os.path.join(d, "spot"))
    plan = []
    names = ["BTCUSDT"] + [f"A{i}USDT" for i in range(n - 1)]
    btc = rng.normal(0, 0.03, days)
    for j, p in enumerate(names):
        plan.append([p, p])
        sig = 0.001 if p == peg else 0.01 + 0.002 * j
        if p == "BTCUSDT":
            r = btc
        elif p == peg:
            r = rng.normal(0, sig, days)
        else:
            r = 0.5 * btc + rng.normal(0, sig, days) + drift_per_vol * sig
        c = 100 * np.exp(np.cumsum(r))
        rows = [[T0 + k * DAY, c[k], c[k], c[k], c[k], 1.0, 1e6 * (1 + j)] for k in range(days)]
        f = [[T0 + k * DAY + h * 3600, 1e-4] for k in range(days) for h in (0, 8, 16)]
        json.dump({"meta": {}, "rows": rows}, open(os.path.join(d, "spot", f"{p}.json"), "w"))
        json.dump({"meta": {}, "rows": f}, open(os.path.join(d, "funding", f"{p}.json"), "w"))
    json.dump({"planned": plan}, open(os.path.join(d, "_universe_plan.json"), "w"))


def test_features_do_not_look_ahead():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, n=12, days=300)
        P4 = e4.Panel4(x1.Panel(d))
        t = x1.ts(2020, 1, 6)
        before = dict(P4.universe(t)["A3USDT"])
        s = P4.P.spot["A3USDT"]
        s["close"][s["t"] >= t] *= 5.0
        P4b = e4.Panel4(P4.P)
        P4b.P._u = {}
        after = P4b.universe(t)["A3USDT"]
        assert before == after


def test_quasi_peg_excluded():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, n=12, days=300, peg="A2USDT")
        P4 = e4.Panel4(x1.Panel(d))
        U = P4.universe(x1.ts(2020, 1, 6))
        assert "A2USDT" not in U and "A3USDT" in U


def test_planted_lowvol_effect_recovered_and_null_quiet():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, n=40, days=1200, drift_per_vol=-0.12, seed=1)
        P4 = e4.Panel4(x1.Panel(d))
        r = e4.tests(P4, x1.ts(2020, 1, 6), x1.ts(2022, 12, 26))
        assert r["P_ic_vol"]["mean"] < -0.2 and r["P_ic_vol"]["bonferroni_pass_neg"], r["P_ic_vol"]
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, n=40, days=1200, drift_per_vol=0.0, seed=2)
        P4 = e4.Panel4(x1.Panel(d))
        r = e4.tests(P4, x1.ts(2020, 1, 6), x1.ts(2022, 12, 26))
        assert abs(r["P_ic_vol"]["t"]) < 3.0, r["P_ic_vol"]


def test_periods_are_4_weeks_on_grid():
    ps = e4.periods(x1.ts(2024, 1, 1), x1.ts(2024, 6, 1))
    assert ps[0] == x1.ts(2024, 1, 1) and all(b - a == 28 * DAY for a, b in zip(ps, ps[1:]))


if __name__ == "__main__":
    tests = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    for n, f in tests:
        f()
        print("ok ", n)
    print(f"{len(tests)}/{len(tests)} passed")
