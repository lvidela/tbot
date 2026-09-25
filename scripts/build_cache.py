"""Build a local OHLC cache so research agents can work in parallel without
hammering Kraken's rate limit, and so every result is reproducible from fixed data.
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache")

def build():
    u = json.load(open(os.path.join(ROOT, "data", "universe.json")))
    pairs = [(c["pair"], c["key"], c["is_stable"], c["spread_bps"], c["min_notional"])
             for c in u["eligible"]]
    meta = {}
    for interval, name in ((1440, "1d"), (240, "4h"), (60, "1h")):
        out = {}
        for pair, key, *_ in pairs:
            try:
                d = kraken.public("OHLC", pair=pair, interval=interval)
                k = [x for x in d if x != "last"][0]
                # time, open, high, low, close, vwap, volume, count
                out[pair] = [[int(r[0])] + [float(x) for x in r[1:7]] + [int(r[7])] for r in d[k]]
                time.sleep(0.12)
            except Exception as e:
                print("  skip", pair, name, e)
        json.dump(out, open(os.path.join(CACHE, f"ohlc_{name}.json"), "w"))
        print(f"{name}: {len(out)} pairs, {sum(len(v) for v in out.values())} bars")
    meta = {p: dict(key=k, is_stable=s, spread_bps=sp, min_notional=mn)
            for p, k, s, sp, mn in pairs}
    json.dump(meta, open(os.path.join(CACHE, "meta.json"), "w"), indent=2)
    json.dump(dict(built=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), n_pairs=len(pairs)),
              open(os.path.join(CACHE, "manifest.json"), "w"), indent=2)
    print("cache built:", CACHE)

if __name__ == "__main__":
    build()
