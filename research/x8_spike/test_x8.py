"""Tests for X8 evaluate.py. Run: python3 research/x8_spike/test_x8.py"""
import importlib.util
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
s = importlib.util.spec_from_file_location("x8", os.path.join(HERE, "evaluate.py"))
e = importlib.util.module_from_spec(s)
s.loader.exec_module(e)
H = e.HOUR
T0 = 1_600_000_000 // H * H


def series(n=6000, spikes=(), reversal=0.0, seed=0):
    rng = np.random.default_rng(seed)
    r = rng.normal(0, 0.01, n)
    for i in spikes:
        r[i] = 0.06
        r[i + 1: i + 5] -= reversal / 4
    c = 100 * np.exp(np.cumsum(r))
    return {T0 + i * H: float(c[i]) for i in range(n)}      # bar opened at T0+i*H closes at c[i]


def test_sigma_excludes_event_hour_and_detects_spike():
    cl = series(spikes=(1000,))
    ev = e.events(cl, T0 + 200 * H, T0 + 5000 * H, 3.0, 4)
    Ts = [x[0] for x in ev]
    assert T0 + 1001 * H in Ts             # event bar opened at 1000 closes at boundary T0+1001h


def test_non_overlap():
    cl = series(spikes=(1000, 1002))
    ev = e.events(cl, T0 + 200 * H, T0 + 5000 * H, 3.0, 4)
    Ts = [x[0] for x in ev]
    assert T0 + 1003 * H not in Ts


def test_planted_reversal_found_null_quiet():
    sp = tuple(range(400, 5800, 60))
    s1, _ = e.cell(series(spikes=sp, reversal=0.03, seed=1), T0 + 200 * H, T0 + 5900 * H, 3.0, 4)
    assert s1["mean"] > 0.01 and s1["t"] > 3
    s0, _ = e.cell(series(spikes=sp, reversal=0.0, seed=2), T0 + 200 * H, T0 + 5900 * H, 3.0, 4)
    assert s0["mean"] < 0                  # no reversal -> net is about -cost


if __name__ == "__main__":
    tests = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    for n, f in tests:
        f()
        print("ok ", n)
    print(f"{len(tests)}/{len(tests)} passed")
