"""E1: live maker-execution calibration vs P3 virtual fills (see SPEC.md). Frozen before any live E1 order.

Inputs:
- live orders: data/execution_log.json rows with "experiment" == "E1" (fields already logged by the live
  system: ts, pair, side, post_only, status, vol_exec, requested_vol, fee, cost, latency_sec, regime, vol_ratio);
- P3 virtual outcomes: research/p3_maker/derived/*.jsonl (gap-filtered, amendment 1);
- markouts reconstructed from Kraken PUBLIC Trades (historical `since`), so they do not depend on live logging.

  python3 research/e1_calibration/analyze_e1.py            -> research/e1_calibration/results.json
"""
import datetime as dt
import glob
import json
import os
import time

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
P3DER = os.path.join(HERE, "..", "p3_maker", "derived")
PAIRS = ("LINKUSD", "XBTUSD", "XRPUSD")
FILL_T = 300
MARK_H = 300
MAX_GAP = 120
P3_WINDOW = 7200          # P3 virtual orders within +-2 h of the live order form its paired bracket


def ts_of(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()


def live_orders(path=os.path.join(ROOT, "data", "execution_log.json")):
    rows = json.load(open(path)) if os.path.exists(path) else []
    return [r for r in rows if r.get("experiment") == "E1" and r.get("post_only") and r.get("pair") in PAIRS]


def p3_rows():
    flags = {}
    fp = os.path.join(P3DER, "gapflags.jsonl")
    if os.path.exists(fp):
        flags = {json.loads(x)["id"]: json.loads(x)["max_tick_gap_s"] for x in open(fp) if x.strip()}
    out = []
    for f in glob.glob(os.path.join(P3DER, "orders_*.jsonl")):
        for x in open(f):
            if x.strip():
                r = json.loads(x)
                g = r.get("max_tick_gap_s", flags.get(r["id"]))
                if g is not None and g <= MAX_GAP:
                    out.append(r)
    return out


def live_filled_within(o, t=FILL_T):
    return o.get("status") == "closed" and float(o.get("vol_exec") or 0) > 0 and (o.get("latency_sec") or 1e9) <= t


def p3_bracket(o, p3):
    """P3 strict/touch 5-min fill rates for the same pair and side within +-2 h of the live order."""
    side = "bid" if o["side"] == "buy" else "ask"
    t0 = ts_of(o["ts"])
    near = [r for r in p3 if r["pair"] == o["pair"] and abs(r["t0"] - t0) <= P3_WINDOW]
    if not near:
        return None
    s = np.mean([(r[f"{side}_strict_fill_s"] is not None and r[f"{side}_strict_fill_s"] <= FILL_T) for r in near])
    u = np.mean([(r[f"{side}_touch_fill_s"] is not None and r[f"{side}_touch_fill_s"] <= FILL_T) for r in near])
    mk = [r[f"{side}_strict_markout_{MARK_H}_bps"] for r in near if r[f"{side}_strict_markout_{MARK_H}_bps"] is not None]
    return {"n": len(near), "strict": float(s), "touch": float(u), "markout_mean": float(np.mean(mk)) if mk else None}


def public_price_after(pair, t, cache={}):
    """Last public trade price at or before t (paging Kraken Trades from t - 600 s)."""
    import requests
    key = (pair, int(t))
    if key in cache:
        return cache[key]
    r = requests.get("https://api.kraken.com/0/public/Trades", params={"pair": pair, "since": str(int((t - 600) * 1e9))},
                     timeout=30).json()
    k = next(x for x in r["result"] if x != "last")
    px = [float(x[0]) for x in r["result"][k] if float(x[2]) <= t]
    cache[key] = px[-1] if px else None
    time.sleep(1.1)
    return cache[key]


def markout_bps(o):
    if not live_filled_within(o, 10 ** 9):
        return None
    fill_px = float(o["cost"]) / float(o["vol_exec"])
    t_fill = ts_of(o["ts"]) + (o.get("latency_sec") or 0)
    p = public_price_after(o["pair"], t_fill + MARK_H)
    if p is None:
        return None
    return (p - fill_px) / fill_px * 1e4 if o["side"] == "buy" else (fill_px - p) / fill_px * 1e4


def clopper(k, n):
    lo = stats.beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0
    hi = stats.beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
    return [float(lo), float(hi)]


def evaluate(orders, p3, markout_fn=markout_bps):
    res = {}
    for regime in ("calm", "volatile"):
        sub = [o for o in orders if o.get("regime") == regime]
        k = sum(live_filled_within(o) for o in sub)
        br = [b for o in sub if (b := p3_bracket(o, p3)) is not None]
        mk = [m for o in sub if (m := markout_fn(o)) is not None]
        r = {"n_orders": len(sub), "live_fill_5min": (k / len(sub)) if sub else None,
             "live_fill_ci95": clopper(k, len(sub)) if sub else None,
             "p3_paired_n": len(br),
             "p3_bracket_mean": [float(np.mean([b["strict"] for b in br])), float(np.mean([b["touch"] for b in br]))] if br else None,
             "live_markout_mean_bps": float(np.mean(mk)) if mk else None, "live_markout_n": len(mk),
             "live_markout_ci95": ([float(np.mean(mk) - 1.96 * np.std(mk, ddof=1) / np.sqrt(len(mk))),
                                    float(np.mean(mk) + 1.96 * np.std(mk, ddof=1) / np.sqrt(len(mk)))] if len(mk) >= 3 else None),
             "p3_markout_mean_bps": (float(np.mean([b["markout_mean"] for b in br if b["markout_mean"] is not None]))
                                     if any(b["markout_mean"] is not None for b in br) else None)}
        if r["live_fill_ci95"] and r["p3_bracket_mean"]:
            lo, hi = r["live_fill_ci95"]
            r["fill_calibrated"] = bool(lo <= r["p3_bracket_mean"][1] and hi >= r["p3_bracket_mean"][0])
        res[regime] = r
    res["resolution"] = {
        "Ha_ready": res["calm"]["n_orders"] >= 30 and sum(o["pair"] == "LINKUSD" for o in orders if o.get("regime") == "calm") >= 10,
        "Hb_ready": res["volatile"]["n_orders"] >= 10}
    return res


def main():
    res = evaluate(live_orders(), p3_rows())
    json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
