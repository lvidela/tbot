"""X3 evaluation: rebound after market-wide capitulation days (see PREREGISTRATION.md).

Reuses X1's survivorship-free Binance panel (research/x1_funding/raw).
  python3 research/x3_capitulation/evaluate.py --stage discovery
  python3 research/x3_capitulation/evaluate.py --stage holdout   (after discovery.json is committed)
"""
import datetime as dt
import importlib.util
import json
import os
import sys

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("x1_evaluate", os.path.join(HERE, "..", "x1_funding", "evaluate.py"))
x1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x1)

RES = os.path.join(HERE, "results")
DAY, WEEK = x1.DAY, x1.WEEK
LEG, STRESS = 0.0046, 0.0092
MON0 = x1.ts(2020, 1, 6)
DISC = (x1.ts(2020, 3, 15), x1.ts(2023, 12, 31))
HOLD = (x1.ts(2024, 1, 1), x1.ts(2026, 9, 19))
ALPHA = 0.05 / 3


class Market:
    """Daily equal-weight index over X1's weekly universe (Monday <= T), with no look-ahead."""

    def __init__(self, P, start=MON0, end=x1.ts(2026, 9, 24)):
        self.P = P
        self.days = list(range(start + DAY, end + DAY, DAY))
        self.M, self.U = {}, {}
        for T in self.days:
            mon = MON0 + ((T - MON0) // WEEK) * WEEK
            U = P.universe(mon)
            rets = {}
            for a in U:
                c0, c1 = P.close_at(a, T - DAY), P.close_at(a, T)
                if c0 and c1:
                    rets[a] = float(np.log(c1 / c0))
            self.U[T] = rets
            if len(rets) >= 10:
                self.M[T] = float(np.mean(np.expm1(list(rets.values()))))

    def sd60(self, T):
        v = [self.M[t] for t in range(T - 60 * DAY, T, DAY) if t in self.M]
        return float(np.std(v, ddof=1)) if len(v) >= 50 else None

    def events(self, lo, hi, k_sigma=2.5, gap=5):
        out, last = [], None
        for T in self.days:
            if T < lo or T > hi or T not in self.M:
                continue
            sd = self.sd60(T)
            btc = self.U[T].get("BTCUSDT")
            if sd is None or btc is None:
                continue
            if self.M[T] <= -k_sigma * sd and btc < 0 and (last is None or T - last >= gap * DAY):
                out.append(T)
                last = T
        return out

    def fwd(self, a, T, h):
        c0, c1 = self.P.close_at(a, T), self.P.close_upto(a, T + h * DAY)
        return float(np.log(c1 / c0)) if c0 and c1 else None

    def ew_fwd(self, T, h, names=None):
        names = names if names is not None else list(self.U[T])
        r = [self.fwd(a, T, h) for a in names]
        r = [x for x in r if x is not None]
        return float(np.mean(np.expm1(r))) if r else None

    def uncond(self, lo, hi, h):
        """Unconditional mean h-day EW simple return and LINK log return, non-overlapping windows."""
        ew, link = [], []
        T = lo
        while T + h * DAY <= hi + h * DAY and T in self.U:
            e = self.ew_fwd(T, h)
            if e is not None:
                ew.append(e)
            lr = self.fwd("LINKUSDT", T, h)
            if lr is not None:
                link.append(lr)
            T += h * DAY
        return float(np.mean(ew)), float(np.mean(link)), len(ew)


def summ(x, one_sided=None):
    x = np.array([v for v in x if v is not None and np.isfinite(v)])
    if len(x) < 3:
        return {"n": len(x), "values": x.tolist()}
    m, se = float(x.mean()), float(x.std(ddof=1) / np.sqrt(len(x)))
    t = m / se if se > 0 else float("nan")
    out = {"n": len(x), "mean": m, "median": float(np.median(x)), "se": se, "t": t,
           "p_two_sided": float(2 * stats.t.sf(abs(t), len(x) - 1)), "mde": 2.8 * se}
    if one_sided == "pos":
        out["p_one_sided"] = float(stats.t.sf(t, len(x) - 1))
    elif one_sided == "neg":
        out["p_one_sided"] = float(stats.t.cdf(t, len(x) - 1))
    return out


def boot_ci(x, n=5000, seed=0):
    x = np.asarray([v for v in x if v is not None])
    if len(x) < 3:
        return None
    rng = np.random.default_rng(seed)
    m = [rng.choice(x, len(x)).mean() for _ in range(n)]
    return [float(np.percentile(m, 5)), float(np.percentile(m, 95))]


def study(mk, lo, hi, h=3, k_sigma=2.5, one_sided=False, exclude=()):
    ev = [T for T in mk.events(lo, hi, k_sigma) if T not in exclude]
    ew_u, link_u, n_u = mk.uncond(lo, hi, h)
    p1, p2, p3, e1, e1s, e2, e3, detail = [], [], [], {3: [], 5: []}, {3: [], 5: []}, [], [], []
    for T in ev:
        rets = mk.U[T]
        ew = mk.ew_fwd(T, h)
        p1.append(ew - ew_u if ew is not None else None)
        names = [a for a in rets if mk.fwd(a, T, h) is not None]
        if len(names) >= 10:
            p2.append(float(stats.spearmanr([rets[a] for a in names], [mk.fwd(a, T, h) for a in names]).statistic))
        lr = mk.fwd("LINKUSDT", T, h)
        p3.append(lr - link_u if lr is not None else None)
        if lr is not None:
            rl = float(np.expm1(lr))
            for k in (3, 5):
                worst = sorted(names, key=lambda a: rets[a])[:k]
                rb = float(np.mean([np.expm1(mk.fwd(a, T, h)) for a in worst]))
                e1[k].append((1 - LEG) ** 4 * (1 + rb) - (1 + rl))
                e1s[k].append((1 - STRESS) ** 4 * (1 + rb) - (1 + rl))
            e2.append((1 - LEG) ** 2 * (1 + rl) - 1)
        if ew is not None:
            e3.append((1 - LEG) ** 2 * (1 + ew) - 1)
        detail.append({"T": dt.datetime.fromtimestamp(T, dt.timezone.utc).date().isoformat(),
                       "M": mk.M[T], "sd60": mk.sd60(T), "ew_fwd": ew, "link_fwd": lr})
    years = (hi - lo) / (365.25 * DAY)
    os1 = "pos" if one_sided else None
    res = {"n_events": len(ev), "events_per_year": len(ev) / years,
           "uncond": {"ew_mean_h": ew_u, "link_mean_h_log": link_u, "n_windows": n_u},
           "P1_ew_excess": summ(p1, os1), "P2_ic_crash_vs_fwd": summ(p2, "neg" if one_sided else None),
           "P3_link_excess": summ(p3, os1), "events": detail}
    for k in ("P1_ew_excess", "P3_link_excess"):
        r = res[k]
        r["bonferroni_pass"] = bool("t" in r and r["mean"] > 0 and r["p_two_sided"] < ALPHA)
    r = res["P2_ic_crash_vs_fwd"]
    r["bonferroni_pass"] = bool("t" in r and r["mean"] < 0 and r["p_two_sided"] < ALPHA)
    res["econ"] = {}
    for k in (3, 5):
        res["econ"][f"E1_rotate_LINK_to_worst{k}_vs_LINK_maker"] = {**summ(e1[k]), "ci90": boot_ci(e1[k])}
        res["econ"][f"E1_rotate_LINK_to_worst{k}_vs_LINK_stress"] = {**summ(e1s[k]), "ci90": boot_ci(e1s[k])}
    res["econ"]["E2_USD_buy_LINK"] = {**summ(e2), "ci90": boot_ci(e2)}
    res["econ"]["E3_USD_buy_EW"] = {**summ(e3), "ci90": boot_ci(e3)}
    for v in res["econ"].values():
        if "mean" in v:
            v["per_year"] = v["mean"] * res["events_per_year"]
    return res


def run(stage):
    os.makedirs(RES, exist_ok=True)
    mk = Market(x1.Panel())
    lo, hi = DISC if stage == "discovery" else HOLD
    if stage == "holdout":
        assert os.path.exists(os.path.join(RES, "discovery.json"))
    one = stage == "holdout"
    res = {"meta": {"stage": stage, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat()},
           "primary_h3": study(mk, lo, hi, 3, 2.5, one)}
    res["robust"] = {f"h{h}": study(mk, lo, hi, h, 2.5, one) for h in (1, 5)}
    res["robust"].update({f"k{ks}": study(mk, lo, hi, 3, ks, one) for ks in (2.0, 3.0)})
    res["robust"]["exclude_covid"] = study(mk, lo, hi, 3, 2.5, one, exclude=(x1.ts(2020, 3, 13), x1.ts(2020, 3, 12)))
    json.dump(res, open(os.path.join(RES, f"{stage}.json"), "w"), indent=1)
    p = res["primary_h3"]
    print(f"{stage}: events {p['n_events']} ({p['events_per_year']:.1f}/yr)  uncond {p['uncond']}")
    print("event dates:", [e["T"] for e in p["events"]])
    for k in ("P1_ew_excess", "P2_ic_crash_vs_fwd", "P3_link_excess"):
        r = p[k]
        print(f"  {k:22s} " + ", ".join(f"{a}={b:.4f}" if isinstance(b, float) else f"{a}={b}" for a, b in r.items() if a != "values"))
    for k, v in p["econ"].items():
        print(f"  {k:40s} mean={v.get('mean', float('nan')):+.4f} median={v.get('median', float('nan')):+.4f} ci90={v.get('ci90')} per_yr={v.get('per_year', float('nan')):+.4f}")
    for name, r in res["robust"].items():
        print(f"  robust {name:14s} n={r['n_events']:3d} P1={r['P1_ew_excess'].get('mean', float('nan')):+.4f} "
              f"(t={r['P1_ew_excess'].get('t', float('nan')):+.2f}) P2={r['P2_ic_crash_vs_fwd'].get('mean', float('nan')):+.4f} "
              f"(t={r['P2_ic_crash_vs_fwd'].get('t', float('nan')):+.2f}) P3={r['P3_link_excess'].get('mean', float('nan')):+.4f} "
              f"(t={r['P3_link_excess'].get('t', float('nan')):+.2f})")


if __name__ == "__main__":
    run(sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "discovery")
