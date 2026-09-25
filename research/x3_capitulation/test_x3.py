"""Tests for X3 evaluate.py on a synthetic archive. Run: python3 research/x3_capitulation/test_x3.py"""
import importlib.util
import json
import os
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("x3_evaluate", os.path.join(HERE, "evaluate.py"))
e = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e)
x1 = e.x1
DAY = x1.DAY
T0 = x1.ts(2020, 1, 6) - 203 * DAY


def make_raw(d, n=30, days=700, crash_days=(), rebound=0.0, seed=0):
    """Common factor with planted crash days (-12% market day, worst names -20%) and a planted
    rebound of `rebound` spread over the next 3 days, larger for names that fell more."""
    rng = np.random.default_rng(seed)
    os.makedirs(os.path.join(d, "funding")); os.makedirs(os.path.join(d, "spot"))
    names = ["BTCUSDT", "LINKUSDT"] + [f"A{i}USDT" for i in range(n - 2)]
    f = rng.normal(0, 0.02, days)
    sens = {a: 0.5 + rng.random() for a in names}
    r = {a: f * sens[a] + rng.normal(0, 0.01, days) for a in names}
    for k in crash_days:
        for a in names:
            r[a][k] = -0.12 * sens[a]
            for j in (1, 2, 3):
                r[a][k + j] += rebound * sens[a] / 3
    plan = []
    for j, a in enumerate(names):
        plan.append([a, a])
        c = 100 * np.exp(np.cumsum(r[a]))
        # bar opened at T0 + k*DAY closes at c[k]; the return of day k is realised in that bar
        rows = [[T0 + k * DAY, c[k], c[k], c[k], c[k], 1.0, 1e6 * (1 + j)] for k in range(days)]
        fr = [[T0 + k * DAY + h * 3600, 1e-4] for k in range(days) for h in (0, 8, 16)]
        json.dump({"meta": {}, "rows": rows}, open(os.path.join(d, "spot", f"{a}.json"), "w"))
        json.dump({"meta": {}, "rows": fr}, open(os.path.join(d, "funding", f"{a}.json"), "w"))
    json.dump({"planned": plan}, open(os.path.join(d, "_universe_plan.json"), "w"))


def test_sd60_excludes_event_day():
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, days=400)
        mk = e.Market(x1.Panel(d), end=T0 + 399 * DAY)
        T = x1.ts(2020, 4, 1)
        before = mk.sd60(T)
        mk.M[T] = -5.0
        assert mk.sd60(T) == before


def test_planted_crashes_detected_with_gap_and_rebound_found():
    k0 = 203 + 100
    crashes = [k0, k0 + 2, k0 + 60, k0 + 150]      # second one within the 5-day gap -> dropped
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, days=700, crash_days=crashes, rebound=0.15, seed=1)
        mk = e.Market(x1.Panel(d), end=T0 + 699 * DAY)
        ev = mk.events(x1.ts(2020, 3, 15), T0 + 690 * DAY)
        want = {T0 + (k + 1) * DAY for k in (k0, k0 + 60, k0 + 150)}   # close(T) = bar opened T-1d
        assert want <= set(ev) and T0 + (k0 + 3) * DAY not in ev, (sorted(ev), sorted(want))
        res = e.study(mk, x1.ts(2020, 3, 15), T0 + 690 * DAY)
        assert res["P1_ew_excess"]["mean"] > 0.05
        assert res["P2_ic_crash_vs_fwd"]["mean"] < 0


def test_no_rebound_means_no_p1_effect():
    k0 = 203 + 100
    crashes = [k0 + 20 * i for i in range(12)]
    with tempfile.TemporaryDirectory() as d:
        make_raw(d, days=700, crash_days=crashes, rebound=0.0, seed=2)
        mk = e.Market(x1.Panel(d), end=T0 + 699 * DAY)
        res = e.study(mk, x1.ts(2020, 3, 15), T0 + 690 * DAY)
        assert abs(res["P1_ew_excess"]["mean"]) < 0.03, res["P1_ew_excess"]


if __name__ == "__main__":
    tests = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    for n, f in tests:
        f()
        print("ok ", n)
    print(f"{len(tests)}/{len(tests)} passed")
