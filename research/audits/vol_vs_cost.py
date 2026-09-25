"""Audit measurement A2 -- does execution cost scale with volatility on Kraken USD pairs?

OUTCOME-BLIND: no forward return is computed. For the high-volatility / memecoin question the
relevant structural quantity is cost relative to the size of a move. If a predictable component
were a fixed fraction of sigma, higher volatility helps only if cost rises more slowly than sigma.
This script measures that elasticity and the cost-to-sigma ratio by volatility quintile, for a
clip the size of the live account's tactical position (default $13).

Cost model (per leg): maker = 0.40% fee + measured 5.4 bps adverse selection (registry A1; NOT
measured in volatile regimes, so a floor, not an estimate); taker = 0.80% fee + half-spread +
book impact for the clip. Round trip = 2 legs.

Usage: python3 research/audits/vol_vs_cost.py [--refetch] [--min-usd-vol 250000] [--clip 13]
"""
import json, math, os, statistics, sys, time, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "data", "vol_cost_snapshot.json")
OUT = os.path.join(HERE, "results", "vol_vs_cost.json")
MAKER_FEE, TAKER_FEE, ADVERSE_BPS = 0.40, 0.80, 5.4
STABLES = {"USDT", "USDC", "DAI", "PYUSD", "RLUSD", "EURT", "USDG", "USDS", "TUSD", "EUR", "GBP",
           "PAXG", "XAUT", "USD1", "FDUSD", "USDE", "AUD", "CAD", "CHF", "JPY"}


def api(method, **q):
    url = f"https://api.kraken.com/0/public/{method}" + ("?" + "&".join(f"{k}={v}" for k, v in q.items()) if q else "")
    for i in range(4):
        try:
            d = json.load(urllib.request.urlopen(url, timeout=25))
            if d["error"]:
                raise RuntimeError(d["error"])
            return d["result"]
        except Exception as e:
            err = e
            time.sleep(2 ** i)
    raise err


def arg(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def snapshot(min_usd_vol):
    ap, tk = api("AssetPairs"), api("Ticker")
    rows = []
    for key, v in ap.items():
        if v.get("quote") != "ZUSD" or v.get("status") != "online" or key not in tk:
            continue
        base = v["base"].lstrip("X").lstrip("Z") if len(v["base"]) == 4 else v["base"]
        if base in STABLES or v["altname"].replace("USD", "") in STABLES:
            continue
        t = tk[key]
        bid, ask, vwap, vol = float(t["b"][0]), float(t["a"][0]), float(t["p"][1]), float(t["v"][1])
        if bid <= 0 or ask < bid or vol * vwap < min_usd_vol:
            continue
        rows.append(dict(pair=v["altname"], key=key, bid=bid, ask=ask, usd_vol_24h=vol * vwap,
                         trades_24h=int(t["t"][1])))
    for r in rows:
        d = api("OHLC", pair=r["key"], interval=1440)
        k = [x for x in d if x != "last"][0]
        c = [float(x[4]) for x in d[k]][:-1]            # drop the in-progress day
        rets = [math.log(c[i] / c[i - 1]) for i in range(1, len(c)) if c[i - 1] > 0 and c[i] > 0]
        r["sigma30_pct"] = statistics.pstdev(rets[-30:]) * 100 if len(rets) >= 30 else None
        r["n_days"] = len(c)
        dp = api("Depth", pair=r["key"], count=100)
        dk = list(dp)[0]
        r["asks"] = [[float(p), float(q)] for p, q, *_ in dp[dk]["asks"]]
        r["bids"] = [[float(p), float(q)] for p, q, *_ in dp[dk]["bids"]]
        time.sleep(1.0)
    return dict(fetched_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                min_usd_vol=min_usd_vol, rows=rows)


def impact_bps(levels, clip, side):
    """Average execution price vs touch for a market order of `clip` USD walking the book."""
    if not levels:
        return None
    touch, need, cost, qty = levels[0][0], clip, 0.0, 0.0
    for p, q in levels:
        take = min(q, need / p)
        cost += take * p; qty += take; need -= take * p
        if need <= 1e-9:
            break
    if need > 1e-9:
        return None
    avg = cost / qty
    return abs(avg / touch - 1) * 1e4


def main():
    min_vol, clip = arg("--min-usd-vol", 250000.0), arg("--clip", 13.0)
    if os.path.exists(SNAP) and "--refetch" not in sys.argv:
        snap = json.load(open(SNAP))
    else:
        snap = snapshot(min_vol)
        os.makedirs(os.path.dirname(SNAP), exist_ok=True)
        json.dump(snap, open(SNAP, "w"))
    rows = [r for r in snap["rows"] if r.get("sigma30_pct") and r["n_days"] >= 45]
    for r in rows:
        mid = (r["bid"] + r["ask"]) / 2
        r["spread_bps"] = (r["ask"] - r["bid"]) / mid * 1e4
        ib = impact_bps(r["asks"], clip, "buy")
        r["impact_bps"] = ib
        r["depth_05pct_usd"] = min(sum(p * q for p, q in r["asks"] if p <= mid * 1.005),
                                   sum(p * q for p, q in r["bids"] if p >= mid * 0.995))
        r["maker_rt_pct"] = 2 * (MAKER_FEE + ADVERSE_BPS / 100)
        r["taker_rt_pct"] = 2 * TAKER_FEE + r["spread_bps"] / 100 + 2 * (ib or 0) / 100
        r["spread_over_sigma"] = (r["spread_bps"] / 100) / r["sigma30_pct"]
        # predictable fraction of a 3-day sigma needed just to pay the round trip
        s3 = r["sigma30_pct"] * math.sqrt(3)
        r["breakeven_frac_3d_sigma_maker"] = r["maker_rt_pct"] / s3
        r["breakeven_frac_3d_sigma_taker"] = r["taker_rt_pct"] / s3
    rows.sort(key=lambda r: r["sigma30_pct"])
    ls, lsp = np.log([r["sigma30_pct"] for r in rows]), np.log([max(r["spread_bps"], 0.1) for r in rows])
    slope, icpt = np.polyfit(ls, lsp, 1)
    q = np.array_split(np.arange(len(rows)), 5)
    quint = []
    for i, idx in enumerate(q):
        g = [rows[j] for j in idx]
        med = lambda k: round(float(statistics.median(x[k] for x in g if x[k] is not None)), 4)
        quint.append(dict(quintile=i + 1, n=len(g), sigma30_pct=med("sigma30_pct"),
                          spread_bps=med("spread_bps"), impact_bps_clip=med("impact_bps"),
                          depth_05pct_usd=med("depth_05pct_usd"), usd_vol_24h=med("usd_vol_24h"),
                          taker_rt_pct=med("taker_rt_pct"), maker_rt_pct_floor=med("maker_rt_pct"),
                          breakeven_frac_3d_sigma_maker=med("breakeven_frac_3d_sigma_maker"),
                          breakeven_frac_3d_sigma_taker=med("breakeven_frac_3d_sigma_taker"),
                          examples=[x["pair"] for x in g[-4:]]))
    res = dict(generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               snapshot_utc=snap["fetched_utc"], n_pairs=len(rows), clip_usd=clip,
               min_usd_vol_24h=snap["min_usd_vol"],
               elasticity_log_spread_on_log_sigma=round(float(slope), 3),
               spearman_sigma_spread=round(float(np.corrcoef(np.argsort(np.argsort(ls)),
                                                             np.argsort(np.argsort(lsp)))[0, 1]), 3),
               by_volatility_quintile=quint,
               caveats=["single order-book snapshot; spreads vary intraday",
                        "maker cost is a FLOOR: adverse selection measured only in calm LINKUSD (n=2)",
                        "survivorship: only pairs listed and liquid today",
                        "no forward returns computed -- predictability is NOT measured here"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
