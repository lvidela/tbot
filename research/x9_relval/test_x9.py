"""Tests for X9 evaluate.py. Run: python3 research/x9_relval/test_x9.py"""
import importlib.util
import json
import os
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
s = importlib.util.spec_from_file_location("x9", os.path.join(HERE, "evaluate.py"))
e = importlib.util.module_from_spec(s)
s.loader.exec_module(e)
x1 = e.x1
DAY = x1.DAY
T0 = x1.ts(2020, 1, 6) - 203 * DAY


def make_raw(d, days=900, shock_days=(), converge=True, seed=0, n=12):
    """LINK + n assets with equal vol; on shock days one asset drops 25% vs LINK and (optionally)
    converges back over the next 10 days."""
    rng = np.random.default_rng(seed)
    os.makedirs(os.path.join(d, "funding")); os.makedirs(os.path.join(d, "spot"))
    names = ["LINKUSDT"] + [f"A{i}USDT" for i in range(n)]
    common = rng.normal(0, 0.02, days)
    plan = []
    for j, a in enumerate(names):
        idio = 0.01 if a == "LINKUSDT" else (0.005 if a == "A1USDT" else 0.08)
        r = common + rng.normal(0, idio, days)
        if a == "A1USDT":
            for k in shock_days:
                r[k] -= 0.25
                if converge:
                    r[k + 1: k + 11] += 0.025
        c = 100 * np.exp(np.cumsum(r))
        plan.append([a, a])
        rows = [[T0 + i * DAY, c[i], c[i], c[i], c[i], 1.0, 1e6] for i in range(days)]
        fr = [[T0 + i * DAY + h * 3600, 1e-4] for i in range(days) for h in (0, 8, 16)]
        json.dump({"meta": {}, "rows": rows}, open(os.path.join(d, "spot", f"{a}.json"), "w"))
        json.dump({"meta": {}, "rows": fr}, open(os.path.join(d, "funding", f"{a}.json"), "w"))
    json.dump({"planned": plan}, open(os.path.join(d, "_universe_plan.json"), "w"))


def test_z_excludes_today_and_trigger_found():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, shock_days=(500,))
        rv = e.RV(x1.Panel(d))
        T = T0 + 501 * DAY                     # close of the bar opened on shock day
        assert rv.z("A1USDT", T) < -3
        tr = e.trades(rv, T0 + 400 * DAY, T0 + 600 * DAY, -3.0, 28)
        assert any(t["a"] == "A1USDT" and t["T"] == T for t in tr)


def test_convergence_profits_and_no_convergence_loses():
    shocks = tuple(range(300, 880, 40))
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, shock_days=shocks, converge=True, seed=1)
        c, _ = e.cell(e.RV(x1.Panel(d)), T0 + 290 * DAY, T0 + 870 * DAY, -3.0, 28)
        assert c["mean_net_per_cluster"] > 0.05, c
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, shock_days=shocks, converge=False, seed=2)
        c, _ = e.cell(e.RV(x1.Panel(d)), T0 + 290 * DAY, T0 + 870 * DAY, -3.0, 28)
        assert c["mean_net_per_cluster"] < 0.02, c


if __name__ == "__main__":
    tests = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    for n, f in tests:
        f()
        print("ok ", n)
    print(f"{len(tests)}/{len(tests)} passed")
