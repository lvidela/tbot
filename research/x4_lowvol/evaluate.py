"""X4 evaluation: low-volatility / low-beta cross-section (see PREREGISTRATION.md).

Reuses X1's survivorship-free panel (research/x1_funding/raw, fetched by x1_funding/fetch.py).
  python3 research/x4_lowvol/evaluate.py --stage discovery   -> results/discovery.json
  python3 research/x4_lowvol/evaluate.py --stage holdout     -> results/holdout.json (after discovery is committed)
"""
import datetime as dt
import json
import os
import sys

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("x1_evaluate", os.path.join(HERE, "..", "x1_funding", "evaluate.py"))
x1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x1)

RES = os.path.join(HERE, "results")
DAY, WEEK = x1.DAY, x1.WEEK
H = 28 * DAY
MIN_VOL = 0.005
KS = (1, 3, 5, 10)
ALPHA = 0.05 / 4
DISC = (x1.ts(2020, 1, 6), x1.ts(2023, 12, 25))
DATA_END = x1.ts(2026, 9, 24)
HOLD = (x1.ts(2024, 1, 1), DATA_END - H)


def periods(lo, hi, phase=0):
    """Every 4th Monday on the 2020-01-06 grid (shifted by `phase` weeks) within [lo, hi]."""
    t, out = x1.ts(2020, 1, 6) + phase * WEEK, []
    while t <= hi:
        if t >= lo:
            out.append(t)
        t += 4 * WEEK
    return out


class Panel4:
    def __init__(self, P):
        self.P = P
        self._u = {}

    def _lr(self, a, t, n):
        s = self.P.spot[a]
        i = np.searchsorted(s["t"], t - DAY)
        if i >= len(s["t"]) or s["t"][i] != t - DAY or i < n:
            return None
        return s["t"][i - n + 1: i + 1], np.diff(np.log(s["close"][i - n: i + 1]))

    def universe(self, t):
        if t in self._u:
            return self._u[t]
        base = self.P.universe(t)
        btc = self._lr("BTCUSDT", t, 60)
        out = {}
        for a, x in base.items():
            r = self._lr(a, t, 60)
            if r is None:
                continue
            vol = float(np.std(r[1], ddof=1))
            if vol < MIN_VOL:
                continue
            beta = float(np.polyfit(btc[1], r[1], 1)[0]) if btc is not None and np.array_equal(btc[0], r[0]) else np.nan
            c28 = self.P.close_at(a, t - H)
            mom = float(np.log(self.P.close_at(a, t) / c28)) if c28 else np.nan
            out[a] = {"vol60": vol, "beta60": beta, "mom28": mom, "qv": x["qv"]}
        self._u[t] = out
        return out


def rank(x):
    return stats.rankdata(x)


def period_stats(P4, t):
    U = P4.universe(t)
    rows = [(a, x, P4.P.fwd(a, t, H)) for a, x in U.items()]
    rows = [(a, x, r) for a, x, r in rows if r is not None]
    if len(rows) < 10:
        return None
    vol = np.array([x["vol60"] for _, x, _ in rows]); R = np.array([r for *_, r in rows])
    beta = np.array([x["beta60"] for _, x, _ in rows]); mom = np.array([x["mom28"] for _, x, _ in rows])
    lqv = np.log(np.array([x["qv"] for _, x, _ in rows]))
    ok = np.isfinite(beta)
    ic_b = float(stats.spearmanr(beta[ok], R[ok]).statistic) if ok.sum() >= 10 else np.nan
    okm = np.isfinite(mom)
    ctrl = np.column_stack([rank(mom[okm]), rank(lqv[okm])])
    pic = float(np.corrcoef(x1.resid(rank(vol[okm]), ctrl), x1.resid(rank(R[okm]), ctrl))[0, 1])
    q = max(len(R) // 5, 1)
    o = np.argsort(vol)
    simple = np.expm1(R)
    return {"t": t, "n": len(R), "ic_vol": float(stats.spearmanr(vol, R).statistic), "ic_beta": ic_b,
            "pic_vol": pic, "q_spread": float(simple[o[:q]].mean() - simple[o[-q:]].mean())}


def tests(P4, lo, hi, one_sided=False):
    res = {}
    by_phase = {ph: [s for t in periods(lo, hi, ph) if (s := period_stats(P4, t)) is not None] for ph in range(4)}
    ps = by_phase[0]
    res["P_ic_vol"] = x1.summarize([s["ic_vol"] for s in ps], one_sided)
    res["S1_ic_beta"] = x1.summarize([s["ic_beta"] for s in ps], one_sided)
    res["S2_partial_ic_vol"] = x1.summarize([s["pic_vol"] for s in ps], one_sided)
    res["S3_quintile_spread_lowvol_minus_highvol"] = x1.summarize([s["q_spread"] for s in ps])
    for k in ("P_ic_vol", "S1_ic_beta", "S2_partial_ic_vol"):
        r = res[k]
        r["bonferroni_pass_neg"] = bool("p_two_sided" in r and r["mean"] < 0 and r["p_two_sided"] < ALPHA)
    res["phase_robustness"] = {f"phase{ph}": {k: x1.summarize([s[k] for s in v]).get("mean")
                                              for k in ("ic_vol", "ic_beta", "pic_vol", "q_spread")}
                               for ph, v in by_phase.items()}
    res["phase_averaged_ic_vol"] = float(np.mean([v["ic_vol"] for v in res["phase_robustness"].values()]))
    res["P_per_year"] = x1.per_year(ps, "ic_vol")
    res["periods"] = ps
    return res


def backtest(P4, lo, hi, k, leg, rng=None, subset=None):
    rets, w_prev = [], {}
    for t in periods(lo, hi):
        U = P4.universe(t)
        if subset is not None:
            U = {a: x for a, x in U.items() if a in subset}
        cand = [a for a in U if P4.P.fwd(a, t, H) is not None]
        if len(cand) < k:
            rets.append(0.0); w_prev = {}
            continue
        pick = list(rng.choice(cand, k, replace=False)) if rng is not None else sorted(cand, key=lambda a: U[a]["vol60"])[:k]
        w = {a: 1 / k for a in pick}
        turn = sum(abs(w.get(a, 0) - w_prev.get(a, 0)) for a in set(w) | set(w_prev))
        r = {a: float(np.expm1(P4.P.fwd(a, t, H))) for a in pick}
        gross = sum(w[a] * r[a] for a in pick)
        rets.append(gross - leg * turn)
        w_prev = {a: w[a] * (1 + r[a]) / (1 + gross) for a in pick} if gross > -1 else {}
    return np.array(rets)


def hold(P4, lo, hi, a):
    return np.array([float(np.expm1(r)) if (r := P4.P.fwd(a, t, H)) is not None else 0.0 for t in periods(lo, hi)])


def ew(P4, lo, hi, leg):
    rets, w_prev = [], {}
    for t in periods(lo, hi):
        U = P4.universe(t)
        cand = [a for a in U if P4.P.fwd(a, t, H) is not None]
        w = {a: 1 / len(cand) for a in cand}
        r = {a: float(np.expm1(P4.P.fwd(a, t, H))) for a in cand}
        turn = sum(abs(w.get(a, 0) - w_prev.get(a, 0)) for a in set(w) | set(w_prev))
        g = sum(w[a] * r[a] for a in cand)
        rets.append(g - leg * turn)
        w_prev = {a: w[a] * (1 + r[a]) / (1 + g) for a in cand}
    return np.array(rets)


def economics(P4, lo, hi, subset=None):
    link, btc = hold(P4, lo, hi, "LINKUSDT"), hold(P4, lo, hi, "BTCUSDT")
    out = {"n_periods": len(link), "hold_LINK": float(np.prod(1 + link)), "hold_BTC": float(np.prod(1 + btc)),
           "hold_USD": 1.0}
    for name, leg in (("maker", x1.LEG_MAKER), ("taker", x1.LEG_TAKER)):
        out[f"ew_universe_{name}"] = float(np.prod(1 + ew(P4, lo, hi, leg)))
        for k in KS:
            s = backtest(P4, lo, hi, k, leg, subset=subset)
            rng = np.random.default_rng(100 + k)
            draws = np.array([backtest(P4, lo, hi, k, leg, rng=rng, subset=subset) for _ in range(500)])
            rk = draws.mean(axis=0)
            out[f"top{k}_{name}"] = {
                "wealth": float(np.prod(1 + s)),
                "random_k_wealth_median": float(np.median(np.prod(1 + draws, axis=1))),
                "pct_random_beaten": float((np.prod(1 + draws, axis=1) < np.prod(1 + s)).mean()),
                "excess_vs_random_k_mean": float((s - rk).mean()), "excess_vs_random_k_ci90": x1.block_ci(s - rk, block=3),
                "excess_vs_LINK_mean": float((s - link).mean()), "excess_vs_LINK_ci90": x1.block_ci(s - link, block=3),
                "excess_vs_BTC_mean": float((s - btc).mean()), "excess_vs_BTC_ci90": x1.block_ci(s - btc, block=3),
                "excess_vs_USD_mean": float(s.mean()), "excess_vs_USD_ci90": x1.block_ci(s, block=3)}
    return out


def picks(P4, lo, hi, k=5):
    from collections import Counter
    c = Counter()
    for t in periods(lo, hi):
        U = P4.universe(t)
        cand = [a for a in U if P4.P.fwd(a, t, H) is not None]
        c.update(sorted(cand, key=lambda a: U[a]["vol60"])[:k])
    return c.most_common(15)


def main(stage):
    os.makedirs(RES, exist_ok=True)
    P4 = Panel4(x1.Panel())
    meta = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "assets_loaded": len(P4.P.assets)}
    if stage == "discovery":
        res = {"meta": meta, "tests": tests(P4, *DISC), "economics": economics(P4, *DISC),
               "top5_picks": picks(P4, *DISC)}
        out = "discovery.json"
    elif stage == "holdout":
        assert os.path.exists(os.path.join(RES, "discovery.json"))
        kb = x1.kraken_bases()
        sub = {a for a in P4.P.assets if P4.P.spot[a]["sym"][:-4] in kb}
        res = {"meta": meta, "tests": tests(P4, *HOLD, one_sided=True), "economics": economics(P4, *HOLD),
               "economics_kraken_subset_SURVIVORSHIP_BIASED": economics(P4, *HOLD, subset=sub),
               "economics_full_period": economics(P4, DISC[0], HOLD[1]), "top5_picks": picks(P4, *HOLD)}
        out = "holdout.json"
    else:
        raise SystemExit("unknown stage")
    json.dump(res, open(os.path.join(RES, out), "w"), indent=1, default=float)
    t = res["tests"]
    for k in ("P_ic_vol", "S1_ic_beta", "S2_partial_ic_vol", "S3_quintile_spread_lowvol_minus_highvol"):
        r = t[k]
        print(f"{k:40s} n={r['n']:3d} mean={r['mean']:+.4f} t={r['t']:+.2f} p2={r['p_two_sided']:.4f} mde={r['mde']:.4f}"
              + (f" p1neg={r['p_one_sided_neg']:.4f}" if "p_one_sided_neg" in r else ""))
    print("phase-avg IC vol:", round(t["phase_averaged_ic_vol"], 4), {p: {k: round(v, 4) for k, v in d.items() if v is not None}
                                                                    for p, d in t["phase_robustness"].items()})
    print("per-year:", {y: round(v.get("mean", np.nan), 4) for y, v in t["P_per_year"].items()})
    e = res["economics"]
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in e.items() if not isinstance(v, dict)})
    for k in KS:
        r = e[f"top{k}_maker"]
        print(f"  top{k}: W={r['wealth']:.3f} randmed={r['random_k_wealth_median']:.3f} beat={r['pct_random_beaten']:.2f} "
              f"exRand={r['excess_vs_random_k_mean']:+.4f} {np.round(r['excess_vs_random_k_ci90'], 4)} "
              f"exLINK={r['excess_vs_LINK_mean']:+.4f} {np.round(r['excess_vs_LINK_ci90'], 4)} exBTC={r['excess_vs_BTC_mean']:+.4f}")
    print("top5 picks:", res["top5_picks"][:10])


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "discovery")
