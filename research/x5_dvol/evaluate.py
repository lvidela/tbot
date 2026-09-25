"""X5: Deribit DVOL / variance risk premium as a state variable (see PREREGISTRATION.md).

  python3 research/x5_dvol/evaluate.py --fetch                download DVOL (public, unauthenticated)
  python3 research/x5_dvol/evaluate.py --stage discovery      -> results/discovery.json
  python3 research/x5_dvol/evaluate.py --stage holdout        -> results/holdout.json (after discovery committed)
"""
import datetime as dt
import importlib.util
import json
import os
import sys
import time

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RES = os.path.join(HERE, "results")
CB = os.path.join(HERE, "..", "data", "raw")
DAY = 86400
H = 28 * DAY
LEG = 0.0046
ALPHA = 0.05 / 4
HOLD_START = 1704067200          # 2024-01-01
END = 1790208000                 # 2026-09-24 00:00 (open time of last bar used)


def fetch():
    import requests
    os.makedirs(DATA, exist_ok=True)
    for cur in ("BTC", "ETH"):
        url = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
        rows, end = {}, int(time.time() * 1000)
        while True:
            r = requests.get(url, params={"currency": cur, "start_timestamp": 1546300800000, "end_timestamp": end,
                                          "resolution": "1D"}, timeout=30).json()["result"]
            for t, o, h, l, c in r["data"]:
                rows[int(t) // 1000] = [int(t) // 1000, o, h, l, c]
            if not r.get("continuation") or not r["data"]:
                break
            end = int(r["continuation"])
            time.sleep(0.3)
        out = {"meta": {"source": "deribit public get_volatility_index_data", "currency": cur, "resolution": "1D",
                        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(), "n": len(rows),
                        "first_ts": min(rows), "last_ts": max(rows)},
               "rows": [rows[k] for k in sorted(rows)]}
        json.dump(out, open(os.path.join(DATA, f"dvol_{cur}.json"), "w"))
        print(cur, out["meta"])


def closes(name):
    return {int(r[0]): float(r[4]) for r in json.load(open(os.path.join(CB, name)))["rows"]}


def load_ew():
    """EW-universe forward 28d simple return at t, from X1's survivorship-free panel (if present)."""
    p = os.path.join(HERE, "..", "x1_funding", "evaluate.py")
    spec = importlib.util.spec_from_file_location("x1e", p)
    x1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(x1)
    try:
        P = x1.Panel()
    except FileNotFoundError:
        return None

    def ew(t):
        mon = x1.ts(2020, 1, 6) + ((t - x1.ts(2020, 1, 6)) // x1.WEEK) * x1.WEEK
        r = [P.fwd(a, t, H) for a in P.universe(mon)]
        r = [x for x in r if x is not None]
        return float(np.mean(np.expm1(r))) if len(r) >= 10 else None
    return ew


class Data:
    def __init__(self):
        self.dvol = {int(r[0]): float(r[4]) for r in json.load(open(os.path.join(DATA, "dvol_BTC.json")))["rows"]}
        self.btc, self.link = closes("coinbase_BTC_1d.json"), closes("coinbase_LINK_1d.json")
        self._vrp = {}

    def close(self, s, t):
        return s.get(t - DAY)            # close(t) = close of the bar opened at t - 1d

    def raw_state(self, t):
        dv = self.dvol.get(t - DAY)      # DVOL point stamped at t-1d open (lagged one day, see prereg)
        cl = [self.close(self.btc, t - k * DAY) for k in range(30, -1, -1)]
        if dv is None or any(c is None for c in cl):
            return None
        rv = float(np.std(np.diff(np.log(cl)), ddof=1) * np.sqrt(365))
        return dv / 100 - rv, dv / 100

    def z(self, t, which=0):
        """Expanding z-score over daily values strictly before t (>= 180 days)."""
        hist = [s[which] for d in range(int(min(self.dvol)) + 31 * DAY, t, DAY) if (s := self.raw_state(d)) is not None]
        cur = self.raw_state(t)
        if cur is None or len(hist) < 180:
            return None
        return (cur[which] - np.mean(hist)) / np.std(hist, ddof=1)

    def fwd(self, s, t):
        c0, c1 = self.close(s, t), self.close(s, t + H)
        return float(np.log(c1 / c0)) if c0 and c1 else None


def grid(D, phase=0):
    t = min(D.dvol) + 211 * DAY
    t = t - (t % DAY) + phase * 7 * DAY
    out = []
    while t + H - DAY <= END:
        out.append(t)
        t += H
    return out


def slope(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    res = stats.linregress(x, y)
    return {"n": len(x), "slope": float(res.slope), "se": float(res.stderr), "t": float(res.slope / res.stderr),
            "p_two_sided": float(res.pvalue), "mde": 2.8 * float(res.stderr)}


def block_ci(x, block=3, n=4000, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x)
    nb = int(np.ceil(len(x) / block))
    m = []
    for _ in range(n):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.integers(0, len(x) - block + 1, nb)])[: len(x)]
        m.append(x[idx].mean())
    return [float(np.percentile(m, 5)), float(np.percentile(m, 95))]


def evaluate(D, ew, lo, hi, phase=0, one_sided=False, econ=True):
    ts = [t for t in grid(D, phase) if lo <= t <= hi]
    rows = []
    for t in ts:
        zv, zd = D.z(t, 0), D.z(t, 1)
        lf, bf = D.fwd(D.link, t), D.fwd(D.btc, t)
        if zv is None or lf is None or bf is None:
            continue
        rows.append({"t": t, "z_vrp": zv, "z_dvol": zd, "link": lf, "btc": bf, "ew": ew(t) if ew else None})
    zv = [r["z_vrp"] for r in rows]
    res = {"P_link_on_vrp": slope(zv, [r["link"] for r in rows]),
           "S1_btc_on_vrp": slope(zv, [r["btc"] for r in rows]),
           "S3_link_on_dvol": slope([r["z_dvol"] for r in rows], [r["link"] for r in rows])}
    ewr = [(r["z_vrp"], r["ew"]) for r in rows if r["ew"] is not None]
    res["S2_ew_on_vrp"] = slope(*zip(*ewr)) if len(ewr) >= 5 else {"n": len(ewr)}
    for k, v in res.items():
        if "t" in v:
            v["bonferroni_pass_pos"] = bool(v["slope"] > 0 and v["p_two_sided"] < ALPHA)
            if one_sided:
                v["p_one_sided_pos"] = float(stats.t.sf(v["t"], v["n"] - 2))
    if econ:
        link = np.expm1([r["link"] for r in rows])
        on = np.array([r["z_vrp"] >= 0 for r in rows])
        timing, prev = [], 0.0
        for o, rl in zip(on, link):
            w = 1.0 if o else 0.0
            cost = LEG * abs(w - prev)
            timing.append(w * rl - cost)
            prev = w * (1 + rl) / (1 + w * rl) if w else 0.0
        e = float(on.mean())
        static, prev = [], e
        for rl in link:
            cost = LEG * abs(e - prev)
            static.append(e * rl - cost)
            prev = e * (1 + rl) / (1 + e * rl)
        timing, static = np.array(timing), np.array(static)
        res["econ"] = {"n": len(rows), "exposure": e, "W_timing": float(np.prod(1 + timing)),
                       "W_static": float(np.prod(1 + static)), "W_hold_LINK": float(np.prod(1 + link)), "W_hold_USD": 1.0,
                       "timing_minus_static_mean": float((timing - static).mean()),
                       "timing_minus_static_ci90": block_ci(timing - static),
                       "timing_minus_hold_mean": float((timing - link).mean()),
                       "timing_minus_hold_ci90": block_ci(timing - link),
                       "static_minus_hold_mean": float((static - link).mean())}
    res["rows"] = rows
    return res


def main(stage):
    os.makedirs(RES, exist_ok=True)
    D, ew = Data(), load_ew()
    first = grid(D)[0]
    lo, hi = (first, HOLD_START - DAY) if stage == "discovery" else (HOLD_START, END)
    if stage == "holdout":
        assert os.path.exists(os.path.join(RES, "discovery.json"))
    res = {"meta": {"stage": stage, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "dvol_first": min(D.dvol), "dvol_last": max(D.dvol)},
           "primary": evaluate(D, ew, lo, hi, 0, stage == "holdout"),
           "phases": {f"phase{p}": {k: v.get("slope") for k, v in evaluate(D, ew, lo, hi, p, econ=False).items()
                                    if isinstance(v, dict)} for p in (1, 2, 3)}}
    json.dump(res, open(os.path.join(RES, f"{stage}.json"), "w"), indent=1)
    p = res["primary"]
    for k in ("P_link_on_vrp", "S1_btc_on_vrp", "S2_ew_on_vrp", "S3_link_on_dvol"):
        print(f"{k:18s} " + ", ".join(f"{a}={b:.4f}" if isinstance(b, float) else f"{a}={b}" for a, b in p[k].items()))
    print("phases:", res["phases"])
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in p["econ"].items()})


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch()
    else:
        main(sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "discovery")
