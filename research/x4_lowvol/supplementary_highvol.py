"""SUPPLEMENTARY, NOT PRE-REGISTERED (added after the X4 holdout was run).
Long-only in the k HIGHEST-vol60 names (k = 5, 10), 4-weekly, maker costs, vs random-k and hold-LINK.
Question: what does buying the high-vol end of the universe do? It bears on the live tactical mode,
which enters high-volatility names. Run: python3 research/x4_lowvol/supplementary_highvol.py"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("x4e", os.path.join(HERE, "evaluate.py"))
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


def highvol(P4, lo, hi, k, leg):
    rets, w_prev = [], {}
    for t in e.periods(lo, hi):
        U = P4.universe(t)
        cand = [a for a in U if P4.P.fwd(a, t, e.H) is not None]
        pick = sorted(cand, key=lambda a: -U[a]["vol60"])[:k]
        w = {a: 1 / k for a in pick}
        turn = sum(abs(w.get(a, 0) - w_prev.get(a, 0)) for a in set(w) | set(w_prev))
        r = {a: float(np.expm1(P4.P.fwd(a, t, e.H))) for a in pick}
        g = sum(w[a] * r[a] for a in pick)
        rets.append(g - leg * turn)
        w_prev = {a: w[a] * (1 + r[a]) / (1 + g) for a in pick} if g > -1 else {}
    return np.array(rets)


P4 = e.Panel4(e.x1.Panel())
out = {}
for name, (lo, hi) in (("discovery", e.DISC), ("holdout", e.HOLD)):
    link = e.hold(P4, lo, hi, "LINKUSDT")
    for k in (5, 10):
        s = highvol(P4, lo, hi, k, e.x1.LEG_MAKER)
        rng = np.random.default_rng(7 + k)
        rk = np.array([e.backtest(P4, lo, hi, k, e.x1.LEG_MAKER, rng=rng) for _ in range(300)]).mean(axis=0)
        out[f"{name}_high{k}"] = {"wealth": float(np.prod(1 + s)), "mean_per_period": float(s.mean()),
                                  "median_per_period": float(np.median(s)),
                                  "excess_vs_random_k_mean": float((s - rk).mean()), "excess_vs_random_k_ci90": e.x1.block_ci(s - rk, block=3),
                                  "excess_vs_LINK_mean": float((s - link).mean()), "excess_vs_LINK_ci90": e.x1.block_ci(s - link, block=3)}
        print(name, k, {a: (round(b, 4) if isinstance(b, float) else [round(c, 4) for c in b]) for a, b in out[f"{name}_high{k}"].items()})
json.dump(out, open(os.path.join(HERE, "results", "supplementary_highvol.json"), "w"), indent=1)
