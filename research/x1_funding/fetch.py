"""X1 data: Binance archive USDT-perp funding + spot 1d klines, incl. delisted symbols.

Public, unauthenticated. Enumerates via the archive's public S3 listing (same bucket as
data.binance.vision; the geo-blocked api.binance.com is never used -- A6).
Output (outside git, see .gitignore): research/x1_funding/raw/{funding,spot}/<SYM>.json
with a provenance header. Every failure is logged to raw/_fetch_log.jsonl.

Run: python3 research/x1_funding/fetch.py [--limit N]
"""
import csv
import datetime as dt
import io
import json
import os
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
FILES = "https://data.binance.vision"
UA = {"User-Agent": "tbot-research/1.0 (public market data)"}
STABLE = {"USDC", "FDUSD", "TUSD", "BUSD", "DAI", "USDP", "EUR", "PAXG", "XAUT", "USDE", "AEUR",
          "EURI", "USD1", "RLUSD", "BFUSD", "PYUSD", "USDS", "GBP", "TRY", "BRL"}
SESSION = requests.Session()
SESSION.headers.update(UA)


def now():
    return dt.datetime.now(dt.timezone.utc)


def log(e):
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, "_fetch_log.jsonl"), "a") as f:
        f.write(json.dumps(e) + "\n")


def get(url, tries=5, timeout=60):
    for i in range(tries):
        try:
            r = SESSION.get(url, timeout=timeout)
            if r.status_code == 404:
                return None
            if r.status_code < 500 and r.status_code != 429:
                r.raise_for_status()
                return r
        except (requests.ConnectionError, requests.Timeout):
            if i == tries - 1:
                raise
        time.sleep(2 ** i)
    raise RuntimeError(f"gave up {url}")


def s3_list(prefix, delimiter=True):
    """All keys (or common prefixes) under prefix, following pagination."""
    out, marker = [], ""
    while True:
        url = f"{S3}?prefix={prefix}" + ("&delimiter=/" if delimiter else "") + (f"&marker={marker}" if marker else "")
        t = get(url).text
        tag = "Prefix" if delimiter else "Key"
        if delimiter:
            items = re.findall(r"<CommonPrefixes><Prefix>([^<]+)</Prefix>", t)
        else:
            items = re.findall(r"<Key>([^<]+)</Key>", t)
        out += items
        if "<IsTruncated>true</IsTruncated>" not in t or not items:
            return out
        marker = items[-1]


def csv_rows(url):
    r = get(url)
    if r is None:
        return None
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        return list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))


def ts_s(x):
    x = int(x)
    return x // 1_000_000 if x > 10 ** 14 else x // 1000


def spot_base(perp):
    base = perp[:-4]
    for p in ("1000000", "1000", "1M"):
        if base.startswith(p) and len(base) > len(p):
            return base[len(p):]
    return base


def fetch_funding(sym):
    keys = [k for k in s3_list(f"data/futures/um/monthly/fundingRate/{sym}/", delimiter=False)
            if k.endswith(".zip")]
    rows = {}
    for k in keys:
        for r in csv_rows(f"{FILES}/{k}") or []:
            if r and r[0].isdigit():
                rows[ts_s(r[0])] = float(r[-1])
    return {"meta": {"symbol": sym, "source": "binance-archive futures/um fundingRate", "files": len(keys),
                     "fetched_at": now().isoformat(), "n": len(rows)},
            "rows": [[t, rows[t]] for t in sorted(rows)]}


def fetch_spot(pair):
    keys = [k for k in s3_list(f"data/spot/monthly/klines/{pair}/1d/", delimiter=False) if k.endswith(".zip")]
    dkeys = [k for k in s3_list(f"data/spot/daily/klines/{pair}/1d/", delimiter=False)
             if k.endswith(".zip") and k[-14:-7] >= now().strftime("%Y-%m")[:7]]
    rows = {}
    for k in keys + dkeys:
        for r in csv_rows(f"{FILES}/{k}") or []:
            if r and r[0].isdigit():
                t = ts_s(r[0])
                # [open_ts, open, high, low, close, volume, quote_volume]
                rows[t] = [t, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), float(r[7])]
    return {"meta": {"symbol": pair, "source": "binance-archive spot klines 1d", "files": len(keys) + len(dkeys),
                     "fetched_at": now().isoformat(), "n": len(rows)},
            "rows": [rows[t] for t in sorted(rows)]}


def save(kind, name, fn, arg):
    path = os.path.join(RAW, kind, f"{name}.json")
    if os.path.exists(path):
        return "cached"
    try:
        d = fn(arg)
    except Exception as e:  # logged, never swallowed (D6)
        log({"kind": kind, "name": name, "ok": False, "error": repr(e)[:300], "at": now().isoformat()})
        return "fail"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(d, f)
    log({"kind": kind, "name": name, "ok": True, **d["meta"]})
    return "ok"


def main(limit=None):
    perps = [p.rstrip("/").split("/")[-1] for p in s3_list("data/futures/um/monthly/fundingRate/")]
    perps = [p for p in perps if p.endswith("USDT")]
    spots = {p.rstrip("/").split("/")[-1] for p in s3_list("data/spot/monthly/klines/")}
    plan, excluded = [], {"no_spot": [], "stable": []}
    for p in sorted(perps):
        b = spot_base(p)
        if b in STABLE:
            excluded["stable"].append(p)
        elif f"{b}USDT" not in spots:
            excluded["no_spot"].append(p)
        else:
            plan.append((p, f"{b}USDT"))
    if limit:
        plan = plan[:limit]
    os.makedirs(RAW, exist_ok=True)
    json.dump({"at": now().isoformat(), "perps": len(perps), "planned": plan, "excluded": excluded},
              open(os.path.join(RAW, "_universe_plan.json"), "w"), indent=0)
    print(f"perps {len(perps)}, planned {len(plan)}, no spot {len(excluded['no_spot'])}, stable {len(excluded['stable'])}")
    jobs = [("funding", p, fetch_funding, p) for p, _ in plan] + \
           [("spot", s, fetch_spot, s) for s in sorted({s for _, s in plan})]
    stats = {}
    with ThreadPoolExecutor(16) as ex:
        for i, res in enumerate(ex.map(lambda j: save(*j), jobs)):
            stats[res] = stats.get(res, 0) + 1
            if i % 100 == 0:
                print(i, len(jobs), stats, flush=True)
    print("done", stats)


if __name__ == "__main__":
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    main(lim)
