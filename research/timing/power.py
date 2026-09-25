"""Power / minimum-detectable-effect analysis of the pre-registered T1 design (no market data).

Question: with the data that exists at best (daily LINK since mid-2019), could the T1 test detect
a timing effect large enough to change the live LINK-vs-USD decision? If not, a null from T1 is
uninformative and a "significant" hit is likely an inflated draw (winner's curse), and the result
should be read through the pre-registered shrinkage analysis rather than a significance test.

Synthetic LINK-like returns: Student-t (nu=4) innovations, stochastic volatility (AR(1) log-vol,
persistence 0.97), daily sd swept. The signal is a two-state Markov regime with stationary P(ON)
and mean ON-duration swept (SMA-200-like ~100d, SMA-50-like ~40d, vol/crash/funding-like ~10d).
A planted effect makes the mean daily log return higher by delta when the regime (known at the
close of t) is ON. The real evaluate.evaluate() is used, so power reflects the actual protocol,
including phase averaging and conservative SE.

Run: python3 research/timing/power.py [--reps 300]    (writes results/power.json)
"""
import json
import math
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evaluate as E  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
SAMPLES = {"full_S1-S5": 2440, "full_S6": 1700, "holdout": 995}   # days after warm-up
DURATIONS = (10, 40, 100)
DRIFT_GAP_ANNUAL = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0)   # ON-minus-OFF daily drift x 365
HORIZONS = (5, 10, 20)
P_ON = 0.55


def sim_returns(n, sd, rng, nu=4, phi=0.97, vol_of_vol=0.15):
    z = rng.standard_t(nu, n) / math.sqrt(nu / (nu - 2))
    h = np.empty(n)
    h[0] = 0.0
    e = rng.normal(0, vol_of_vol, n)
    for i in range(1, n):
        h[i] = phi * h[i - 1] + e[i]
    v = np.exp(h)
    v /= math.sqrt(np.mean(v ** 2))
    return sd * v * z


def markov(n, dur, p_on, rng):
    q_off = 1 / dur
    q_on = q_off * p_on / (1 - p_on)
    u = rng.random(n)
    s = np.empty(n)
    s[0] = float(rng.random() < p_on)
    for i in range(1, n):
        flip = u[i] < (q_off if s[i - 1] == 1 else q_on)
        s[i] = 1 - s[i - 1] if flip else s[i - 1]
    return s


def implied_spread(delta, dur, h):
    """E[R_h | ON at t] - E[R_h | OFF at t] for the Markov regime: the regime decays with
    eigenvalue lam = 1 - q_off - q_on, so only sum_k lam^k of the drift gap is forecastable."""
    q_off = 1 / dur
    q_on = q_off * P_ON / (1 - P_ON)
    lam = 1 - q_off - q_on
    return delta * sum(lam ** k for k in range(h))


def one(n, sd, dur, delta, rng):
    s = markov(n, dur, P_ON, rng)
    mu = np.where(s == 1, delta * (1 - P_ON), -delta * P_ON)   # zero unconditional drift
    r = sim_returns(n, sd, rng) + mu
    lr = np.concatenate([[0.0], r[:-1]])                        # day t+1 return uses state at t
    px = 100 * np.exp(np.cumsum(lr))
    return {h: E.evaluate(px, s, h) for h in HORIZONS}


def main():
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 300
    rng = np.random.default_rng(20260925)
    out = {"reps": reps, "p_on": P_ON, "cells": []}
    tb = {h: None for h in HORIZONS}
    for sd in (0.045,):
        for sample, n in SAMPLES.items():
            for dur in DURATIONS:
                for g in DRIFT_GAP_ANNUAL:
                    delta = g / 365
                    res = [one(n, sd, dur, delta, rng) for _ in range(reps)]
                    cell = {"daily_sd": sd, "sample": sample, "n_days": n, "on_duration": dur,
                            "drift_gap_annual": g, "by_h": {}}
                    fam = np.zeros(reps, bool)
                    for h in HORIZONS:
                        t = np.array([r[h]["t"] for r in res])
                        est = np.array([r[h]["spread"] for r in res])
                        df = np.median([r[h]["n_windows"] for r in res]) - 2
                        crit = stats.t.ppf(1 - 0.025 / E.N_FAMILY, df)
                        sig_b = t >= crit
                        fam |= sig_b
                        cell["by_h"][h] = {
                            "implied_spread": implied_spread(delta, dur, h),
                            "power_unadj": float((t >= stats.t.ppf(0.975, df)).mean()),
                            "power_bonf": float(sig_b.mean()),
                            "median_se": float(np.median([r[h]["se"] for r in res])),
                            "mean_est": float(est.mean()),
                            "mean_est_given_bonf_sig": float(est[sig_b].mean()) if sig_b.any() else None,
                            "mean_excess_vs_hold_per_window": float(np.mean(
                                [r[h]["excess_vs_hold_link"] for r in res])),
                        }
                    cell["family_power_bonf_any_h"] = float(fam.mean())
                    out["cells"].append(cell)
                    b20 = cell["by_h"][20]
                    print(f"{sample:<11} dur={dur:>3} gap={g:>3.1f}/yr  impl20={b20['implied_spread']:.3f}"
                          f"  P20(unadj)={b20['power_unadj']:.2f} P20(bonf)={b20['power_bonf']:.2f}"
                          f"  P5(bonf)={cell['by_h'][5]['power_bonf']:.2f}"
                          f"  any-h(bonf)={cell['family_power_bonf_any_h']:.2f}"
                          f"  SE20={b20['median_se']:.3f}  est20|sig={b20['mean_est_given_bonf_sig']}")
    # analytic MDEs across horizons for the full sample, iid approximation
    sd = 0.045
    out["analytic_mde"] = {}
    for h in (5, 10, 20):
        n_w = SAMPLES["full_S1-S5"] / h
        sdh = sd * math.sqrt(h)
        se = sdh * math.sqrt(1 / (P_ON * n_w) + 1 / ((1 - P_ON) * n_w))
        out["analytic_mde"][f"h{h}"] = {
            "se": se, "mde_unadj": (1.96 + 0.8416) * se,
            "mde_bonf": (stats.norm.ppf(1 - 0.025 / E.N_FAMILY) + 0.8416) * se}
    # cross-asset pooling: SE factor for an equal-weight average over k assets with correlation rho
    out["pooling_se_factor"] = {f"k{k}_rho{rho}": math.sqrt((1 + (k - 1) * rho) / k)
                                for k in (3, 4) for rho in (0.6, 0.75, 0.85)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "power.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"analytic_mde": out["analytic_mde"], "pooling": out["pooling_se_factor"]}, indent=1))


if __name__ == "__main__":
    main()
