"""X8: conditional short-horizon reversal after LINK hourly UP-spikes (2-leg exit and re-entry). See PREREGISTRATION.md.

  python3 research/x8_spike/evaluate.py --fetch                  Binance archive LINKUSDT 1h + Coinbase LINK-USD 1h
  python3 research/x8_spike/evaluate.py --stage discovery        -> results/discovery.json
  python3 research/x8_spike/evaluate.py --stage reused           -> results/reused.json (after discovery is committed)
"""
import csv
import datetime as dt
import io
import json
import os
import sys
import time
import zipfile

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
RES = os.path.join(HERE, "results")
HOUR = 3600
LEGS2 = 0.0092                     # 2 maker legs incl. adverse selection (A1)
KS, HS = (2.0, 3.0), (1, 4, 24)
PRIMARY = (2.0, 4)
SIG_WIN = 168                      # trailing hours for sigma, excluding the event hour


def ts(y, m, d):
    return int(dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp())


DISC = (ts(2019, 7, 1), ts(2023, 12, 31))
REUSED = (ts(2024, 1, 1), ts(2026, 6, 30))
POSTCUT = (ts(2026, 7, 1), ts(2026, 9, 24))


# ---------------------------------------------------------------- data
def fetch():
    import requests
    os.makedirs(RAW, exist_ok=True)
    rows = {}
    base = "https://data.binance.vision/data/spot"
    now = dt.datetime.now(dt.timezone.utc)
    y, m = 2019, 1
    while (y, m) < (now.year, now.month):
        r = requests.get(f"{base}/monthly/klines/LINKUSDT/1h/LINKUSDT-1h-{y}-{m:02d}.zip", timeout=60)
        if r.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                for k in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))):
                    if k and k[0].isdigit():
                        t = int(k[0]); t = t // 1_000_000 if t > 10 ** 14 else t // 1000
                        rows[t] = float(k[4])
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    for d in range(1, now.day):
        r = requests.get(f"{base}/daily/klines/LINKUSDT/1h/LINKUSDT-1h-{now.year}-{now.month:02d}-{d:02d}.zip", timeout=60)
        if r.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                for k in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))):
                    if k and k[0].isdigit():
                        t = int(k[0]); t = t // 1_000_000 if t > 10 ** 14 else t // 1000
                        rows[t] = float(k[4])
    json.dump({"meta": {"source": "binance archive spot klines LINKUSDT 1h", "fetched_at": now.isoformat(), "n": len(rows)},
               "rows": [[t, rows[t]] for t in sorted(rows)]}, open(os.path.join(RAW, "binance_LINK_1h.json"), "w"))
    cb, t0 = {}, dt.datetime(2019, 6, 20, tzinfo=dt.timezone.utc)
    url = "https://api.exchange.coinbase.com/products/LINK-USD/candles"
    while t0 < now:
        t1 = min(t0 + dt.timedelta(hours=299), now)
        for _ in range(5):
            try:
                r = requests.get(url, params={"granularity": 3600, "start": t0.isoformat(), "end": t1.isoformat()}, timeout=30)
                if r.status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(2)
        for t, lo, hi, op, cl, v in r.json():
            cb[int(t)] = float(cl)
        t0 = t1
        time.sleep(0.35)
    json.dump({"meta": {"source": "coinbase LINK-USD 1h candles", "fetched_at": now.isoformat(), "n": len(cb)},
               "rows": [[t, cb[t]] for t in sorted(cb)]}, open(os.path.join(RAW, "coinbase_LINK_1h.json"), "w"))
    print("binance", len(rows), "coinbase", len(cb))


def load(name):
    d = json.load(open(os.path.join(RAW, name)))["rows"]
    return {int(t): c for t, c in d}          # key = bar OPEN time; close of that bar is at key + 1h


# ---------------------------------------------------------------- events
def events(close, lo, hi, k, h):
    """UP events at hour boundary T (the close of the bar opened at T-1h). r = log close(T)/close(T-1h);
    sigma = sd of the SIG_WIN hourly returns ending at T-1h (event hour excluded). Non-overlapping: after an
    event the next may start only at T + h. Returns [(T, r_event, sigma, fwd_simple)]."""
    c = lambda T: close.get(T - HOUR)   # noqa: E731  close at boundary T
    out, T, busy_until = [], lo, lo
    while T <= hi:
        if T >= busy_until:
            c0, c1 = c(T - HOUR), c(T)
            hist = [c(T - HOUR - i * HOUR) for i in range(SIG_WIN + 1)]
            if c0 and c1 and all(x is not None for x in hist):
                sig = float(np.std(np.diff(np.log(hist[::-1])), ddof=1))
                r = float(np.log(c1 / c0))
                if sig > 0 and r >= k * sig:
                    cf = c(T + h * HOUR)
                    if cf is not None:
                        out.append((T, r, sig, cf / c1 - 1.0))
                        busy_until = T + h * HOUR
        T += HOUR
    return out


def uncond(close, lo, hi, h):
    """Unconditional -r over non-overlapping h-hour windows: the drift cost of being in USD at random times."""
    c = lambda T: close.get(T - HOUR)   # noqa: E731
    out, T = [], lo
    while T + h * HOUR <= hi:
        a, b = c(T), c(T + h * HOUR)
        if a and b:
            out.append(-(b / a - 1.0))
        T += h * HOUR
    return out


def summ(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 3:
        return {"n": n}
    m, se = float(x.mean()), float(x.std(ddof=1) / np.sqrt(n))
    t = m / se
    return {"n": n, "mean": m, "median": float(np.median(x)), "se": se, "t": t,
            "p_one_sided_pos": float(stats.t.sf(t, n - 1)), "p_two_sided": float(2 * stats.t.sf(abs(t), n - 1)),
            "mde": 2.8 * se, "hit_rate": float((x > 0).mean())}


def cell(close, lo, hi, k, h):
    ev = events(close, lo, hi, k, h)
    net = [-f - LEGS2 for *_, f in ev]
    gross = [-f for *_, f in ev]
    unc = uncond(close, lo, hi, h)
    years = (hi - lo) / (365.25 * 86400)
    s = summ(net)
    s["events_per_year"] = len(ev) / years
    s["gross_reversal"] = summ(gross)
    s["gross_minus_uncond"] = float(np.mean(gross) - np.mean(unc)) if ev and unc else None
    s["per_year_net"] = s.get("mean", 0) * s["events_per_year"] if "mean" in s else None
    return s, ev


def main(stage):
    os.makedirs(RES, exist_ok=True)
    bn, cb = load("binance_LINK_1h.json"), load("coinbase_LINK_1h.json")
    if stage == "discovery":
        lo, hi = DISC
    elif stage == "reused":
        assert os.path.exists(os.path.join(RES, "discovery.json")), "run discovery first"
        lo, hi = REUSED
    else:
        raise SystemExit("stage?")
    res = {"meta": {"stage": stage, "window": [lo, hi], "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "binance_hours": len(bn), "coinbase_hours": len(cb)}, "cells": {}, "coinbase": {}}
    for k in KS:
        for h in HS:
            s, ev = cell(bn, lo, hi, k, h)
            res["cells"][f"k{k}_h{h}"] = s
            res["coinbase"][f"k{k}_h{h}"] = cell(cb, lo, hi, k, h)[0]
    pk = f"k{PRIMARY[0]}_h{PRIMARY[1]}"
    res["primary"] = pk
    if stage == "reused":
        res["postcutoff_descriptive"] = {f"k{k}_h{h}": cell(bn, *POSTCUT, k, h)[0] for k in KS for h in HS}
    json.dump(res, open(os.path.join(RES, f"{stage}.json"), "w"), indent=1)
    for name, s in res["cells"].items():
        c = res["coinbase"][name]
        print(f"{name:8s} n={s['n']:4d} ev/yr={s['events_per_year']:.0f} net={s.get('mean', np.nan):+.4f} "
              f"t={s.get('t', np.nan):+.2f} p1={s.get('p_one_sided_pos', np.nan):.4f} mde={s.get('mde', np.nan):.4f} "
              f"gross={s['gross_reversal'].get('mean', np.nan):+.4f} g-unc={s['gross_minus_uncond'] or np.nan:+.4f} "
              f"| coinbase n={c['n']} net={c.get('mean', np.nan):+.4f} t={c.get('t', np.nan):+.2f}")


if __name__ == "__main__":
    fetch() if "--fetch" in sys.argv else main(sys.argv[sys.argv.index("--stage") + 1])
