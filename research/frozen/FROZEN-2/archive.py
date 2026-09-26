"""FROZEN-2 close archive (NOT frozen; data plumbing only). Appends Kraken PUBLIC daily closes for the frozen
universe to closes.jsonl (append-only, committed), so pairs that are later delisted keep their last traded
price and the evaluation is not survivorship-biased. Run once per research session:

  python3 research/frozen/FROZEN-2/archive.py
"""
import json
import os
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "closes.jsonl")
START = 1790380800 - 75 * 86400      # keep only bars from ~75 days before the freeze (vol60 lookback)


def last_ts():
    out = {}
    if os.path.exists(OUT):
        for line in open(OUT):
            if line.strip():
                r = json.loads(line)
                if r.get("t") is None:
                    continue
                out[r["pair"]] = max(out.get(r["pair"], 0), r["t"])
    return out


def main():
    pairs = json.load(open(os.path.join(HERE, "universe.json")))["pairs"]
    have = last_ts()
    new = 0
    with open(OUT, "a") as f:
        for p in pairs:
            try:
                r = requests.get("https://api.kraken.com/0/public/OHLC", params={"pair": p, "interval": 1440},
                                 timeout=30).json()
                if r.get("error"):
                    f.write(json.dumps({"pair": p, "t": None, "error": str(r["error"])[:200], "at": time.time()}) + "\n")
                    continue
                key = next(k for k in r["result"] if k != "last")
                for row in r["result"][key][:-1]:                   # complete bars only
                    t = int(row[0])
                    if t >= START and t > have.get(p, 0):
                        f.write(json.dumps({"pair": p, "t": t, "close": float(row[4]),
                                            "vol_usd": float(row[5]) * float(row[6])}) + "\n")
                        new += 1
            except Exception as e:  # logged, never swallowed
                f.write(json.dumps({"pair": p, "t": None, "error": repr(e)[:200], "at": time.time()}) + "\n")
            time.sleep(1.1)
    print("appended", new)


if __name__ == "__main__":
    main()
