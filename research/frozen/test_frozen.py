"""Tests for the frozen evaluator on synthetic data (no network, no ACCESS log writes).
Run: python3 research/frozen/test_frozen.py"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


ev = mod("frozen_eval", os.path.join(HERE, "evaluate.py"))
ent = mod("frozen1_entrants", os.path.join(HERE, "FROZEN-1", "entrants.py"))
SPEC = json.load(open(os.path.join(HERE, "FROZEN-1", "spec.json")))
DAY = 86400
FREEZE = 1790380800 + 3600          # 2026-09-26 01:00 UTC (synthetic)
T0 = (FREEZE // DAY + 1) * DAY


def panel(days_before=200, days_after=900, lowvol_drift=0.0, seed=0):
    rng = np.random.default_rng(seed)
    out = {}
    pairs = SPEC["universe_kraken_pairs"]
    start = T0 - days_before * DAY
    for j, p in enumerate(pairs):
        sig = 0.005 if p == "LINKUSD" else 0.01 + 0.004 * j
        r = rng.normal(0, sig, days_before + days_after)
        if p != "LINKUSD":
            r = r + lowvol_drift * (sig < 0.03)
        c = 100 * np.exp(np.cumsum(r))
        out[p] = {start + k * DAY: float(c[k]) for k in range(len(c))}
    return out


def test_no_outcome_before_freeze():
    P = panel()
    win = ent.a1_s2_windows(P, T0, T0 + 200 * DAY)
    assert win and min(t for t, _, _ in win) >= T0
    per = ent.a2_periods(P, SPEC["universe_kraken_pairs"], T0, T0 + 400 * DAY)
    assert per and min(p[0] for p in per) >= T0
    rows = [{"decision_ts_epoch": FREEZE - 10, "pair": "ETHUSD"}, {"decision_ts_epoch": FREEZE + 10, "pair": "ETHUSD"}]
    b = ent.b_rows(rows, P, SPEC["universe_kraken_pairs"], FREEZE)
    assert len(b) == 1 and b[0]["t"] == T0


def test_planted_lowvol_edge_succeeds_and_null_does_not():
    freeze = {"freeze_ts": FREEZE}
    res = ev.run(SPEC, freeze, ent, panel(lowvol_drift=0.004, seed=1), [], T0 + 880 * DAY)
    assert res["A2_X4_lowvol5_excess_vs_LINK"]["verdict"] == "SUCCESS", res["A2_X4_lowvol5_excess_vs_LINK"]
    res0 = ev.run(SPEC, freeze, ent, panel(lowvol_drift=0.0, seed=2), [], T0 + 880 * DAY)
    assert res0["A2_X4_lowvol5_excess_vs_LINK"]["verdict"] != "SUCCESS"
    assert res0["B1_tactical_candidates_all"]["verdict"] == "INSUFFICIENT_N"


def test_static_control_cancels_pure_exposure():
    """A rule that is always ON equals static exposure 1: the statistic must be exactly 0."""
    wins = [(T0 + i * 5 * DAY, 1.0, 0.01 * ((-1) ** i)) for i in range(20)]
    diff, e = ent.a1_statistic(wins)
    assert e == 1.0 and np.allclose(diff, 0.0)


def test_holm():
    assert ev.holm([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]


if __name__ == "__main__":
    tests = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    for n, f in tests:
        f()
        print("ok ", n)
    print(f"{len(tests)}/{len(tests)} passed")
