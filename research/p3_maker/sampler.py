"""P3 sampler: virtual post-only orders at the touch, observed against Kraken PUBLIC trades and ticker.

No orders are placed and no credentials are used. Only public endpoints: Ticker, Trades, OHLC.
Single instance (flock). Writes append-only JSONL to research/p3_maker/raw/ (gitignored):
  ticks.jsonl   {ts, pair, bid, ask}                      one per pair per cycle
  trades.jsonl  {pair, price, vol, ts, side, type}        every public trade since start
  orders.jsonl  {id, pair, t0, bid, ask, regime, vol_ratio, seed}   virtual bid AND ask at the touch
  log.jsonl     errors and lifecycle

Run: python3 research/p3_maker/sampler.py --hours 3.5   (background; a routine restarts it each session)
"""
import fcntl
import json
import os
import statistics
import sys
import time

import numpy as np
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
API = "https://api.kraken.com/0/public/"
MEAN_GAP_S = 600          # Poisson placement, mean 10 min per pair
PAUSE_S = 1.1             # between public calls (rate limit courtesy)
CALM_VOL_RATIO = 1.5      # scripts/execution_stats.py definition


def pairs():
    p = json.load(open(os.path.join(HERE, "pairs.json")))
    return [x for q in sorted(p["by_quintile"]) for x in p["by_quintile"][q]] + [p["anchor"]]


def quintile_of():
    p = json.load(open(os.path.join(HERE, "pairs.json")))
    out = {x: int(q) for q, xs in p["by_quintile"].items() for x in xs}
    out[p["anchor"]] = 0
    return out


def append(name, row):
    with open(os.path.join(RAW, name), "a") as f:
        f.write(json.dumps(row) + "\n")


def get(ep, **params):
    r = requests.get(API + ep, params=params, timeout=20)
    r.raise_for_status()
    d = r.json()
    if d.get("error"):
        raise RuntimeError(str(d["error"]))
    return d["result"]


def regime(pair):
    """execution_stats.vol_regime: |last daily return| / pstdev(last 30 daily returns)."""
    d = get("OHLC", pair=pair, interval=1440)
    k = next(x for x in d if x != "last")
    c = [float(r[4]) for r in d[k]]
    rets = [c[i] / c[i - 1] - 1 for i in range(1, len(c))]
    v30 = statistics.pstdev(rets[-30:])
    ratio = abs(rets[-1]) / v30 if v30 else 0.0
    return ("volatile" if ratio >= CALM_VOL_RATIO else "calm"), round(ratio, 3)


def main(hours):
    os.makedirs(RAW, exist_ok=True)
    lock = open(os.path.join(RAW, ".lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("sampler already running")
        return
    ps = pairs()
    seed = int(time.time())
    rng = np.random.default_rng(seed)
    append("log.jsonl", {"ts": time.time(), "event": "start", "seed": seed, "pairs": ps, "hours": hours})
    since = {p: str(time.time_ns()) for p in ps}
    next_place = {p: time.time() + rng.exponential(MEAN_GAP_S) for p in ps}
    ap = get("AssetPairs", pair=",".join(ps))
    key_to_pair = {k: v["altname"] for k, v in ap.items()}
    append("log.jsonl", {"ts": time.time(), "event": "keymap", "map": key_to_pair})
    reg_cache, end = {}, time.time() + hours * 3600
    while time.time() < end:
        try:
            tk = get("Ticker", pair=",".join(ps))
            now = time.time()
            quotes = {key_to_pair.get(k, k): (float(v["b"][0]), float(v["a"][0])) for k, v in tk.items()}
            for p in ps:
                if p not in quotes:
                    continue
                b, a = quotes[p]
                append("ticks.jsonl", {"ts": now, "pair": p, "bid": b, "ask": a})
                if now >= next_place[p]:
                    if p not in reg_cache or now - reg_cache[p][2] > 3600:
                        reg_cache[p] = (*regime(p), now)
                        time.sleep(PAUSE_S)
                    append("orders.jsonl", {"id": f"{p}-{int(now * 1000)}", "pair": p, "t0": now, "bid": b, "ask": a,
                                            "regime": reg_cache[p][0], "vol_ratio": reg_cache[p][1],
                                            "quintile": quintile_of()[p], "seed": seed})
                    next_place[p] = now + rng.exponential(MEAN_GAP_S)
            time.sleep(PAUSE_S)
            for p in ps:
                d = get("Trades", pair=p, since=since[p])
                since[p] = d["last"]
                k = next(x for x in d if x != "last")
                for t in d[k]:
                    append("trades.jsonl", {"pair": p, "price": float(t[0]), "vol": float(t[1]), "ts": float(t[2]),
                                            "side": t[3], "type": t[4]})
                time.sleep(PAUSE_S)
        except Exception as e:  # logged, never swallowed silently (D6)
            append("log.jsonl", {"ts": time.time(), "event": "error", "error": repr(e)[:300]})
            time.sleep(5)
    append("log.jsonl", {"ts": time.time(), "event": "stop"})


if __name__ == "__main__":
    main(float(sys.argv[sys.argv.index("--hours") + 1]) if "--hours" in sys.argv else 3.5)
