"""V2: cross-exchange check of F4's V1b nuisance parameters, and VOI rerun (PREREGISTRATION_V2.md).

  python3 research/voi/crosscheck.py --fetch   download Coinbase + Binance-archive daily bars for
                                               F4's 19-asset universe (public, unauthenticated)
  python3 research/voi/crosscheck.py           compute P1/P2/P3 and the rerun -> results/crosscheck_v2.json

voi_screen.py (F4's record) is imported, never edited.
"""
import datetime as dt
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "timing"))
import voi_screen as v  # noqa: E402

RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "results", "crosscheck_v2.json")

# F4 universe (Kraken names) -> base ticker used on Coinbase / Binance
KRAKEN = ['AAVEUSD', 'ADAUSD', 'ALGOUSD', 'ATOMUSD', 'AVAXUSD', 'BCHUSD', 'DOTUSD', 'ETCUSD',
          'ETHUSD', 'FILUSD', 'LINKUSD', 'LTCUSD', 'SOLUSD', 'TRXUSD', 'UNIUSD', 'XBTUSD',
          'XDGUSD', 'XLMUSD', 'XRPUSD', 'XTZUSD']
BASE = {k: {"XBTUSD": "BTC", "XDGUSD": "DOGE"}.get(k, k[:-3]) for k in KRAKEN}
VENUES = ("kraken", "coinbase", "binance")

DAY = 86400
F4_START = int(dt.datetime(2024, 10, 5, tzinfo=dt.timezone.utc).timestamp())
LONG_START = int(dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp())
END = int(dt.datetime(2026, 9, 24, tzinfo=dt.timezone.utc).timestamp())   # last bar used (open ts)
HORIZONS = {"H20": 20, "H365": 365, "H730": 730}


# ---------------------------------------------------------------- data
def fetch():
    import fetch as f  # research/timing/fetch.py
    for k in KRAKEN:
        b = BASE[k]
        if not os.path.exists(os.path.join(RAW, f"coinbase_{b}_1d.json")):
            f.save(f"coinbase_{b}_1d", "coinbase", f"{b}-USD", f.coinbase_daily)
        if not os.path.exists(os.path.join(RAW, f"binance_{b}_1d.json")):
            f.save(f"binance_{b}_1d", "binance", f"{b}USDT", f.binance_daily)


def load_venue(venue, raw=RAW, kraken_path=v.OHLC):
    """{base: {open_ts: close}} for one venue. Kraken comes from F4's file (partial last bar
    dropped, as in F4); others from research/data/raw. Missing files are simply absent."""
    out = {}
    if venue == "kraken":
        d = json.load(open(kraken_path))
        for k in KRAKEN:
            out[BASE[k]] = {int(r[0]): float(r[4]) for r in d[k]["1440"][:-1]}
        return out
    for k in KRAKEN:
        p = os.path.join(raw, f"{venue}_{BASE[k]}_1d.json")
        if os.path.exists(p):
            rows = json.load(open(p))["rows"]
            out[BASE[k]] = {int(r[0]): float(r[4]) for r in rows}
    return out


def align(series, start, end, assets):
    """Close matrix on the daily grid start..end (inclusive). Assets lacking any bar on the grid
    are dropped and reported -- no forward filling."""
    grid = np.arange(start, end + 1, DAY)
    kept, dropped, cols = [], [], []
    for a in assets:
        s = series.get(a)
        if s is None or any(t not in s for t in grid):
            dropped.append(a)
            continue
        kept.append(a)
        cols.append([s[t] for t in grid])
    return kept, dropped, np.array(cols, float), grid


def params(kept, closes, h=3):
    """Same estimator as voi_screen.ledger_params, on an aligned matrix (LINK must be kept)."""
    lp = np.log(closes)
    li = kept.index("LINK")
    oth = [i for i in range(len(kept)) if i != li]
    link_sd = float(np.std(np.diff(lp[li]), ddof=1))
    sig, rho = [], []
    for ph in range(h):
        idx = np.arange(ph, lp.shape[1], h)
        rl = np.diff(lp[li][idx])
        X = np.array([np.diff(lp[i][idx]) - rl for i in oth])
        sig.append(float(np.std(X, ddof=1)))
        c = np.corrcoef(X)
        rho.append(float(c[~np.eye(len(oth), dtype=bool)].mean()))
    return {"sigma_x": float(np.median(sig)), "rho": float(np.median(rho)), "link_daily_sd": link_sd,
            "n_assets": len(oth), "bars": int(lp.shape[1]),
            "per_phase_sigma": sig, "per_phase_rho": rho}


# ---------------------------------------------------------------- VOI rerun
def rerun(p, horizons=HORIZONS):
    """Every candidate at the given horizons, with nuisance parameters p (only C9 uses them)."""
    fns = dict(v.CANDIDATES)
    fns["C9 forward ledgers"] = lambda s, d: v.c9_ledgers(s, d, p)
    res = {}
    for name, fn in fns.items():
        res[name] = {}
        for hz, days in horizons.items():
            row = {s: dict(zip(("evpi", "evsi", "note"), fn(s, days))) for s in v.SCEN}
            row["label"] = v.label(row["central"]["evsi"])
            res[name][hz] = row
    return res


def timetable(p):
    out = {}
    for m in (1, 3, 10):
        out[f"m={m}"] = {"mde_at": {d: v.mde(d, p["sigma_x"], p["rho"], m) for d in (20, 60, 180, 365)},
                         **{f"days_to_mde_{t:.2%}": v.days_to(t, p["sigma_x"], p["rho"], m)
                            for t in (0.0183, 0.0283, 0.01, 0.005)}}
    return out


def main():
    data = {vn: load_venue(vn) for vn in VENUES}
    assets = [BASE[k] for k in KRAKEN]
    res = {"sources": {}, "P1": {}, "P2": {}, "P3": {}, "rerun": {}, "timetable": {}}
    for vn in ("coinbase", "binance"):
        res["sources"][vn] = {}
        for a in assets:
            p = os.path.join(RAW, f"{vn}_{a}_1d.json")
            if os.path.exists(p):
                m = json.load(open(p))["meta"]
                res["sources"][vn][a] = {k: m[k] for k in ("symbol", "url", "fetched_at", "n")}
    res["sources"]["kraken"] = {"file": "research/tsmom/ohlc_long.json", "key": "1440"}

    # P2: each venue's own full set, F4 window
    avail = {}
    for vn in VENUES:
        kept, dropped, C, _ = align(data[vn], F4_START, END, assets)
        avail[vn] = set(kept)
        res["P2"][vn] = {**params(kept, C), "assets": kept, "dropped": dropped}

    # P1: matched set, F4 window
    matched = [a for a in assets if all(a in avail[vn] for vn in VENUES)]
    for vn in VENUES:
        kept, dropped, C, _ = align(data[vn], F4_START, END, matched)
        assert kept == matched and not dropped
        res["P1"][vn] = params(kept, C)
    res["P1"]["matched_assets"] = matched
    k1 = res["P1"]["kraken"]
    for vn in ("coinbase", "binance"):
        q = res["P1"][vn]
        res["P1"][vn]["vs_kraken"] = {
            "sigma_rel": q["sigma_x"] / k1["sigma_x"] - 1, "rho_abs": q["rho"] - k1["rho"],
            "material": abs(q["sigma_x"] / k1["sigma_x"] - 1) > 0.20 or abs(q["rho"] - k1["rho"]) > 0.10}
    med = {"sigma_x": float(np.median([res["P1"][vn]["sigma_x"] for vn in VENUES])),
           "rho": float(np.median([res["P1"][vn]["rho"] for vn in VENUES]))}
    res["P1"]["median"] = med

    # P3: long window, Coinbase and Binance
    for vn in ("coinbase", "binance"):
        kept, dropped, C, _ = align(data[vn], LONG_START, END, assets)
        res["P3"][vn] = {**params(kept, C), "assets": kept, "dropped": dropped}

    sets = {"F4_kraken_full": {k: res["P2"]["kraken"][k] for k in ("sigma_x", "rho")}}
    for vn in VENUES:
        sets[f"P1_{vn}"] = {k: res["P1"][vn][k] for k in ("sigma_x", "rho")}
    sets["P1_median (decision)"] = med
    for vn in ("coinbase", "binance"):
        sets[f"P3_{vn}"] = {k: res["P3"][vn][k] for k in ("sigma_x", "rho")}
    for name, p in sets.items():
        res["rerun"][name] = rerun(p)
        res["timetable"][name] = timetable(p)

    dec = res["rerun"]["P1_median (decision)"]
    res["decision"] = {
        "meaningful_H365_median": [c for c, r in dec.items() if r["H365"]["central"]["evsi"] >= v.MEANINGFUL],
        "meaningful_any_set_or_H730": sorted({c for s in res["rerun"].values() for c, r in s.items()
                                              for hz in ("H365", "H730")
                                              if r[hz]["central"]["evsi"] >= v.MEANINGFUL})}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)
    report(res)
    return res


def report(res):
    print(f"P1 matched set ({len(res['P1']['matched_assets'])} assets): {res['P1']['matched_assets']}")
    for vn in VENUES:
        q = res["P1"][vn]
        extra = q.get("vs_kraken", {})
        print(f"  {vn:9s} sigma_x {q['sigma_x']:.4f}  rho {q['rho']:.3f}  LINK sd {q['link_daily_sd']:.4f}"
              f"  bars {q['bars']}  {extra and ('dsig %+.1f%% drho %+.3f material=%s' % (100*extra['sigma_rel'], extra['rho_abs'], extra['material']))}")
    print(f"  median    sigma_x {res['P1']['median']['sigma_x']:.4f}  rho {res['P1']['median']['rho']:.3f}")
    for tag in ("P2", "P3"):
        for vn, q in res[tag].items():
            print(f"{tag} {vn:9s} n={q['n_assets']:2d} sigma_x {q['sigma_x']:.4f} rho {q['rho']:.3f} "
                  f"LINK sd {q['link_daily_sd']:.4f} bars {q['bars']} dropped {q['dropped']}")
    print("\nC9 central EVSI (USD) by parameter set:")
    for name, r in res["rerun"].items():
        c = r["C9 forward ledgers"]
        print(f"  {name:22s} " + "  ".join(f"{hz} ${c[hz]['central']['evsi']:.3f} ({c[hz]['label']})"
                                            for hz in HORIZONS))
    print("\nAll candidates, decision set, central EVSI:")
    for cand, r in res["rerun"]["P1_median (decision)"].items():
        print(f"  {cand:34s} " + "  ".join(f"{hz} ${r[hz]['central']['evsi']:.3f} {r[hz]['label']:10s}"
                                           for hz in HORIZONS))
    print("\ndecision:", res["decision"])


if __name__ == "__main__":
    fetch() if "--fetch" in sys.argv else main()
