"""X9: wide-divergence relative value vs LINK (live-agent proposal A3). See PREREGISTRATION.md.

Reuses X1's survivorship-free Binance daily panel (research/x1_funding/raw, fetched by x1_funding/fetch.py).
  python3 research/x9_relval/evaluate.py --stage discovery   -> results/discovery.json
  python3 research/x9_relval/evaluate.py --stage reused      -> results/reused.json (after discovery committed)
"""
import datetime as dt
import importlib.util
import json
import math
import os
import sys

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location("x1_evaluate", os.path.join(HERE, "..", "x1_funding", "evaluate.py"))
x1 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(x1)

RES = os.path.join(HERE, "results")
DAY, WEEK = x1.DAY, x1.WEEK
RT4 = 0.0183
LOOK = 90
VETO_PTS = 15.0
ZS, HOLDS = (-2.5, -3.0), (7, 28)
PRIMARY = (-3.0, 28)
MON0 = x1.ts(2020, 1, 6)
DISC = (x1.ts(2020, 4, 6), x1.ts(2023, 12, 31))
REUSED = (x1.ts(2024, 1, 1), x1.ts(2026, 6, 30))
POSTCUT = (x1.ts(2026, 7, 1), x1.ts(2026, 8, 27))
LINK = "LINKUSDT"


class RV:
    def __init__(self, P):
        self.P = P
        self._c = {}

    def lc(self, a, T):
        """log close(T) or None."""
        k = (a, T)
        if k not in self._c:
            c = self.P.close_at(a, T)
            self._c[k] = math.log(c) if c else None
        return self._c[k]

    def z(self, a, T):
        """z of log(X/LINK) at close(T) vs mean/sd of the LOOK prior closes (T excluded)."""
        cur_a, cur_l = self.lc(a, T), self.lc(LINK, T)
        if cur_a is None or cur_l is None:
            return None
        hist = []
        for i in range(1, LOOK + 1):
            xa, xl = self.lc(a, T - i * DAY), self.lc(LINK, T - i * DAY)
            if xa is None or xl is None:
                return None
            hist.append(xa - xl)
        sd = float(np.std(hist, ddof=1))
        return ((cur_a - cur_l) - float(np.mean(hist))) / sd if sd > 0 else None

    def vol60(self, a, T):
        v = [self.lc(a, T - i * DAY) for i in range(61)]
        if any(x is None for x in v):
            return None
        return float(np.std(np.diff(v[::-1]), ddof=1))

    def universe(self, T):
        mon = MON0 + ((T - MON0) // WEEK) * WEEK
        return [a for a in self.P.universe(mon) if a != LINK]

    def veto_ok(self, a, T, names):
        vols = {n: v for n in set(names) | {LINK, a} if (v := self.vol60(n, T)) is not None}
        if a not in vols or LINK not in vols:
            return False
        order = sorted(vols, key=vols.get)
        pct = {n: 100.0 * i / (len(order) - 1) for i, n in enumerate(order)}
        return pct[a] - pct[LINK] <= VETO_PTS

    def exit_day(self, a, T, zthr, hold):
        for d in range(1, hold + 1):
            zz = self.z(a, T + d * DAY)
            if zz is not None and zz >= 0:
                return T + d * DAY
        return T + hold * DAY

    def excess(self, a, T, Te):
        xa0, xl0 = self.P.close_at(a, T), self.P.close_at(LINK, T)
        xa1, xl1 = self.P.close_upto(a, Te), self.P.close_upto(LINK, Te)
        if not (xa0 and xl0 and xa1 and xl1):
            return None
        return (xa1 / xa0) / (xl1 / xl0) - 1.0 - RT4


def trades(rv, lo, hi, zthr, hold):
    """All triggered trades (per-asset non-overlapping)."""
    out, busy = [], {}
    T = lo
    while T <= hi:
        U = rv.universe(T)
        for a in U:
            if busy.get(a, 0) > T:
                continue
            zz = rv.z(a, T)
            if zz is None or zz > zthr or not rv.veto_ok(a, T, U):
                continue
            Te = rv.exit_day(a, T, zthr, hold)
            ex = rv.excess(a, T, Te)
            if ex is None:
                continue
            out.append({"T": T, "a": a, "z": zz, "Te": Te, "days": (Te - T) // DAY, "net": ex})
            busy[a] = Te
        T += DAY
    return out


def weekly_clusters(tr):
    by = {}
    for t in tr:
        by.setdefault(MON0 + ((t["T"] - MON0) // WEEK) * WEEK, []).append(t)
    return {w: v for w, v in sorted(by.items())}


def nw_t(x, lag):
    x = np.asarray(x, float)
    n = len(x)
    if n < 5:
        return None, None
    m = x.mean()
    e = x - m
    s = e @ e / n
    for L in range(1, lag + 1):
        s += 2 * (1 - L / (lag + 1)) * (e[L:] @ e[:-L]) / n
    se = math.sqrt(max(s, 1e-18) / n)
    t = m / se
    return float(t), float(stats.t.sf(t, n - 1))


def random_control(rv, clusters, n_draws=300, seed=0):
    """Matched null: same entry dates, counts and holding lengths, random veto-passing universe members."""
    rng = np.random.default_rng(seed)
    elig = {}
    for tr in clusters.values():
        for t in tr:
            if t["T"] not in elig:
                U = rv.universe(t["T"])
                elig[t["T"]] = [a for a in U if rv.veto_ok(a, t["T"], U)]
    means = []
    for _ in range(n_draws):
        vals = []
        for w, tr in clusters.items():
            v = []
            for t in tr:
                U = elig[t["T"]]
                if not U:
                    continue
                a = U[rng.integers(len(U))]
                ex = rv.excess(a, t["T"], t["Te"])
                if ex is not None:
                    v.append(ex)
            if v:
                vals.append(float(np.mean(v)))
        means.append(float(np.mean(vals)) if vals else np.nan)
    return np.array(means)


def cell(rv, lo, hi, zthr, hold, control=False):
    tr = trades(rv, lo, hi, zthr, hold)
    cl = weekly_clusters(tr)
    vals = [float(np.mean([t["net"] for t in v])) for v in cl.values()]
    lag = math.ceil(hold / 7)
    t, p = nw_t(vals, lag)
    out = {"n_trades": len(tr), "n_week_clusters": len(vals),
           "mean_net_per_cluster": float(np.mean(vals)) if vals else None,
           "median_net_trade": float(np.median([x["net"] for x in tr])) if tr else None,
           "hit_rate": float(np.mean([x["net"] > 0 for x in tr])) if tr else None,
           "mean_hold_days": float(np.mean([x["days"] for x in tr])) if tr else None,
           "nw_t": t, "p_one_sided_pos": p,
           "mde": (2.8 * abs(np.mean(vals) / t) if t else None) if vals else None,
           "trades_per_year": len(tr) / ((hi - lo) / (365.25 * DAY))}
    if control and vals:
        null = random_control(rv, cl)
        out["random_control_mean"] = float(np.nanmean(null))
        out["p_vs_random"] = float(np.mean(null >= np.mean(vals)))
    return out, tr


def main(stage):
    os.makedirs(RES, exist_ok=True)
    rv = RV(x1.Panel())
    if stage == "discovery":
        lo, hi = DISC
    elif stage == "reused":
        assert os.path.exists(os.path.join(RES, "discovery.json"))
        lo, hi = REUSED
    else:
        raise SystemExit("stage?")
    res = {"meta": {"stage": stage, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat()}, "cells": {}}
    for zt in ZS:
        for h in HOLDS:
            c, tr = cell(rv, lo, hi, zt, h, control=(zt, h) == PRIMARY)
            res["cells"][f"z{zt}_h{h}"] = c
            if (zt, h) == PRIMARY:
                res["primary_trades"] = [{**t, "T": dt.datetime.fromtimestamp(t["T"], dt.timezone.utc).date().isoformat(),
                                          "Te": dt.datetime.fromtimestamp(t["Te"], dt.timezone.utc).date().isoformat()}
                                         for t in tr]
    if stage == "reused":
        res["postcutoff_descriptive"] = {f"z{zt}_h{h}": cell(rv, *POSTCUT, zt, h)[0] for zt in ZS for h in HOLDS}
    json.dump(res, open(os.path.join(RES, f"{stage}.json"), "w"), indent=1)
    for k, c in res["cells"].items():
        print(k, {a: (round(b, 5) if isinstance(b, float) else b) for a, b in c.items()})


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--stage") + 1])
