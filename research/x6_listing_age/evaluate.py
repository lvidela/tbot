"""X6 evaluation: listing age beyond volatility (see PREREGISTRATION.md).

Reuses X4's universe (x4_lowvol/evaluate.py) on X1's survivorship-free panel.
  python3 research/x6_listing_age/evaluate.py --stage discovery
  python3 research/x6_listing_age/evaluate.py --stage holdout   (after discovery.json is committed)
"""
import datetime as dt
import importlib.util
import json
import os
import sys

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("x4_evaluate", os.path.join(HERE, "..", "x4_lowvol", "evaluate.py"))
x4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x4)
x1 = x4.x1

RES = os.path.join(HERE, "results")
DAY, H = x1.DAY, x4.H
YOUNG = 180 * DAY
ALPHA = 0.05 / 3
LEG = x1.LEG_MAKER


def age_days(P, a, t):
    return (t - int(P.spot[a]["t"][0])) / DAY


def period_stats(P4, t):
    U = P4.universe(t)
    rows = []
    for a, x in U.items():
        r = P4.P.fwd(a, t, H)
        if r is None or not np.isfinite(x["mom28"]):
            continue
        rows.append((a, np.log(age_days(P4.P, a, t)), x["vol60"], x["mom28"], np.log(x["qv"]), r))
    if len(rows) < 10:
        return None
    A = np.array(rows, dtype=object)
    lage, vol, mom, lqv, R = (np.array(A[:, i], float) for i in range(1, 6))
    ctrl = np.column_stack([x4.rank(vol), x4.rank(mom), x4.rank(lqv)])
    pic = float(np.corrcoef(x1.resid(x4.rank(lage), ctrl), x1.resid(x4.rank(R), ctrl))[0, 1])
    young = lage < np.log(YOUNG / DAY)
    simple = np.expm1(R)
    spread = float(simple[young].mean() - simple[~young].mean()) if young.sum() >= 3 and (~young).sum() >= 3 else None
    return {"t": t, "n": len(R), "n_young": int(young.sum()), "pic_age": pic,
            "ic_age": float(stats.spearmanr(lage, R).statistic), "young_spread": spread,
            "corr_age_vol": float(stats.spearmanr(lage, vol).statistic)}


def tests(P4, lo, hi, one_sided=False):
    ps = [s for t in x4.periods(lo, hi) if (s := period_stats(P4, t)) is not None]
    res = {"P_partial_ic_age": x1.summarize([s["pic_age"] for s in ps]),
           "S1_ic_age": x1.summarize([s["ic_age"] for s in ps]),
           "S2_young_minus_rest": x1.summarize([s["young_spread"] for s in ps if s["young_spread"] is not None]),
           "mean_corr_age_vol": float(np.mean([s["corr_age_vol"] for s in ps])),
           "mean_n_young": float(np.mean([s["n_young"] for s in ps]))}
    for k, direction in (("P_partial_ic_age", 1), ("S1_ic_age", 1), ("S2_young_minus_rest", -1)):
        r = res[k]
        if "t" in r:
            r["bonferroni_pass"] = bool(np.sign(r["mean"]) == direction and r["p_two_sided"] < ALPHA)
            if one_sided:
                r["p_one_sided"] = float(stats.t.sf(direction * r["t"], r["n"] - 1))
    res["phase_robustness"] = {f"phase{ph}": x1.summarize([s["pic_age"] for t in x4.periods(lo, hi, ph)
                                                           if (s := period_stats(P4, t)) is not None]).get("mean")
                               for ph in range(1, 4)}
    res["per_year_pic"] = x1.per_year(ps, "pic_age")
    res["periods"] = ps
    return res


def ew(P4, lo, hi, keep, cap=None, rng=None):
    rets, w_prev = [], {}
    for t in x4.periods(lo, hi):
        U = P4.universe(t)
        cand = [a for a in U if P4.P.fwd(a, t, H) is not None and keep(a, t)]
        if cap is not None:
            cand = list(rng.choice(cand, min(cap, len(cand)), replace=False)) if rng is not None else cand[:cap]
        if not cand:
            rets.append(0.0); w_prev = {}
            continue
        w = {a: 1 / len(cand) for a in cand}
        r = {a: float(np.expm1(P4.P.fwd(a, t, H))) for a in cand}
        turn = sum(abs(w.get(a, 0) - w_prev.get(a, 0)) for a in set(w) | set(w_prev))
        g = sum(w[a] * r[a] for a in cand)
        rets.append(g - LEG * turn)
        w_prev = {a: w[a] * (1 + r[a]) / (1 + g) for a in cand} if g > -1 else {}
    return np.array(rets)


def economics(P4, lo, hi):
    P = P4.P
    old = ew(P4, lo, hi, lambda a, t: age_days(P, a, t) * DAY >= YOUNG)
    allu = ew(P4, lo, hi, lambda a, t: True)
    young = ew(P4, lo, hi, lambda a, t: age_days(P, a, t) * DAY < YOUNG,
               cap=5)   # deterministic: first 5 young names in universe (volume) order
    rng = np.random.default_rng(6)
    n_young = [min(5, sum(1 for a in P4.universe(t) if age_days(P, a, t) * DAY < YOUNG and P.fwd(a, t, H) is not None))
               for t in x4.periods(lo, hi)]
    rand = []
    for _ in range(300):
        rr, i = [], 0
        for t, k in zip(x4.periods(lo, hi), n_young):
            U = [a for a in P4.universe(t) if P.fwd(a, t, H) is not None]
            pick = rng.choice(U, k, replace=False) if k else []
            rr.append(float(np.mean([np.expm1(P.fwd(a, t, H)) for a in pick])) if k else 0.0)
        rand.append(rr)
    rand = np.array(rand).mean(axis=0)
    link = x4.hold(P4, lo, hi, "LINKUSDT")
    W = lambda x: float(np.prod(1 + x))  # noqa: E731
    return {"EW_old": W(old), "EW_all": W(allu), "young_basket": W(young), "hold_LINK": W(link), "hold_USD": 1.0,
            "old_minus_all_mean": float((old - allu).mean()), "old_minus_all_ci90": x1.block_ci(old - allu, block=3),
            "young_minus_random_mean_gross": float((young - rand).mean()),
            "young_minus_random_ci90": x1.block_ci(young - rand, block=3),
            "periods_with_young": int(sum(1 for k in n_young if k))}


def main(stage):
    os.makedirs(RES, exist_ok=True)
    P4 = x4.Panel4(x1.Panel())
    lo, hi = x4.DISC if stage == "discovery" else x4.HOLD
    if stage == "holdout":
        assert os.path.exists(os.path.join(RES, "discovery.json"))
    res = {"meta": {"stage": stage, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat()},
           "tests": tests(P4, lo, hi, stage == "holdout"), "economics": economics(P4, lo, hi)}
    json.dump(res, open(os.path.join(RES, f"{stage}.json"), "w"), indent=1, default=float)
    t = res["tests"]
    for k in ("P_partial_ic_age", "S1_ic_age", "S2_young_minus_rest"):
        r = t[k]
        print(f"{k:22s} " + ", ".join(f"{a}={b:.4f}" if isinstance(b, float) else f"{a}={b}" for a, b in r.items() if a != "ci95"))
    print("corr(age,vol)", round(t["mean_corr_age_vol"], 3), "mean n_young", round(t["mean_n_young"], 2),
          "phases", {k: round(v, 4) for k, v in t["phase_robustness"].items()})
    print("per-year pic", {y: round(v.get("mean", np.nan), 4) for y, v in t["per_year_pic"].items()})
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in res["economics"].items()})


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "discovery")
