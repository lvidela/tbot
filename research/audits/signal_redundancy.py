"""Audit measurement A1 -- are the tactical 'confluence' conditions independent?

OUTCOME-BLIND BY DESIGN. This script never computes a forward return. It measures only how
often the five conditions in scripts/tactical.py fire together, so it adds no new researcher
degree of freedom and cannot be used to select a strategy. Registry D4 argued analytically that
momentum / breakout / relative-strength are monotone functions of one recent price change; this
measures it on Kraken data.

Conditions replicated from scripts/tactical.py (thresholds imported, not re-typed):
  volatility_expansion  |trailing-24h return| / sd(30 completed daily returns) >= 1.5
  volume_confirmation   trailing-24h USD volume / mean daily USD volume (30d) >= 3.0
  momentum_continuation 4h return >= 2% and 12h return > 0
  breakout_confirmed    close >= 95% of 30-day close range, range >= 3% of price, 4h return > 0
  relative_strength     12h return - cross-sectional median 12h return >= 3%
Approximation: tactical.py uses Kraken's in-progress daily bar; here trailing 24h (6 x 4h bars)
is used so every 4h bar is evaluated point-in-time with no partial-bar ambiguity.

Usage:  python3 research/audits/signal_redundancy.py [--refetch]
Data snapshot is written to research/audits/data/ohlc_4h_1d.json so the result is reproducible.
"""
import json, math, os, statistics, sys, time, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
SNAP = os.path.join(HERE, "data", "ohlc_4h_1d.json")
OUT = os.path.join(HERE, "results", "signal_redundancy.json")

# thresholds: read from tactical.py source without importing it (it imports the private client)
_src = open(os.path.join(ROOT, "scripts", "tactical.py")).read()
def _const(name):
    for line in _src.splitlines():
        if line.startswith(name):
            return float(line.split("=")[1].split("#")[0])
    raise KeyError(name)
VOL_EXP, VOLU, MOM, REL = (_const("VOL_EXPANSION_MIN"), _const("VOLUME_MIN"),
                           _const("MOMENTUM_MIN"), _const("REL_STRENGTH_MIN"))
NAMES = ["volatility_expansion", "volume_confirmation", "momentum_continuation",
         "breakout_confirmed", "relative_strength"]


def fetch(pair, interval):
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}"
    for i in range(4):
        try:
            d = json.load(urllib.request.urlopen(url, timeout=20))
            if d["error"]:
                raise RuntimeError(d["error"])
            k = [x for x in d["result"] if x != "last"][0]
            return [[int(r[0]), float(r[4]), float(r[6]) * float(r[4])] for r in d["result"][k]]
        except Exception as e:
            time.sleep(2 ** i)
            err = e
    raise err


def load(refetch=False):
    if os.path.exists(SNAP) and not refetch:
        return json.load(open(SNAP))
    pairs = list(json.load(open(os.path.join(ROOT, "research", "tsmom", "ohlc_long.json"))))
    snap = dict(fetched_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                source="Kraken public OHLC, interval 240 and 1440; rows [ts, close, usd_volume]",
                pairs={})
    for p in pairs:
        snap["pairs"][p] = dict(h4=fetch(p, 240), d1=fetch(p, 1440))
        time.sleep(1.1)
    os.makedirs(os.path.dirname(SNAP), exist_ok=True)
    json.dump(snap, open(SNAP, "w"))
    return snap


def features(snap):
    """Point-in-time condition values for every (4h bar, pair). Returns dict ts -> pair -> feats."""
    out = {}
    for p, d in snap["pairs"].items():
        h4, d1 = d["h4"], d["d1"]
        dts = [r[0] for r in d1]
        for i in range(6, len(h4)):
            ts = h4[i][0] + 4 * 3600          # bar close time: information available at ts
            # completed daily bars strictly before the day containing ts
            done = [j for j in range(len(d1)) if dts[j] + 86400 <= ts]
            if len(done) < 32:
                continue
            j = done[-1]
            dc = [d1[k][1] for k in range(j - 30, j + 1)]
            drets = [dc[k] / dc[k - 1] - 1 for k in range(1, len(dc))]
            sd30 = statistics.pstdev(drets)
            c = h4[i][1]
            r24 = c / h4[i - 6][1] - 1
            r4 = c / h4[i - 1][1] - 1
            r12 = c / h4[i - 3][1] - 1
            v24 = sum(h4[k][2] for k in range(i - 5, i + 1))
            v30 = statistics.mean(d1[k][2] for k in range(j - 29, j + 1))
            w = dc[-30:] + [c]
            lo, hi = min(w), max(w)
            pos = (c - lo) / (hi - lo) if hi > lo else 0.5
            out.setdefault(ts, {})[p] = dict(
                vol_ratio=abs(r24) / sd30 if sd30 else 0.0, volume_ratio=v24 / v30 if v30 else 0.0,
                r4=r4, r12=r12, r24=r24, pos=pos, range_frac=(hi - lo) / c)
    return out


def conditions(feat):
    rows = []
    for ts, per in sorted(feat.items()):
        if len(per) < 10:
            continue
        med = statistics.median(f["r12"] for f in per.values())
        for p, f in per.items():
            rel = f["r12"] - med
            cond = [f["vol_ratio"] >= VOL_EXP, f["volume_ratio"] >= VOLU,
                    f["r4"] >= MOM and f["r12"] > 0,
                    f["pos"] >= 0.95 and f["range_frac"] >= 0.03 and f["r4"] > 0,
                    rel >= REL]
            cont = [f["vol_ratio"], math.log(max(f["volume_ratio"], 1e-6)), f["r4"], f["pos"], rel]
            rows.append(dict(ts=ts, pair=p, cond=[int(x) for x in cond], cont=cont, r24=f["r24"]))
    return rows


def rank(x):
    return np.argsort(np.argsort(x)).astype(float)


def meff(corr):
    """Nyholt (2004) effective number of independent tests: 1 + (M-1)(1 - var(eigenvalues)/M).
    (Li & Ji's variant returns M whenever every eigenvalue is < 2, so it cannot discriminate
    at M = 5.) A crude summary; the independence-null inflation below is the sharper measure."""
    ev = np.linalg.eigvalsh(corr)
    m = len(ev)
    return float(1 + (m - 1) * (1 - np.var(ev, ddof=1) / m))


def main():
    snap = load("--refetch" in sys.argv)
    rows = conditions(features(snap))
    C = np.array([r["cond"] for r in rows], dtype=float)
    X = np.array([r["cont"] for r in rows], dtype=float)
    n = len(rows)
    fire = C.mean(0)
    phi = np.corrcoef(C.T)
    Xr = np.column_stack([rank(X[:, k]) for k in range(X.shape[1])])
    spear = np.corrcoef(Xr.T)
    cond_p = {}
    for i in range(5):
        for j in range(5):
            if i != j and C[:, i].sum():
                cond_p[f"P({NAMES[j]}|{NAMES[i]})"] = round(float(C[C[:, i] == 1, j].mean()), 3)
    conf = C.sum(1)
    # independence null: expected P(confluence>=3) if conditions were independent at observed rates
    pmf = np.zeros(6); pmf[0] = 1.0
    for q in fire:
        pmf = np.convolve(pmf, [1 - q, q])[:6]
    obs3 = float((conf >= 3).mean())
    ind3 = float(pmf[3:].sum())
    # how much of the confluence count is one factor: trailing 24h return rank within timestamp
    r24 = np.array([r["r24"] for r in rows])
    sp_conf_r24 = float(np.corrcoef(rank(conf), rank(r24))[0, 1])
    hi = conf >= 3
    combos = {}
    for r, h in zip(rows, hi):
        if h:
            key = "+".join(NAMES[k] for k in range(5) if r["cond"][k])
            combos[key] = combos.get(key, 0) + 1
    res = dict(
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        data=dict(fetched_utc=snap["fetched_utc"], pairs=len(snap["pairs"]), pair_bars=n,
                  timestamps=len({r["ts"] for r in rows})),
        thresholds=dict(VOL_EXPANSION_MIN=VOL_EXP, VOLUME_MIN=VOLU, MOMENTUM_MIN=MOM,
                        REL_STRENGTH_MIN=REL),
        firing_rate=dict(zip(NAMES, [round(float(x), 4) for x in fire])),
        phi_binary=[[round(float(v), 3) for v in row] for row in phi],
        spearman_continuous=[[round(float(v), 3) for v in row] for row in spear],
        meff_binary=round(meff(np.nan_to_num(phi)), 2),
        meff_continuous=round(meff(spear), 2),
        conditional_probabilities=cond_p,
        confluence_ge3_observed=round(obs3, 5), confluence_ge3_if_independent=round(ind3, 5),
        confluence_ge3_inflation=round(obs3 / ind3, 1) if ind3 else None,
        spearman_confluence_vs_trailing24h_return=round(sp_conf_r24, 3),
        confluence_ge3_combinations=dict(sorted(combos.items(), key=lambda kv: -kv[1])),
        mean_r24_when_confluence_ge3=round(float(r24[hi].mean()), 4) if hi.any() else None,
        share_ge3_with_r24_positive=round(float((r24[hi] > 0).mean()), 3) if hi.any() else None)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
