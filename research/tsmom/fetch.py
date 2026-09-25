"""Fetch long-history weekly (10080) and daily (1440) OHLC from Kraken's public API.

Read-only, no credentials. Kraken returns at most 720 bars per interval, so weekly bars
reach back ~13.8 years (to each pair's listing) while daily bars cover only ~2 years.
Output: research/tsmom/ohlc_long.json  {pair: {"10080": [[t,o,h,l,c,vol],...], "1440": ...}}
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import kraken  # noqa: E402

PAIRS = sys.argv[1:] or [
    "LINKUSD", "XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD", "DOTUSD", "LTCUSD",
    "XLMUSD", "ATOMUSD", "AAVEUSD", "UNIUSD", "XDGUSD", "AVAXUSD", "BCHUSD", "ETCUSD",
    "XTZUSD", "ALGOUSD", "FILUSD", "TRXUSD",
]

out = {}
for p in PAIRS:
    for iv in (10080, 1440):
        try:
            r = kraken.public("OHLC", pair=p, interval=iv)
        except Exception as e:  # report, never swallow silently
            print(p, iv, "ERROR", e)
            continue
        k = [x for x in r if x != "last"][0]
        out.setdefault(p, {})[str(iv)] = [
            [int(b[0]), float(b[1]), float(b[2]), float(b[3]), float(b[4]), float(b[6])] for b in r[k]
        ]
        time.sleep(1.1)
    w = out.get(p, {}).get("10080", [])
    if w:
        print(p, len(w), "weekly from", time.strftime("%Y-%m-%d", time.gmtime(w[0][0])),
              len(out[p].get("1440", [])), "daily")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ohlc_long.json"), "w") as fh:
    json.dump(out, fh)
