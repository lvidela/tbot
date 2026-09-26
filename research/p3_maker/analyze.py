"""P3 analysis: virtual maker fill probability and post-fill markout (see PREREGISTRATION.md).

Reads research/p3_maker/raw/*.jsonl (and any committed research/p3_maker/derived/orders_*.jsonl), resolves every
virtual order whose 60-minute window is complete, appends resolved outcomes to derived/, and prints the
pre-registered tables.

  python3 research/p3_maker/analyze.py            resolve + report (report only covers resolved orders)
"""
import glob
import json
import os
import sys
from bisect import bisect_left, bisect_right

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
DER = os.path.join(HERE, "derived")
FILL_T = (60, 300, 1800)          # seconds
MARK_H = (60, 300, 1800)
TICK_TOL = 45                     # seconds: nearest tick after target must be within this
WINDOW = max(FILL_T) + max(MARK_H) + TICK_TOL
MAX_GAP = 120                     # AMENDMENT 1 (2026-09-26): exclude orders whose window has a sampler gap > 120 s


def jl(path):
    return [json.loads(x) for x in open(path) if x.strip()] if os.path.exists(path) else []


def mid_after(ticks, target):
    """Mid of the first tick at or after target, if within TICK_TOL."""
    ts = ticks["ts"]
    i = bisect_left(ts, target)
    if i < len(ts) and ts[i] - target <= TICK_TOL:
        return (ticks["bid"][i] + ticks["ask"][i]) / 2
    return None


def max_gap(ticks, a, b):
    """Largest gap between consecutive ticks covering [a, b] (the sampler's heartbeat; trades are polled in the
    same cycle, so a tick gap is also a trade-coverage gap)."""
    ts = ticks["ts"]
    i, j = bisect_left(ts, a), bisect_right(ts, b)
    pts = [a] + ts[i:j] + [b]
    return float(max(y - x for x, y in zip(pts, pts[1:])))


def gap_of(r, flags):
    return r.get("max_tick_gap_s", flags.get(r["id"]))


def resolve(order, trades, ticks):
    """Virtual post-only BID at order['bid'] and ASK at order['ask'], placed at t0.
    strict fill: a trade prints strictly through the price (bid: price < B; ask: price > A).
    touch fill: a trade at the price by the aggressing side (bid: seller-initiated 's' at B; ask: 'b' at A).
    Markout (bps, positive = favourable to the maker): bid (mid - B)/B, ask (A - mid)/A, at fill + h."""
    t0 = order["t0"]
    tt = trades["ts"]
    lo, hi = bisect_right(tt, t0), bisect_right(tt, t0 + max(FILL_T))
    out = {"id": order["id"], "pair": order["pair"], "t0": t0, "quintile": order["quintile"],
           "regime": order["regime"], "vol_ratio": order["vol_ratio"],
           "spread_bps": (order["ask"] - order["bid"]) / ((order["ask"] + order["bid"]) / 2) * 1e4}
    m0 = mid_after(ticks, t0)
    out["max_tick_gap_s"] = max_gap(ticks, t0, t0 + WINDOW)
    for h in MARK_H:
        mh = mid_after(ticks, t0 + h)
        out[f"drift_{h}_bps"] = (mh / m0 - 1) * 1e4 if (m0 and mh) else None   # unconditional control
    for side, px in (("bid", order["bid"]), ("ask", order["ask"])):
        strict = touch = None
        for i in range(lo, hi):
            p, s, t = trades["price"][i], trades["side"][i], tt[i]
            through = p < px if side == "bid" else p > px
            at = (p == px and s == ("s" if side == "bid" else "b"))
            if touch is None and (through or at):
                touch = t
            if strict is None and through:
                strict = t
                break
        for kind, tf in (("strict", strict), ("touch", touch)):
            out[f"{side}_{kind}_fill_s"] = (tf - t0) if tf is not None else None
            for h in MARK_H:
                key = f"{side}_{kind}_markout_{h}_bps"
                if tf is None:
                    out[key] = None
                    continue
                mh = mid_after(ticks, tf + h)
                out[key] = None if mh is None else ((mh - px) / px * 1e4 if side == "bid" else (px - mh) / px * 1e4)
    return out


def load_raw():
    trades, ticks = {}, {}
    for r in jl(os.path.join(RAW, "trades.jsonl")):
        d = trades.setdefault(r["pair"], [])
        d.append((r["ts"], r["price"], r["side"]))
    for r in jl(os.path.join(RAW, "ticks.jsonl")):
        ticks.setdefault(r["pair"], []).append((r["ts"], r["bid"], r["ask"]))
    T = {p: {"ts": [x[0] for x in sorted(v)], "price": [x[1] for x in sorted(v)], "side": [x[2] for x in sorted(v)]}
         for p, v in trades.items()}
    K = {p: {"ts": [x[0] for x in sorted(v)], "bid": [x[1] for x in sorted(v)], "ask": [x[2] for x in sorted(v)]}
         for p, v in ticks.items()}
    return T, K


def resolve_all():
    """Resolve raw orders whose full window has elapsed within the recorded tick coverage; append new ones."""
    os.makedirs(DER, exist_ok=True)
    done = {r["id"] for f in glob.glob(os.path.join(DER, "orders_*.jsonl")) for r in jl(f)}
    T, K = load_raw()
    new = []
    for o in jl(os.path.join(RAW, "orders.jsonl")):
        p = o["pair"]
        if o["id"] in done or p not in K or p not in T:
            continue
        if K[p]["ts"][-1] < o["t0"] + WINDOW:
            continue                           # window not yet covered by the sampler
        new.append(resolve(o, T[p], K[p]))
    if new:
        day = __import__("datetime").datetime.utcfromtimestamp(new[0]["t0"]).strftime("%Y%m%d")
        with open(os.path.join(DER, f"orders_{day}_{int(new[0]['t0'])}.jsonl"), "a") as f:
            for r in new:
                f.write(json.dumps(r) + "\n")
    return len(new)


def cluster_boot(values, clusters, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    by = {}
    for v, c in zip(values, clusters):
        by.setdefault(c, []).append(v)
    keys = list(by)
    if len(keys) < 2:
        return None
    ms = []
    for _ in range(n):
        pick = rng.choice(len(keys), len(keys))
        vals = [x for i in pick for x in by[keys[i]]]
        ms.append(np.mean(vals))
    return [float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))]


def summarize(rows, fill_key, t_s, mark_key):
    """Fill probability within t_s (lower=strict, upper=touch, mid=strict+0.5*(touch-only)) and markout."""
    out = {"n_orders": len(rows)}
    if not rows:
        return out
    cl = [f"{r['pair']}-{int(r['t0'] // 3600)}" for r in rows]
    for side in ("bid", "ask"):
        s = np.array([(r[f"{side}_strict_fill_s"] is not None and r[f"{side}_strict_fill_s"] <= t_s) for r in rows], float)
        u = np.array([(r[f"{side}_touch_fill_s"] is not None and r[f"{side}_touch_fill_s"] <= t_s) for r in rows], float)
        mid = s + 0.5 * (u - s)
        out[f"{side}_fill_{t_s}s"] = {"lower": float(s.mean()), "upper": float(u.mean()), "mid": float(mid.mean()),
                                      "mid_ci95": cluster_boot(mid, cl)}
        mk = [(r[f"{side}_strict_markout_{mark_key}_bps"], c) for r, c in zip(rows, cl)
              if r[f"{side}_strict_markout_{mark_key}_bps"] is not None]
        if mk:
            v, c = zip(*mk)
            out[f"{side}_strict_markout_{mark_key}s_bps"] = {"n": len(v), "mean": float(np.mean(v)),
                                                            "ci95": cluster_boot(v, c)}
    return out


def backfill_gap_flags():
    """AMENDMENT 1: rows resolved before max_tick_gap_s existed get their gap from raw ticks, appended to
    derived/gapflags.jsonl (append-only). Rows whose raw ticks are gone stay unknown and are excluded."""
    path = os.path.join(DER, "gapflags.jsonl")
    have = {r["id"] for r in jl(path)}
    _, K = load_raw()
    new = []
    for f in sorted(glob.glob(os.path.join(DER, "orders_*.jsonl"))):
        for r in jl(f):
            if "max_tick_gap_s" in r or r["id"] in have or r["pair"] not in K:
                continue
            new.append({"id": r["id"], "max_tick_gap_s": max_gap(K[r["pair"]], r["t0"], r["t0"] + WINDOW)})
    with open(path, "a") as fh:
        for x in new:
            fh.write(json.dumps(x) + "\n")
    return len(new)


def report():
    flags = {r["id"]: r["max_tick_gap_s"] for r in jl(os.path.join(DER, "gapflags.jsonl"))}
    all_rows = [r for f in sorted(glob.glob(os.path.join(DER, "orders_*.jsonl"))) for r in jl(f)]
    rows = [r for r in all_rows if gap_of(r, flags) is not None and gap_of(r, flags) <= MAX_GAP]
    res = {"n_resolved": len(all_rows), "n_used_after_gap_filter": len(rows),
           "n_excluded_gap_or_unknown": len(all_rows) - len(rows), "by_regime": {}, "by_quintile": {}}
    for reg in ("calm", "volatile"):
        sub = [r for r in rows if r["regime"] == reg]
        res["by_regime"][reg] = {f"T{t}": summarize(sub, None, t, 300) for t in FILL_T}
    for q in range(0, 6):
        sub = [r for r in rows if r["quintile"] == q]
        res["by_quintile"][str(q)] = summarize(sub, None, 300, 300)
    json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1)
    print(json.dumps({"n_resolved": res["n_resolved"], "n_used": res["n_used_after_gap_filter"],
                      "regime_T300": {k: v["T300"] for k, v in res["by_regime"].items()}}, indent=1)[:4000])
    return res


if __name__ == "__main__":
    print("resolved new:", resolve_all())
    print("gap flags backfilled:", backfill_gap_flags())
    report()
