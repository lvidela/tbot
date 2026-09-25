"""Download public, unauthenticated daily market data for pre-registration T1.

Every download is cached as raw JSON under research/data/raw/ with a provenance header
(source, url template, fetched_at UTC, row count, first/last timestamp). Nothing here uses
credentials or private endpoints. If a host is denied by the environment's network policy the
failure is recorded in research/data/raw/_fetch_log.jsonl and the run continues; do not route
around a denial.

Run: python3 research/timing/fetch.py            (all series)
     python3 research/timing/fetch.py --probe    (one request per host, reports reachability)
"""
import datetime as dt
import json
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.environ.get("T1_RAW_DIR") or os.path.join(ROOT, "data", "raw")
START = dt.datetime(2019, 1, 1, tzinfo=dt.timezone.utc)
UA = {"User-Agent": "tbot-research/1.0 (public market data)"}

SPOT = {  # series -> {source: symbol}
    "LINK": {"coinbase": "LINK-USD", "binance": "LINKUSDT", "kraken": "LINKUSD"},
    "BTC": {"coinbase": "BTC-USD", "binance": "BTCUSDT", "kraken": "XBTUSD"},
    "ETH": {"coinbase": "ETH-USD", "binance": "ETHUSDT", "kraken": "ETHUSD"},
    "SOL": {"coinbase": "SOL-USD", "binance": "SOLUSDT", "kraken": "SOLUSD"},
}
FUNDING = {"binance": "LINKUSDT", "okx": "LINK-USDT-SWAP"}


def _now():
    return dt.datetime.now(dt.timezone.utc)


def _request(url, params=None, timeout=30, tries=5):
    """GET with exponential backoff on connection/SSL errors and 5xx/429 (transient drops seen
    on data.binance.vision). 4xx other than 429 is returned to the caller unchanged."""
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code != 429 and r.status_code < 500:
                return r
        except (requests.ConnectionError, requests.Timeout):
            if i == tries - 1:
                raise
        time.sleep(2 ** i)
    r.raise_for_status()
    return r


def _get(url, params=None):
    r = _request(url, params)
    r.raise_for_status()
    return r.json()


def _log(entry):
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, "_fetch_log.jsonl"), "a") as f:
        f.write(json.dumps(entry) + "\n")


def coinbase_daily(product):
    """Rows [t_open_s, open, high, low, close, volume], ascending. Max 300 candles per call."""
    url = f"https://api.exchange.coinbase.com/products/{product}/candles"
    rows, t0, end = {}, START, _now()
    while t0 < end:
        t1 = min(t0 + dt.timedelta(days=299), end)
        data = _get(url, {"granularity": 86400, "start": t0.isoformat(), "end": t1.isoformat()})
        for t, lo, hi, op, cl, vol in data:
            rows[int(t)] = [int(t), float(op), float(hi), float(lo), float(cl), float(vol)]
        t0 = t1
        time.sleep(0.35)  # public rate limit
    return url, [rows[k] for k in sorted(rows)]


ARCHIVE = "https://data.binance.vision/data"


def _months(start):
    y, m = start.year, start.month
    now = _now()
    while (y, m) < (now.year, now.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def _archive_csv(url):
    """Rows of the single CSV inside a data.binance.vision zip, or None if the file is absent."""
    import csv, io, zipfile
    r = _request(url, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        return list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))


def _ts_s(x):
    """Archive timestamps are ms, and microseconds for spot files from 2025 on."""
    x = int(x)
    return x // 1_000_000 if x > 10 ** 14 else x // 1000


def binance_daily(symbol):
    """Binance spot 1d klines from the official archive (api.binance.com is geo-blocked, A6).
    Monthly files, plus daily files for the current month."""
    tmpl = f"{ARCHIVE}/spot/monthly/klines/{symbol}/1d/{symbol}-1d-{{y}}-{{m:02d}}.zip"
    rows = {}
    for y, m in _months(START):
        for k in _archive_csv(tmpl.format(y=y, m=m)) or []:
            if k and k[0].isdigit():
                t = _ts_s(k[0])
                rows[t] = [t, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])]
    now = _now()
    for d in range(1, now.day):
        url = (f"{ARCHIVE}/spot/daily/klines/{symbol}/1d/"
               f"{symbol}-1d-{now.year}-{now.month:02d}-{d:02d}.zip")
        for k in _archive_csv(url) or []:
            if k and k[0].isdigit():
                t = _ts_s(k[0])
                rows[t] = [t, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])]
    return tmpl, [rows[t] for t in sorted(rows)]


def kraken_daily(pair):
    """Kraken's public OHLC returns at most the last 720 bars: a recent-period cross-check only."""
    url = "https://api.kraken.com/0/public/OHLC"
    data = _get(url, {"pair": pair, "interval": 1440})
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    key = next(k for k in data["result"] if k != "last")
    rows = [[int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[6])]
            for r in data["result"][key]]
    return url, rows


def binance_funding(symbol):
    """Rows [funding_time_s, rate] from the official archive (fapi.binance.com geo-blocked, A6)."""
    tmpl = f"{ARCHIVE}/futures/um/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{{y}}-{{m:02d}}.zip"
    rows = {}
    for y, m in _months(START):
        for k in _archive_csv(tmpl.format(y=y, m=m)) or []:
            if k and k[0].isdigit():
                rows[_ts_s(k[0])] = float(k[-1])
    return tmpl, [[t, rows[t]] for t in sorted(rows)]


def okx_funding(inst):
    """OKX funding-rate-history: recent months only; cross-check for Binance funding (A6)."""
    url = "https://www.okx.com/api/v5/public/funding-rate-history"
    rows, after = {}, None
    while True:
        params = {"instId": inst, "limit": 100}
        if after:
            params["after"] = after
        data = _get(url, params).get("data", [])
        if not data:
            break
        for d in data:
            rows[int(d["fundingTime"]) // 1000] = float(d.get("realizedRate") or d["fundingRate"])
        after = min(int(d["fundingTime"]) for d in data)
        time.sleep(0.25)
    return url, [[k, rows[k]] for k in sorted(rows)]


def bybit_funding(symbol):
    url = "https://api.bybit.com/v5/market/funding/history"
    rows, end_ms = {}, int(_now().timestamp() * 1000)
    while True:
        data = _get(url, {"category": "linear", "symbol": symbol, "endTime": end_ms, "limit": 200})
        lst = data.get("result", {}).get("list", [])
        if not lst:
            break
        for d in lst:
            rows[int(d["fundingRateTimestamp"]) // 1000] = float(d["fundingRate"])
        oldest = min(int(d["fundingRateTimestamp"]) for d in lst)
        if oldest <= START.timestamp() * 1000 or len(lst) < 200:
            break
        end_ms = oldest - 1
        time.sleep(0.2)
    return url, [[k, rows[k]] for k in sorted(rows)]


def save(name, source, symbol, fn):
    os.makedirs(RAW, exist_ok=True)
    fetched_at = _now().isoformat()
    try:
        url, rows = fn(symbol)
    except Exception as e:  # recorded, never swallowed silently (registry D6)
        _log({"name": name, "source": source, "symbol": symbol, "fetched_at": fetched_at,
              "ok": False, "error": repr(e)[:300]})
        print(f"  FAIL {name:<22} {repr(e)[:120]}")
        return False
    meta = {"name": name, "source": source, "symbol": symbol, "url": url, "fetched_at": fetched_at,
            "n": len(rows), "first_ts": rows[0][0] if rows else None,
            "last_ts": rows[-1][0] if rows else None}
    with open(os.path.join(RAW, f"{name}.json"), "w") as f:
        json.dump({"meta": meta, "rows": rows}, f)
    _log({**meta, "ok": True})
    print(f"  ok   {name:<22} n={len(rows)}")
    return True


def fetch_all():
    fns = {"coinbase": coinbase_daily, "binance": binance_daily, "kraken": kraken_daily}
    for asset, srcs in SPOT.items():
        for source, sym in srcs.items():
            save(f"{source}_{asset}_1d", source, sym, fns[source])
    save("binance_LINK_funding", "binance", FUNDING["binance"], binance_funding)
    save("okx_LINK_funding", "okx", FUNDING["okx"], okx_funding)


PROBES = {
    "api.kraken.com": "https://api.kraken.com/0/public/Time",
    "api.exchange.coinbase.com": "https://api.exchange.coinbase.com/products/LINK-USD/ticker",
    "api.binance.com": "https://api.binance.com/api/v3/ping",
    "fapi.binance.com": "https://fapi.binance.com/fapi/v1/ping",
    "data.binance.vision": "https://data.binance.vision/?prefix=data/spot/",
    "www.okx.com": "https://www.okx.com/api/v5/public/time",
    "api.bybit.com": "https://api.bybit.com/v5/market/time",
    "www.deribit.com": "https://www.deribit.com/api/v2/public/get_time",
}


def probe():
    out = {}
    for host, url in PROBES.items():
        try:
            r = requests.get(url, headers=UA, timeout=15)
            out[host] = f"HTTP {r.status_code}"
        except Exception as e:
            out[host] = "proxy 403 (network policy)" if "403" in str(e) else repr(e)[:100]
        print(f"  {host:<28} {out[host]}")
    _log({"probe": out, "at": _now().isoformat()})
    return out


if __name__ == "__main__":
    probe() if "--probe" in sys.argv else fetch_all()
