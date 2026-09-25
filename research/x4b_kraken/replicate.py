"""X4b: replicate X4's low-vol IC on Kraken daily data (see PREREGISTRATION.md).
Run: python3 research/x4b_kraken/replicate.py  -> results.json"""
import json
import os

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
OHLC = os.path.join(HERE, "..", "tsmom", "ohlc_long.json")
DAY = 86400
H = 28 * DAY
ANCHOR = 1578268800          # 2020-01-06 00:00 UTC (X4 grid)
END = 1790208000             # 2026-09-24 00:00 UTC, open time of the last bar used


def load(path=OHLC):
    d = json.load(open(path))
    out = {}
    for a, v in d.items():
        rows = v["1440"][:-1]                       # drop partial last bar
        out[a] = {int(r[0]): float(r[4]) for r in rows}
    return out


def close_at(s, t):
    return s.get(t - DAY)                           # close(t) = close of the bar opened at t - 1d


def features(s, t):
    cl = [s.get(t - DAY * k) for k in range(61, 0, -1)]
    if any(c is None for c in cl):
        return None
    return float(np.std(np.diff(np.log(cl)), ddof=1))


def grid(data, phase=0):
    first = min(min(s) for s in data.values())
    t, out = ANCHOR + phase * 7 * DAY, []
    while t + H - DAY <= END:
        if t - 61 * DAY >= first:
            out.append(t)
        t += H
    return out


def period(data, t):
    rows = []
    for a, s in data.items():
        v = features(s, t)
        c0, c1 = close_at(s, t), close_at(s, t + H)
        if v is None or v < 0.005 or c0 is None or c1 is None:
            continue
        rows.append((a, v, float(np.log(c1 / c0))))
    return rows


def summarize(x):
    x = np.array(x)
    m, se = float(x.mean()), float(x.std(ddof=1) / np.sqrt(len(x)))
    t = m / se
    return {"n": len(x), "mean": m, "se": se, "t": t, "p_one_sided_neg": float(stats.t.cdf(t, len(x) - 1)),
            "mde": 2.8 * se}


def baskets(data, ts, k=5, leg=0.0046, seed=0):
    rng = np.random.default_rng(seed)

    def run(select):
        rets, w_prev = [], {}
        for t in ts:
            rows = period(data, t)
            pick = select(rows)
            w = {a: 1 / k for a in pick}
            turn = sum(abs(w.get(a, 0) - w_prev.get(a, 0)) for a in set(w) | set(w_prev))
            r = {a: float(np.expm1(x)) for a, _, x in rows if a in w}
            g = sum(w[a] * r[a] for a in pick)
            rets.append(g - leg * turn)
            w_prev = {a: w[a] * (1 + r[a]) / (1 + g) for a in pick}
        return np.array(rets)

    low = run(lambda rows: [a for a, *_ in sorted(rows, key=lambda x: x[1])[:k]])
    high = run(lambda rows: [a for a, *_ in sorted(rows, key=lambda x: -x[1])[:k]])
    rand = np.array([run(lambda rows: list(rng.choice([a for a, *_ in rows], k, replace=False))) for _ in range(500)])
    link = np.array([float(np.expm1(x)) for t in ts for a, _, x in period(data, t) if a == "LINKUSD"])
    W = lambda x: float(np.prod(1 + x))  # noqa: E731
    return {"low5": W(low), "high5": W(high), "random5_median": float(np.median(np.prod(1 + rand, axis=1))),
            "hold_LINK": W(link), "low5_minus_random_mean": float((low - rand.mean(0)).mean()),
            "high5_minus_random_mean": float((high - rand.mean(0)).mean()),
            "low5_minus_LINK_mean": float((low - link).mean())}


def main():
    data = load()
    res = {"phases": {}}
    for ph in range(4):
        ts = grid(data, ph)
        ics = [stats.spearmanr([v for _, v, _ in r], [x for *_, x in r]).statistic for t in ts if len(r := period(data, t)) >= 10]
        res["phases"][f"phase{ph}"] = summarize(ics)
    p = res["phases"]["phase0"]
    res["primary"] = p
    res["verdict"] = ("REPLICATED" if p["p_one_sided_neg"] < 0.05 else
                      "NOT REPLICATED" if p["mean"] >= 0 else "INCONCLUSIVE")
    ts = grid(data, 0)
    res["periods"] = [{"t": t, "n": len(period(data, t))} for t in ts]
    res["baskets_phase0_maker"] = baskets(data, ts)
    pct = []
    for t in ts:
        r = sorted(period(data, t), key=lambda x: x[1])
        names = [a for a, *_ in r]
        if "LINKUSD" in names:
            pct.append(names.index("LINKUSD") / (len(names) - 1))
    res["LINK_vol_percentile"] = {"median": float(np.median(pct)), "min": float(min(pct)), "max": float(max(pct))}
    json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "periods"}, indent=1))


if __name__ == "__main__":
    main()
