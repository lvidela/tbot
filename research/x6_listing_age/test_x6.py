"""Tests for X6 evaluate.py. Run: python3 research/x6_listing_age/test_x6.py"""
import importlib.util
import json
import os
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("x6_evaluate", os.path.join(HERE, "evaluate.py"))
e = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e)
x1, x4 = e.x1, e.x4
DAY = x1.DAY
T0 = x1.ts(2020, 1, 6) - 400 * DAY


def make_raw(d, n=40, days=1400, age_drift=0.0, seed=0):
    """Assets list at staggered dates; daily drift = age_drift * (listed within the last 180 days).
    Volatility is identical across assets, so any age effect is not a volatility effect."""
    rng = np.random.default_rng(seed)
    os.makedirs(os.path.join(d, "funding")); os.makedirs(os.path.join(d, "spot"))
    plan = []
    for j in range(n):
        a = "BTCUSDT" if j == 0 else f"A{j}USDT"
        start = 0 if j < 10 else int(rng.integers(0, days - 200))
        r = rng.normal(0, 0.03, days)
        k = np.arange(days)
        r = r + age_drift * ((k - start) < 180)
        c = 100 * np.exp(np.cumsum(r))
        rows = [[T0 + i * DAY, c[i], c[i], c[i], c[i], 1.0, 1e6] for i in range(start, days)]
        fr = [[T0 + i * DAY + h * 3600, 1e-4] for i in range(start, days) for h in (0, 8, 16)]
        plan.append([a, a])
        json.dump({"meta": {}, "rows": rows}, open(os.path.join(d, "spot", f"{a}.json"), "w"))
        json.dump({"meta": {}, "rows": fr}, open(os.path.join(d, "funding", f"{a}.json"), "w"))
    json.dump({"planned": plan}, open(os.path.join(d, "_universe_plan.json"), "w"))


def test_age_from_first_bar():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, n=12, days=500)
        P = x1.Panel(d)
        a = "A11USDT"
        t0 = int(P.spot[a]["t"][0])
        assert e.age_days(P, a, t0 + 100 * DAY) == 100


def test_planted_young_underperformance_found_and_null_quiet():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, age_drift=-0.004, seed=1)
        r = e.tests(x4.Panel4(x1.Panel(d)), x1.ts(2020, 1, 6), x1.ts(2023, 3, 1))
        assert r["P_partial_ic_age"]["mean"] > 0.05, r["P_partial_ic_age"]
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, age_drift=0.0, seed=2)
        r = e.tests(x4.Panel4(x1.Panel(d)), x1.ts(2020, 1, 6), x1.ts(2023, 3, 1))
        assert abs(r["P_partial_ic_age"]["t"]) < 3.0, r["P_partial_ic_age"]


if __name__ == "__main__":
    tests = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    for n, f in tests:
        f()
        print("ok ", n)
    print(f"{len(tests)}/{len(tests)} passed")
