"""X1 evaluation (see PREREGISTRATION.md).

  python3 research/x1_funding/evaluate.py --stage discovery   -> results/discovery.json
  python3 research/x1_funding/evaluate.py --stage holdout     -> results/holdout.json (run once, after
                                                                 discovery.json is committed)
  python3 research/x1_funding/evaluate.py --stage crosscheck  -> results/crosscheck.json

Conventions: a daily bar is keyed by its UTC open time; close(t) is the close of the bar that opened
at t - 1 day. Nothing at or after t enters a signal or universe filter for decision time t.
"""
import datetime as dt
import glob
import json
import os
import sys

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
RES = os.path.join(HERE, "results")
DAY = 86400
WEEK = 7 * DAY
TOPN, MIN_BARS, VOL_BARS = 50, 60, 30
LEG_MAKER, LEG_TAKER = 0.0046, 0.0083
KS = (1, 3, 5, 10)
N_TESTS = 5
ALPHA = 0.05 / N_TESTS


def ts(y, m, d):
    return int(dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp())


DISC = (ts(2020, 1, 6), ts(2023, 12, 25))
HOLD = (ts(2024, 1, 1), ts(2026, 9, 14))
FUNDING_END = ts(2026, 8, 31)   # archive's last month; later weeks have partial signals (see finding)


# ---------------------------------------------------------------- data
class Panel:
    def __init__(self, raw=RAW):
        plan = json.load(open(os.path.join(raw, "_universe_plan.json")))
        self.pairs = [(p, s) for p, s in plan["planned"]]
        self.fund, self.spot = {}, {}
        for p, s in self.pairs:
            fp, sp = os.path.join(raw, "funding", f"{p}.json"), os.path.join(raw, "spot", f"{s}.json")
            if not (os.path.exists(fp) and os.path.exists(sp)):
                continue
            f = np.array(json.load(open(fp))["rows"], float).reshape(-1, 2)
            r = np.array(json.load(open(sp))["rows"], float).reshape(-1, 7)
            if len(f) == 0 or len(r) == 0:
                continue
            self.fund[p] = f
            self.spot[p] = {"t": r[:, 0].astype(np.int64), "close": r[:, 4], "qv": r[:, 6], "sym": s}
        # duplicate spot mapping (e.g. X and 1000X perps) -> keep the perp with more funding prints
        by_spot = {}
        for p in self.spot:
            s = self.spot[p]["sym"]
            if s not in by_spot or len(self.fund[p]) > len(self.fund[by_spot[s]]):
                by_spot[s] = p
        self.assets = sorted(by_spot.values())
        self._u, self._f = {}, {}

    def close_at(self, a, t):
        """close(t) = close of the bar opened at t - 1d, or None if that bar is missing."""
        s = self.spot[a]
        i = np.searchsorted(s["t"], t - DAY)
        return s["close"][i] if i < len(s["t"]) and s["t"][i] == t - DAY else None

    def close_upto(self, a, t):
        """Last close at or before t (handles delisting: price at the last trade)."""
        s = self.spot[a]
        i = np.searchsorted(s["t"], t - DAY, side="right") - 1
        return s["close"][i] if i >= 0 else None

    def features(self, a, t):
        s, f = self.spot[a], self.fund[a]
        i = np.searchsorted(s["t"], t - DAY)          # index of the bar that closes at t
        if i >= len(s["t"]) or s["t"][i] != t - DAY or i + 1 < MIN_BARS:
            return None
        w = f[(f[:, 0] > t - WEEK) & (f[:, 0] <= t)]
        if len(w) == 0:
            return None
        d1 = f[(f[:, 0] > t - DAY) & (f[:, 0] <= t)]
        c = s["close"][: i + 1]
        lr = np.diff(np.log(c[-31:]))
        c7 = self.close_at(a, t - WEEK)
        return {"F7": float(w[:, 1].mean()), "F1": float(d1[:, 1].mean()) if len(d1) else float(w[-1, 1]),
                "qv": float(np.median(s["qv"][i + 1 - VOL_BARS: i + 1])),
                "ret7": float(np.log(c[-1] / c7)) if c7 else float(np.log(c[-1] / c[-8])),
                "vol30": float(np.std(lr, ddof=1))}

    def universe(self, t):
        if t not in self._u:
            self._u[t] = self._universe(t)
        return self._u[t]

    def _universe(self, t):
        rows = {a: x for a in self.assets if (x := self.features(a, t)) is not None}
        top = sorted(rows, key=lambda a: -rows[a]["qv"])[:TOPN]
        return {a: rows[a] for a in top}

    def fwd(self, a, t, h):
        key = (a, t, h)
        if key not in self._f:
            self._f[key] = self._fwd(a, t, h)
        return self._f[key]

    def _fwd(self, a, t, h):
        c0 = self.close_at(a, t)
        c1 = self.close_upto(a, t + h)
        return float(np.log(c1 / c0)) if c0 and c1 else None


# ---------------------------------------------------------------- statistics
def rank(x):
    return stats.rankdata(x)


def resid(y, X):
    X = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def week_stats(P, t, h, sig="F7"):
    U = P.universe(t)
    names, F, R, M, V = [], [], [], [], []
    for a, x in U.items():
        r = P.fwd(a, t, h)
        if r is None:
            continue
        names.append(a); F.append(x[sig]); R.append(r); M.append(x["ret7"]); V.append(x["vol30"])
    if len(names) < 10:
        return None
    F, R, M, V = map(np.array, (F, R, M, V))
    ic = stats.spearmanr(F, R).statistic
    rF, rR = rank(F), rank(R)
    ctrl = np.column_stack([rank(M), rank(V)])
    pic = float(np.corrcoef(resid(rF, ctrl), resid(rR, ctrl))[0, 1])
    q = max(len(F) // 5, 1)
    order = np.argsort(F)
    simple = np.expm1(R)
    spread = float(simple[order[:q]].mean() - simple[order[-q:]].mean())
    return {"t": t, "n": len(F), "ic": float(ic), "pic": pic, "q_spread": spread}


def summarize(vals, one_sided_neg=False):
    v = np.array([x for x in vals if x is not None and np.isfinite(x)])
    n = len(v)
    if n < 3:
        return {"n": n}
    m, se = float(v.mean()), float(v.std(ddof=1) / np.sqrt(n))
    if se == 0:
        return {"n": n, "mean": m, "se": 0.0}
    tt = m / se
    p2 = float(2 * stats.t.sf(abs(tt), n - 1))
    out = {"n": n, "mean": m, "se": se, "t": tt, "p_two_sided": p2, "mde": 2.8 * se,
           "ci95": [m - 1.96 * se, m + 1.96 * se]}
    if one_sided_neg:
        out["p_one_sided_neg"] = float(stats.t.cdf(tt, n - 1))
    return out


def mondays(start, end, step_weeks=1, phase_days=0):
    t = start + phase_days * DAY
    out = []
    while t <= end:
        out.append(t)
        t += step_weeks * WEEK
    return out


def per_year(rows, key):
    out = {}
    for r in rows:
        y = dt.datetime.fromtimestamp(r["t"], dt.timezone.utc).year
        out.setdefault(y, []).append(r[key])
    return {y: summarize(v) for y, v in sorted(out.items())}


def tests(P, lo, hi, one_sided=False):
    res = {}
    weeks = [w for t in mondays(lo, hi) if (w := week_stats(P, t, WEEK)) is not None]
    res["P_ic_7d"] = summarize([w["ic"] for w in weeks], one_sided)
    res["S-c_partial_ic_7d"] = summarize([w["pic"] for w in weeks], one_sided)
    res["S-d_quintile_spread_low_minus_high"] = summarize([w["q_spread"] for w in weeks])
    wb = [w for t in mondays(lo, hi) if (w := week_stats(P, t, WEEK, "F1")) is not None]
    res["S-b_ic_7d_last24h"] = summarize([w["ic"] for w in wb], one_sided)
    s28 = {}
    for ph in range(4):
        ws = [w for t in mondays(lo + ph * WEEK, hi - 3 * WEEK, 4) if (w := week_stats(P, t, 4 * WEEK)) is not None]
        s28[f"phase{ph}"] = summarize([w["ic"] for w in ws], one_sided)
    res["S-a_ic_28d"] = s28["phase0"]
    res["S-a_phases"] = s28
    res["P_per_year"] = per_year(weeks, "ic")
    res["P_weekday_anchor_robustness"] = {
        d: summarize([w["ic"] for t in mondays(lo, hi, 1, d) if (w := week_stats(P, t, WEEK)) is not None])
        for d in range(1, 7)}
    res["universe_size"] = summarize([w["n"] for w in weeks])
    res["weeks"] = weeks
    for k in ("P_ic_7d", "S-a_ic_28d", "S-b_ic_7d_last24h", "S-c_partial_ic_7d"):
        r = res[k]
        r["bonferroni_pass_neg"] = bool("p_two_sided" in r and r["mean"] < 0 and r["p_two_sided"] < ALPHA)
    return res


# ---------------------------------------------------------------- economics
def backtest(P, lo, hi, k, leg, rng=None, n_draws=0, subset=None):
    """Long-only equal-weight k lowest-F7 (or random-k if rng given), weekly. Returns weekly net
    simple returns. Turnover cost = leg * sum|w_target - w_drifted|; first week pays full entry."""
    rets, w_prev = [], {}
    for t in mondays(lo, hi):
        U = P.universe(t)
        if subset is not None:
            U = {a: x for a, x in U.items() if a in subset}
        cand = [a for a in U if P.fwd(a, t, WEEK) is not None]
        if len(cand) < k:
            rets.append(0.0); w_prev = {}
            continue
        pick = rng.choice(cand, k, replace=False) if rng is not None else sorted(cand, key=lambda a: U[a]["F7"])[:k]
        w = {a: 1 / k for a in pick}
        turn = sum(abs(w.get(a, 0) - w_prev.get(a, 0)) for a in set(w) | set(w_prev))
        r = {a: float(np.expm1(P.fwd(a, t, WEEK))) for a in pick}
        gross = sum(w[a] * r[a] for a in pick)
        net = gross - leg * turn
        rets.append(net)
        tot = 1 + gross
        w_prev = {a: w[a] * (1 + r[a]) / tot for a in pick} if tot > 0 else {}
    return np.array(rets)


def ew_universe(P, lo, hi, leg):
    rets, w_prev = [], {}
    for t in mondays(lo, hi):
        U = P.universe(t)
        cand = [a for a in U if P.fwd(a, t, WEEK) is not None]
        w = {a: 1 / len(cand) for a in cand}
        r = {a: float(np.expm1(P.fwd(a, t, WEEK))) for a in cand}
        turn = sum(abs(w.get(a, 0) - w_prev.get(a, 0)) for a in set(w) | set(w_prev))
        gross = sum(w[a] * r[a] for a in cand)
        rets.append(gross - leg * turn)
        w_prev = {a: w[a] * (1 + r[a]) / (1 + gross) for a in cand}
    return np.array(rets)


def hold(P, lo, hi, asset="LINKUSDT"):
    out = []
    for t in mondays(lo, hi):
        r = P.fwd(asset, t, WEEK)
        out.append(float(np.expm1(r)) if r is not None else 0.0)
    return np.array(out)


def block_ci(x, block=4, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x)
    nb = int(np.ceil(len(x) / block))
    means = []
    for _ in range(n):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.integers(0, len(x) - block + 1, nb)])[: len(x)]
        means.append(x[idx].mean())
    return [float(np.percentile(means, 5)), float(np.percentile(means, 95))]


def economics(P, lo, hi, subset=None):
    link, usd = hold(P, lo, hi), np.zeros(len(mondays(lo, hi)))
    out = {"hold_LINK": {"wealth": float(np.prod(1 + link)), "mean_wk": float(link.mean())},
           "hold_USD": {"wealth": 1.0}}
    for leg_name, leg in (("maker", LEG_MAKER), ("taker", LEG_TAKER)):
        ew = ew_universe(P, lo, hi, leg)
        out[f"ew_universe_{leg_name}"] = {"wealth": float(np.prod(1 + ew)), "mean_wk": float(ew.mean())}
        for k in KS:
            s = backtest(P, lo, hi, k, leg, subset=subset)
            rng = np.random.default_rng(k)
            draws = np.array([backtest(P, lo, hi, k, leg, rng=rng, subset=subset) for _ in range(100 if leg_name == "taker" else 500)])
            rk = draws.mean(axis=0)
            row = {"wealth": float(np.prod(1 + s)), "mean_wk": float(s.mean()),
                   "random_k_wealth_median": float(np.median(np.prod(1 + draws, axis=1))),
                   "random_k_mean_wk": float(rk.mean()),
                   "pct_random_draws_beaten_by_wealth": float((np.prod(1 + draws, axis=1) < np.prod(1 + s)).mean()),
                   "excess_vs_random_k_mean_wk": float((s - rk).mean()),
                   "excess_vs_random_k_ci90": block_ci(s - rk),
                   "excess_vs_LINK_mean_wk": float((s - link).mean()),
                   "excess_vs_LINK_ci90": block_ci(s - link),
                   "excess_vs_USD_mean_wk": float(s.mean()),
                   "excess_vs_USD_ci90": block_ci(s - usd),
                   "min_order_ok_at_A58.62": 58.62 / k >= 5.0}
            out[f"top{k}_{leg_name}"] = row
    return out


def kraken_bases():
    path = os.path.join(RAW, "kraken_assetpairs.json")
    if not os.path.exists(path):
        import requests
        d = requests.get("https://api.kraken.com/0/public/AssetPairs", timeout=30).json()
        json.dump({"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(), "result": d["result"]}, open(path, "w"))
    d = json.load(open(path))["result"]
    alias = {"XBT": "BTC", "XDG": "DOGE"}
    out = set()
    for v in d.values():
        ws = v.get("wsname", "")
        if ws.endswith("/USD"):
            b = ws.split("/")[0]
            out.add(alias.get(b, b))
    return out


def crosscheck(P, raw_cb=os.path.join(HERE, "..", "data", "raw")):
    """Binance spot vs Coinbase USD weekly log returns (Monday closes), F5's bases."""
    out = {}
    for f in sorted(glob.glob(os.path.join(raw_cb, "coinbase_*_1d.json"))):
        b = os.path.basename(f).split("_")[1]
        a = next((x for x in P.assets if P.spot[x]["sym"] == f"{b}USDT"), None)
        if a is None:
            continue
        cb = {int(r[0]): float(r[4]) for r in json.load(open(f))["rows"]}
        xs, ys = [], []
        for t in mondays(DISC[0], HOLD[1]):
            b0, b1 = P.close_at(a, t), P.close_at(a, t + WEEK)
            c0, c1 = cb.get(t - DAY), cb.get(t + WEEK - DAY)
            if b0 and b1 and c0 and c1:
                xs.append(np.log(b1 / b0)); ys.append(np.log(c1 / c0))
        out[b] = {"n": len(xs), "corr": float(np.corrcoef(xs, ys)[0, 1])}
    return out


def main(stage):
    os.makedirs(RES, exist_ok=True)
    P = Panel()
    meta = {"assets_loaded": len(P.assets), "generated_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    if stage == "discovery":
        res = {"meta": meta, "tests": tests(P, *DISC), "economics": economics(P, *DISC)}
        out = os.path.join(RES, "discovery.json")
    elif stage == "holdout":
        assert os.path.exists(os.path.join(RES, "discovery.json")), "run discovery first"
        kb = kraken_bases()
        sub = {a for a in P.assets if P.spot[a]["sym"][:-4] in kb}
        res = {"meta": {**meta, "kraken_subset_size": len(sub)},
               "tests": tests(P, *HOLD, one_sided=True),
               "tests_to_funding_end": tests(P, HOLD[0], FUNDING_END - WEEK, one_sided=True),
               "economics": economics(P, *HOLD),
               "economics_kraken_subset_SURVIVORSHIP_BIASED": economics(P, *HOLD, subset=sub),
               "economics_full_period": economics(P, DISC[0], HOLD[1])}
        out = os.path.join(RES, "holdout.json")
    elif stage == "crosscheck":
        res = {"meta": meta, "binance_vs_coinbase_weekly_log_return_corr": crosscheck(P)}
        json.dump(res, open(os.path.join(RES, "crosscheck.json"), "w"), indent=1)
        for a, v in res["binance_vs_coinbase_weekly_log_return_corr"].items():
            print(f"  {a:6s} n={v['n']:4d} corr={v['corr']:.4f} {'OK' if v['corr'] >= 0.98 else 'FAIL'}")
        return res
    else:
        raise SystemExit("unknown stage")
    json.dump(res, open(out, "w"), indent=1)
    t = res["tests"]
    for k in ("P_ic_7d", "S-a_ic_28d", "S-b_ic_7d_last24h", "S-c_partial_ic_7d", "S-d_quintile_spread_low_minus_high"):
        r = t[k]
        print(f"{k:38s} n={r['n']:4d} mean={r['mean']:+.4f} t={r['t']:+.2f} p2={r['p_two_sided']:.4f} "
              f"mde={r['mde']:.4f}" + (f" p1neg={r['p_one_sided_neg']:.4f}" if "p_one_sided_neg" in r else ""))
    print("per-year IC:", {y: round(v.get('mean', float('nan')), 4) for y, v in t["P_per_year"].items()})
    print("anchor robustness:", {d: round(v['mean'], 4) for d, v in t["P_weekday_anchor_robustness"].items()})
    for k, v in res["economics"].items():
        print(f"  {k:18s} " + ", ".join(f"{a}={b:.4f}" if isinstance(b, float) else f"{a}={b}" for a, b in v.items()
                                        if not isinstance(b, list)))
    return res


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "discovery")
