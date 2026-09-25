"""Tests for X1 evaluate.py on a synthetic archive. Run: python3 research/x1_funding/test_x1.py"""
import json
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evaluate as e  # noqa: E402

DAY = e.DAY
T0 = e.ts(2020, 1, 6) - 203 * DAY   # Monday-aligned


def make_raw(d, n_assets=30, days=600, beta=0.0, seed=0, delist=None):
    """Planted structure: funding is constant within each Monday-aligned week block b; the daily
    drift in block b is beta * funding of block b-1 (what the signal at the block start sees)."""
    rng = np.random.default_rng(seed)
    os.makedirs(os.path.join(d, "funding")); os.makedirs(os.path.join(d, "spot"))
    plan = []
    for i in range(n_assets):
        p = f"A{i}USDT"
        plan.append([p, p])
        fb = rng.normal(0, 1e-3, days // 7 + 2)
        f_rows, s_rows, price = [], [], 100.0
        for k in range(days):
            t, b = T0 + k * DAY, k // 7
            for h in (0, 8, 16):
                f_rows.append([t + h * 3600, float(fb[b])])
            price *= float(np.exp(rng.normal(0, 0.02) + (beta * fb[b - 1] if b > 0 else 0.0)))
            if delist and p == delist[0] and t >= delist[1]:
                continue
            s_rows.append([t, price, price, price, price, 1.0, 1e6 * (1 + i)])
        json.dump({"meta": {}, "rows": f_rows}, open(os.path.join(d, "funding", f"{p}.json"), "w"))
        json.dump({"meta": {}, "rows": s_rows}, open(os.path.join(d, "spot", f"{p}.json"), "w"))
    json.dump({"planned": plan}, open(os.path.join(d, "_universe_plan.json"), "w"))


def test_features_do_not_look_ahead():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, n_assets=3, days=200)
        P = e.Panel(d)
        t = T0 + 120 * DAY
        before = P.features("A0USDT", t)
        s = P.spot["A0USDT"]
        s["close"][s["t"] >= t] *= 10.0          # corrupt every bar opened at/after t
        f = P.fund["A0USDT"]
        f[f[:, 0] > t, 1] = 9.9                  # corrupt every funding print after t
        after = P.features("A0USDT", t)
        assert before == after, (before, after)


def test_delisted_asset_keeps_last_close():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, n_assets=2, days=200, delist=("A1USDT", T0 + 150 * DAY))
        P = e.Panel(d)
        t = T0 + 147 * DAY
        r = P.fwd("A1USDT", t, 7 * DAY)
        s = P.spot["A1USDT"]
        c0 = s["close"][s["t"] == t - DAY][0]
        assert abs(r - np.log(s["close"][-1] / c0)) < 1e-12


def test_first_week_pays_full_entry_cost():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, n_assets=12, days=400)
        P = e.Panel(d)
        lo = e.ts(2020, 1, 6)
        g = e.backtest(P, lo, lo, 3, 0.0)
        n = e.backtest(P, lo, lo, 3, 0.01)
        assert abs((g[0] - n[0]) - 0.01) < 1e-12   # turnover 1.0 into cash-free start


def test_planted_negative_effect_is_recovered_and_null_is_not():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, n_assets=40, days=900, beta=-15.0, seed=3)
        P = e.Panel(d)
        r = e.tests(P, e.ts(2020, 1, 6), e.ts(2021, 12, 27))
        assert r["P_ic_7d"]["mean"] < -0.1 and r["P_ic_7d"]["bonferroni_pass_neg"], r["P_ic_7d"]
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, n_assets=40, days=900, beta=0.0, seed=4)
        P = e.Panel(d)
        r = e.tests(P, e.ts(2020, 1, 6), e.ts(2021, 12, 27))
        assert abs(r["P_ic_7d"]["t"]) < 3.0, r["P_ic_7d"]


def test_universe_capped_and_ranked_by_past_volume():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, n_assets=60, days=200)
        P = e.Panel(d)
        U = P.universe(T0 + 150 * DAY)
        assert len(U) == e.TOPN
        assert "A59USDT" in U and "A0USDT" not in U   # quote volume increases with index


if __name__ == "__main__":
    tests = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    for n, f in tests:
        f()
        print("ok ", n)
    print(f"{len(tests)}/{len(tests)} passed")
