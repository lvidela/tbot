"""Synthetic tests for FROZEN-2 (no network, no ACCESS log). Run: python3 research/frozen/FROZEN-2/test_frozen2.py"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def mod(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


ent = mod("f2ent", os.path.join(HERE, "entrants.py"))
ev = mod("f2ev", os.path.join(HERE, "evaluate2.py"))
SPEC = json.load(open(os.path.join(HERE, "spec.json")))
DAY = 86400
FZ = {"freeze_ts": 1790380800 + 9 * 3600}


def closes(highvol_drift=0.0, days_after=800, seed=0, delist=None):
    rng = np.random.default_rng(seed)
    t0 = ent.first_monday_after(FZ["freeze_ts"])
    start = t0 - 90 * DAY
    out = {}
    for j, p in enumerate(SPEC["universe_pairs"][:40] + ["LINKUSD"]):
        sig = 0.01 if p == "LINKUSD" else 0.01 + 0.002 * j
        r = rng.normal(0, sig, 90 + days_after) + (highvol_drift if sig > 0.06 else 0.0)
        c = 100 * np.exp(np.cumsum(r))
        n = len(c) if p != delist else 150
        out[p] = {start + k * DAY: float(c[k]) for k in range(n)}
    return out


def test_first_monday():
    t = ent.first_monday_after(FZ["freeze_ts"])
    import datetime as dt
    assert dt.datetime.fromtimestamp(t, dt.timezone.utc).weekday() == 0 and t > FZ["freeze_ts"]


def test_no_period_before_t0_and_delisted_kept():
    t0 = ent.first_monday_after(FZ["freeze_ts"])
    c = closes(delist=SPEC["universe_pairs"][39])
    per = ent.periods(c, SPEC["universe_pairs"] + ["LINKUSD"], t0, t0 + 400 * DAY)
    assert per and min(p["t"] for p in per) >= t0


def test_positive_and_negative_ev_detected():
    t0 = ent.first_monday_after(FZ["freeze_ts"])
    spec = dict(SPEC, universe_pairs=SPEC["universe_pairs"][:40] + ["LINKUSD"])
    pos = ev.run(spec, FZ, ent, closes(highvol_drift=0.01, seed=1), t0 + 780 * DAY)
    assert pos["q5_net"]["verdict"] == "POSITIVE_EV", pos["q5_net"]
    neg = ev.run(spec, FZ, ent, closes(highvol_drift=-0.01, seed=2), t0 + 780 * DAY)
    assert neg["q5_net"]["verdict"] == "NEGATIVE_EV", neg["q5_net"]


if __name__ == "__main__":
    tests = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    for n, f in tests:
        f()
        print("ok ", n)
    print(f"{len(tests)}/{len(tests)} passed")
