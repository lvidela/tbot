"""Tests for the T1 pipeline on synthetic data (no network).

Run: python3 research/timing/test_timing.py   (or pytest research/timing)
"""
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data as D  # noqa: E402
import evaluate as E  # noqa: E402
import signals as S  # noqa: E402


def _walk(n, sd=0.05, seed=0, mu=0.0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2019-07-01", periods=n, freq="D", tz="UTC")
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(mu, sd, n))), index=idx)


def _markov(n, dur, p_on, seed):
    rng = np.random.default_rng(seed)
    q_off = 1 / dur                        # P(leave ON)
    q_on = q_off * p_on / (1 - p_on)       # P(leave OFF), stationary P(ON) = p_on
    s = np.empty(n)
    s[0] = 1.0
    for i in range(1, n):
        flip = rng.random() < (q_off if s[i - 1] == 1 else q_on)
        s[i] = 1 - s[i - 1] if flip else s[i - 1]
    return s


def test_signals_no_lookahead():
    link, btc = _walk(900, seed=1), _walk(900, seed=2)
    fund = pd.Series(np.random.default_rng(3).normal(1e-4, 1e-4, 900), index=link.index)
    a = S.compute(link, btc, fund)
    link2, btc2, fund2 = link.copy(), btc.copy(), fund.copy()
    link2.iloc[700:] *= 3.0; btc2.iloc[700:] *= 0.2; fund2.iloc[700:] = 0.01
    b = S.compute(link2, btc2, fund2)
    pd.testing.assert_frame_equal(a.iloc[:700], b.iloc[:700])


def test_signal_definitions():
    idx = pd.date_range("2020-01-01", periods=400, freq="D", tz="UTC")
    up = pd.Series(np.linspace(1, 2, 400), index=idx)
    sg = S.compute(up, up)
    assert sg["S1"].iloc[250] == 1 and sg["S3"].iloc[100] == 1
    assert math.isnan(sg["S1"].iloc[150])                 # 200d warm-up
    crash = up.copy(); crash.iloc[300:] = crash.iloc[299] * 0.5
    assert S.compute(crash, up)["S4"].iloc[310] == 0      # -50% from 90d max
    assert S.compute(up, up)["S4"].iloc[310] == 1


def test_windows_nonoverlapping_and_phase():
    close = np.arange(1, 101, dtype=float)
    sig = np.ones(100)
    R, s, t = E.windows(close, sig, 10, 3)
    assert list(t[:3]) == [3, 13, 23] and np.all(np.diff(t) == 10)
    assert np.allclose(R, close[t + 10] / close[t] - 1)
    R1, _, t1 = E.windows(close, sig, 10, 3, lag=1)
    assert np.allclose(R1, close[t1 + 11] / close[t1 + 1] - 1)


def test_cost_accounting():
    R = np.array([0.1, -0.1, 0.05, 0.02])
    net, exc, cost = E.strategy(R, np.ones(4), 0.0046)
    assert np.allclose(exc, 0) and cost.sum() == 0        # always ON == hold LINK, no cost
    net, exc, cost = E.strategy(R, np.array([0, 1, 0, 1.0]), 0.0046)
    assert np.isclose(cost.sum(), 4 * 0.0046)             # starts ON: out, in, out, in
    assert np.isclose(net[0], -0.0046) and np.isclose(exc[0], -0.1046)


def test_crosscheck_flags_divergence():
    a = _walk(300, seed=4)
    b = a * 1.001
    b.iloc[100] *= 1.05
    summ, flagged = D.crosscheck(a, b)
    assert summ["n_flagged"] == 1 and flagged.index[0] == a.index[100]
    assert abs(summ["median_log_ratio_bps"] + 10) < 1


def test_null_false_positive_rate():
    """Independent persistent signal on a random walk: |t| > 1.96 should occur ~5% of the time.
    Phase averaging must not inflate it (it would if SE were divided by sqrt(h))."""
    hits, reps = 0, 150
    for r in range(reps):
        px = _walk(2600, sd=0.05, seed=100 + r).values
        sg = _markov(2600, 40, 0.55, seed=900 + r)
        res = E.evaluate(px, sg, 20)
        hits += abs(res["t"]) > 1.96
    rate = hits / reps
    assert rate < 0.11, rate


def test_planted_effect_detected():
    n = 2600
    sg = _markov(n, 40, 0.55, seed=7)
    rng = np.random.default_rng(8)
    r = rng.normal(0, 0.03, n) + np.where(sg == 1, 0.004, -0.004)   # regime known at t, drives t+1..
    lr = np.concatenate([[0], r[:-1]])                                # return on day t+1 uses sig[t]
    px = 100 * np.exp(np.cumsum(lr))
    res = E.evaluate(px, sg, 20)
    assert res["t"] > 3 and res["spread"] > 0.05
    assert res["excess_vs_hold_link"] > 0


def test_circular_shift_preserves_values_and_warmup():
    s = np.array([np.nan, np.nan, 1, 0, 0, 1, 1])
    out = E.circular_shift(s, 2)
    assert np.isnan(out[:2]).all() and sorted(out[2:]) == sorted(s[2:])


def test_shrink_and_mde():
    shr, w = E.shrink(0.05, 0.03, 0.03)
    assert np.isclose(w, 0.5) and np.isclose(shr, 0.025)
    assert abs(E.mde_analytic(0.2, 50, 50) - 2.8016 * 0.2 * math.sqrt(0.04)) < 1e-3


def test_perturbations_shape():
    for sg in ("S1", "S4", "S5", "S6"):
        ps = S.perturbations(sg)
        assert len(ps) == 4
    assert all(0 < x["q"] < 1 for x in S.perturbations("S6") if "q" in x)
    assert np.isclose(S.perturbations("S4")[2]["dd"], -0.2) and np.isclose(S.perturbations("S4")[3]["dd"], -0.4)


def test_end_to_end_smoke(tmp=None):
    """Synthetic raw files in the fetch.py format -> run.main() produces every output file."""
    import json, subprocess, tempfile
    tmp = tmp or tempfile.mkdtemp()
    raw, out = os.path.join(tmp, "raw"), os.path.join(tmp, "out")
    os.makedirs(raw)
    t0 = int(pd.Timestamp("2019-07-01", tz="UTC").timestamp())
    n = 2640
    for i, (src, a) in enumerate([(s, a) for a in ("LINK", "BTC", "ETH", "SOL")
                                  for s in ("coinbase", "binance", "kraken")]):
        px = _walk(n, sd=0.045, seed=50 + i // 3).values * (1 + 0.001 * (i % 3))
        rows = [[t0 + 86400 * k, p, p, p, p, 1.0] for k, p in enumerate(px)]
        if src == "kraken":
            rows = rows[-720:]
        with open(os.path.join(raw, f"{src}_{a}_1d.json"), "w") as f:
            json.dump({"meta": {"source": src, "symbol": a}, "rows": rows}, f)
    rng = np.random.default_rng(5)
    for src in ("binance", "okx"):
        rows = [[t0 + 8 * 3600 * k, float(rng.normal(1e-4, 1e-4))] for k in range(3 * (n - 200))]
        rows = [[r[0] + 200 * 86400, r[1]] for r in rows]
        with open(os.path.join(raw, f"{src}_LINK_funding.json"), "w") as f:
            json.dump({"meta": {"source": src}, "rows": rows}, f)
    env = {**os.environ, "T1_RAW_DIR": raw, "T1_OUT_DIR": out}
    here = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run([sys.executable, os.path.join(here, "run.py"), "--perm", "3"], env=env,
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    for f in ("crosscheck.json", "in_sample.json", "full.json", "holdout.json", "subperiods.json",
              "replication.json", "perturbations.json", "lag1.json", "taker.json",
              "permutation.json", "labels.json", "decision.json"):
        assert os.path.exists(os.path.join(out, f)), f
    labels = json.load(open(os.path.join(out, "labels.json")))
    assert set(labels) == {"S1", "S2", "S3", "S4", "S5", "S6"}
    full = json.load(open(os.path.join(out, "full.json")))
    assert "S6_h20" in full and "S1_h5" in full


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"{len(fns)}/{len(fns)} passed")
