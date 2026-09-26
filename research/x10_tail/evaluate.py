"""X10: independent out-of-sample check of the live agent's ARMED LINK tail-reversal bet
(research/findings/2026-09-26_prereg_link_tail_reversal.md), on history the live agent did not use.

Rule (copied exactly): completed daily bar with |log return| >= 2.5 sigma, sigma = sd of the trailing 720 daily
log returns as of that bar; trade AGAINST the move; exit at +1 day (also +2, +3 reported); 2 maker legs 0.92%.
Non-overlapping: after a trigger, the next may occur only after the exit.

Run: python3 research/x10_tail/evaluate.py  -> results.json
"""
import json
import os

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
COST = 0.0092
LIVE_SAMPLE_START = 1728172800        # 2024-10-06 00:00 UTC: first bar of the live agent's 720-bar sample
DAY = 86400


def load(name):
    rows = json.load(open(os.path.join(RAW, name)))["rows"]
    return np.array([r[0] for r in rows], dtype=np.int64), np.array([r[4] for r in rows], float)


def events(t, c, k=2.5, win=720, h=1, end_ts=LIVE_SAMPLE_START):
    """Bars i with |r_i| >= k*sd(r_{i-win..i-1}); outcome = -sign(r_i) * (c[i+h]/c[i]-1) - COST.
    Only triggers whose bar AND exit lie strictly before the live agent's sample."""
    r = np.diff(np.log(c))                     # r[j] is the return of bar j+1 (close j -> close j+1)
    out, busy = [], -1
    for j in range(win, len(r)):
        i = j + 1                              # bar index whose close completes the move
        if i <= busy or i + h >= len(c) or t[i + h] >= end_ts:
            continue
        sd = float(np.std(r[j - win:j], ddof=1))
        if abs(r[j]) >= k * sd:
            fwd = c[i + h] / c[i] - 1.0
            out.append({"t": int(t[i]), "r": float(r[j]), "sigma": sd, "net": float(-np.sign(r[j]) * fwd - COST)})
            busy = i + h
    return out


def summ(ev):
    x = np.array([e["net"] for e in ev])
    if len(x) < 2:
        return {"n": len(x), "values": x.tolist()}
    m, se = float(x.mean()), float(x.std(ddof=1) / np.sqrt(len(x)))
    return {"n": len(x), "mean_net": m, "median_net": float(np.median(x)), "se": se, "t": m / se,
            "p_one_sided_pos": float(stats.t.sf(m / se, len(x) - 1)), "mde": 2.8 * se,
            "hit_rate": float((x > 0).mean()), "n_up_moves": int(sum(e["r"] > 0 for e in ev))}


def main():
    res = {}
    for venue, f in (("binance", "binance_LINK_1d.json"), ("coinbase", "coinbase_LINK_1d.json")):
        t, c = load(f)
        res[venue] = {}
        for h in (1, 2, 3):
            ev = events(t, c, h=h)
            res[venue][f"h{h}"] = {**summ(ev), "first": ev[0]["t"] if ev else None, "last": ev[-1]["t"] if ev else None}
        # pre-declared sensitivity: 365-day sigma window (more history usable)
        res[venue]["h1_sigma365"] = summ(events(t, c, win=365, h=1))
    json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1)
    for v, d in res.items():
        for k, s in d.items():
            print(v, k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in s.items() if a != "values"})


if __name__ == "__main__":
    main()
