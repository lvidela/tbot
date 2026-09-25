"""Q2 -- Is the production expected-move model in scripts/tactical.py calibrated?

Audits two production formulas:
    expected_move_pct   = 0.5 * daily_sigma * (1 + 0.15 * max(0, confluence - 3))
    success_probability = min(0.50 + 0.03 * confluence, 0.62)

Method (deliberately conservative, mirroring the fixes that killed R1/R2):
  * Confluence conditions are reconstructed EXACTLY as tactical.analyse() defines them,
    evaluated at a daily bar close (00:00 UTC) so that every input is information that
    existed at decision time. No look-ahead.
  * Forward returns are cross-sectionally demeaned (same-day equal-weight universe mean)
    so we measure selection skill, not market beta.
  * Every t-statistic is cluster-robust by DATE. 32 correlated assets firing on the same
    day are not 32 independent observations.
  * Overlapping forward windows (a 3d window on consecutive dates shares 2 days) are
    additionally handled with a moving-block bootstrap over dates.
  * Everything is reported gross AND net of the measured 1.83% round-trip cost (A1).

Data: local cache only (/home/lisandro/data/cache). No API calls, no orders.

HARD SAMPLE LIMIT: the 4h cache starts 2026-05-27, so mom_4h / mom_12h / relative_strength
-- three of the five confluence conditions -- can only be reconstructed over ~115 days.
The primary study therefore has at most ~112 distinct dates. A PROXY study over the full
721-day daily history is run separately and is explicitly NOT the production definition.
"""
import json, os, math, random, statistics as st
from collections import defaultdict

CACHE = "/home/lisandro/data/cache"
COST_RT = 1.83          # A1: 4 legs at maker pricing, incl. spread + adverse selection
EXCLUDED = {"EURUSD", "GBPUSD", "PAXGUSD"}

# --- production thresholds, copied from scripts/tactical.py ------------------------
VOL_EXPANSION_MIN = 1.5
VOLUME_MIN        = 3.0
MOMENTUM_MIN      = 0.02
REL_STRENGTH_MIN  = 0.03
MAX_SPREAD_BPS    = 25
MIN_CONFLUENCE    = 3

DAY = 86400
H4  = 14400


def predicted_move(sigma_pct, confluence):
    return 0.5 * sigma_pct * (1.0 + 0.15 * max(0, confluence - MIN_CONFLUENCE))


def predicted_p(confluence):
    return min(0.50 + 0.03 * confluence, 0.62)


# ================================ statistics ======================================

def clustered_mean(x, groups):
    """Mean with a date-cluster-robust SE. Returns (mean, se, t, n, n_groups)."""
    n = len(x)
    if n == 0:
        return (float("nan"),) * 3 + (0, 0)
    m = sum(x) / n
    g = defaultdict(float)
    for xi, gi in zip(x, groups):
        g[gi] += xi - m
    G = len(g)
    if G < 2:
        return m, float("nan"), float("nan"), n, G
    S = sum(v * v for v in g.values()) * G / (G - 1)
    se = math.sqrt(S) / n
    return m, se, (m / se if se > 0 else float("nan")), n, G


def ols_origin(y, x, groups):
    """Fit y = k*x through the origin. Cluster-robust SE by date. Returns dict."""
    sxx = sum(xi * xi for xi in x)
    if sxx == 0:
        return None
    k = sum(xi * yi for xi, yi in zip(x, y)) / sxx
    g = defaultdict(float)
    for xi, yi, gi in zip(x, y, groups):
        g[gi] += xi * (yi - k * xi)
    G = len(g)
    if G < 2:
        return None
    meat = sum(v * v for v in g.values()) * G / (G - 1)
    se = math.sqrt(meat) / sxx
    return dict(k=k, se=se, lo=k - 1.96 * se, hi=k + 1.96 * se,
                n=len(y), n_days=G, t=(k / se if se > 0 else float("nan")))


def block_bootstrap_k(y, x, dates, block=4, iters=2000, seed=7):
    """Moving-block bootstrap over ordered dates -> CI robust to overlapping windows."""
    rnd = random.Random(seed)
    byd = defaultdict(list)
    for yi, xi, d in zip(y, x, dates):
        byd[d].append((yi, xi))
    order = sorted(byd)
    D = len(order)
    if D < block * 3:
        return None
    nblocks = max(1, D // block)
    out = []
    for _ in range(iters):
        sxx = sxy = 0.0
        for _b in range(nblocks):
            s = rnd.randrange(0, D - block + 1)
            for d in order[s:s + block]:
                for yi, xi in byd[d]:
                    sxx += xi * xi
                    sxy += xi * yi
        if sxx > 0:
            out.append(sxy / sxx)
    if len(out) < 100:
        return None
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))]


def block_bootstrap_mean(x, dates, block=4, iters=2000, seed=11):
    rnd = random.Random(seed)
    byd = defaultdict(list)
    for xi, d in zip(x, dates):
        byd[d].append(xi)
    order = sorted(byd)
    D = len(order)
    if D < block * 3:
        return None
    nblocks = max(1, D // block)
    out = []
    for _ in range(iters):
        acc, cnt = 0.0, 0
        for _b in range(nblocks):
            s = rnd.randrange(0, D - block + 1)
            for d in order[s:s + block]:
                for xi in byd[d]:
                    acc += xi
                    cnt += 1
        if cnt:
            out.append(acc / cnt)
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))]


def clustered_prop(flags, groups):
    """Proportion of True with cluster-robust SE (flags as 0/1)."""
    x = [1.0 if f else 0.0 for f in flags]
    m, se, t, n, G = clustered_mean(x, groups)
    return dict(p=m, se=se, lo=max(0.0, m - 1.96 * se), hi=min(1.0, m + 1.96 * se),
                n=n, n_days=G)


# ================================ data loading ====================================

def load():
    meta = json.load(open(os.path.join(CACHE, "meta.json")))
    d1 = json.load(open(os.path.join(CACHE, "ohlc_1d.json")))
    d4 = json.load(open(os.path.join(CACHE, "ohlc_4h.json")))
    pairs = sorted(p for p, v in meta.items()
                   if not v["is_stable"] and p not in EXCLUDED and p in d1 and p in d4)
    D1, D4 = {}, {}
    for p in pairs:
        rows = sorted(d1[p], key=lambda r: r[0])
        # drop the final daily bar: it is the in-progress day at cache-build time
        rows = rows[:-1]
        D1[p] = {int(r[0]): dict(o=float(r[1]), h=float(r[2]), l=float(r[3]),
                                 c=float(r[4]), v=float(r[6])) for r in rows}
        D4[p] = {int(r[0]): dict(h=float(r[2]), l=float(r[3]), c=float(r[4])) for r in d4[p]}
    return meta, pairs, D1, D4


# ================================ feature build ===================================

def build_events(meta, pairs, D1, D4, mode="exact"):
    """Reconstruct tactical.analyse() at each daily close.

    mode='exact'  -> mom_4h / mom_12h from the 4h cache (production definition).
    mode='proxy'  -> mom_4h ~ day D return, mom_12h ~ 3-day return. NOT production;
                     used only as a longer-history robustness check.
    """
    all_ts = sorted({t for p in pairs for t in D1[p]})
    feats = defaultdict(dict)          # ts -> pair -> feature dict

    for p in pairs:
        ts = sorted(D1[p])
        c = [D1[p][t]["c"] for t in ts]
        vusd = [D1[p][t]["v"] * D1[p][t]["c"] for t in ts]
        rets = [c[i] / c[i - 1] - 1 for i in range(1, len(c))]
        spread_ok = meta[p]["spread_bps"] <= MAX_SPREAD_BPS
        for i in range(len(ts)):
            if i < 40:                                    # tactical: len(closes) >= 40
                continue
            T = ts[i] + DAY                               # decision instant
            r30 = rets[i - 30:i]                          # returns of days D-29..D
            if len(r30) < 30:
                continue
            v30 = st.pstdev(r30)
            if v30 <= 0:
                continue
            vol_ratio = abs(rets[i - 1]) / v30            # rets[i-1] is day D's return
            vol30_usd = st.mean(vusd[i - 29:i + 1])       # includes day D, as in tactical
            volume_ratio = vusd[i] / vol30_usd if vol30_usd else 0.0

            if mode == "exact":
                b1, b2, b4 = T - H4, T - 2 * H4, T - 4 * H4
                if not (b1 in D4[p] and b2 in D4[p] and b4 in D4[p]):
                    continue
                mom_4h = D4[p][b1]["c"] / D4[p][b2]["c"] - 1
                mom_12h = D4[p][b1]["c"] / D4[p][b4]["c"] - 1
            else:
                if i < 43:
                    continue
                mom_4h = rets[i - 1]
                mom_12h = c[i] / c[i - 3] - 1

            w = c[i - 29:i + 1]                           # last 30 closes incl. day D
            rng = max(w) - min(w)
            bid = c[i]                                    # close stands in for the bid
            pos = (bid - min(w)) / rng if rng > 0 else 0.5

            feats[ts[i]][p] = dict(
                pair=p, ts=ts[i], i=i, close=bid, sigma=v30 * 100.0,
                vol_ratio=vol_ratio, volume_ratio=volume_ratio,
                mom_4h=mom_4h, mom_12h=mom_12h, pos=pos, rng_rel=rng / bid,
                spread_ok=spread_ok)

    # relative strength needs the same-day universe median 12h momentum
    events = []
    for t, per in feats.items():
        med = st.median([f["mom_12h"] for f in per.values()])
        for f in per.values():
            rel = f["mom_12h"] - med
            cond = dict(
                volatility_expansion=f["vol_ratio"] >= VOL_EXPANSION_MIN,
                volume_confirmation=f["volume_ratio"] >= VOLUME_MIN,
                momentum_continuation=(f["mom_4h"] >= MOMENTUM_MIN and f["mom_12h"] > 0),
                breakout_confirmed=(f["pos"] >= 0.95 and f["rng_rel"] >= 0.03 and f["mom_4h"] > 0),
                relative_strength=rel >= REL_STRENGTH_MIN,
            )
            f["rel"] = rel
            f["cond"] = cond
            f["confluence"] = sum(1 for v in cond.values() if v)
            events.append(f)
    return feats, events, all_ts


def attach_forward(feats, events, D1, horizons=(1, 2, 3), D4=None):
    """Forward close-to-close returns, MFE/MAE from daily high/low, time-to-peak (4h)."""
    by_pair_ts = {}
    for p in D1:
        by_pair_ts[p] = sorted(D1[p])

    # same-day universe mean forward return, over the WHOLE eligible universe
    mkt = {h: {} for h in horizons}
    for t, per in feats.items():
        for h in horizons:
            rs = []
            for f in per.values():
                r = _fwd(D1, by_pair_ts, f, h)
                if r is not None:
                    rs.append(r)
            if len(rs) >= 5:
                mkt[h][t] = st.mean(rs)

    out = []
    for f in events:
        ok = True
        for h in horizons:
            r = _fwd(D1, by_pair_ts, f, h)
            if r is None or f["ts"] not in mkt[h]:
                ok = False
                break
            f[f"r{h}"] = r
            f[f"x{h}"] = r - mkt[h][f["ts"]]
            mfe, mae = _excursion(D1, by_pair_ts, f, h)
            f[f"mfe{h}"], f[f"mae{h}"] = mfe, mae
        if not ok:
            continue
        f["ttp_h"] = _time_to_peak(D4, f, 3) if D4 else None
        out.append(f)
    return out


def _fwd(D1, tsmap, f, h):
    ts = tsmap[f["pair"]]
    i = f["i"]
    if i + h >= len(ts):
        return None
    return (D1[f["pair"]][ts[i + h]]["c"] / f["close"] - 1) * 100.0


def _excursion(D1, tsmap, f, h):
    ts = tsmap[f["pair"]]
    i = f["i"]
    if i + h >= len(ts):
        return None, None
    hi = max(D1[f["pair"]][ts[j]]["h"] for j in range(i + 1, i + h + 1))
    lo = min(D1[f["pair"]][ts[j]]["l"] for j in range(i + 1, i + h + 1))
    return (hi / f["close"] - 1) * 100.0, (lo / f["close"] - 1) * 100.0


def _time_to_peak(D4, f, days):
    """Hours from decision instant to the highest 4h high within the window."""
    T = f["ts"] + DAY
    best, best_t = None, None
    for j in range(days * 6):
        b = T + j * H4
        row = D4[f["pair"]].get(b)
        if row is None:
            continue
        if best is None or row["h"] > best:
            best, best_t = row["h"], (j + 1) * 4
    return best_t


# ================================ reporting =======================================

def pct(x):
    return "   n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:+.2f}%"


def section(title):
    print("\n" + "=" * 92)
    print(title)
    print("=" * 92)


def describe_sample(ev, label):
    days = sorted({e["ts"] for e in ev})
    print(f"{label}: n_events={len(ev)}  n_days={len(days)}  "
          f"pairs={len({e['pair'] for e in ev})}")
    if days:
        import datetime as dt
        f = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")
        print(f"    date range {f(days[0])} .. {f(days[-1])}")


def lowconf(n_days):
    return "  *** LOW CONFIDENCE (<30 clustered obs) ***" if n_days < 30 else ""


def run(mode="exact"):
    meta, pairs, D1, D4 = load()
    feats, events, all_ts = build_events(meta, pairs, D1, D4, mode=mode)
    ev = attach_forward(feats, events, D1, D4=D4 if mode == "exact" else None)

    section(f"MODE = {mode.upper()}   universe = {len(pairs)} non-stable pairs, spread veto <= {MAX_SPREAD_BPS}bps")
    describe_sample(ev, "all reconstructed observations")

    # condition firing rates
    print("\ncondition firing rates over all observations:")
    for cname in ("volatility_expansion", "volume_confirmation", "momentum_continuation",
                  "breakout_confirmed", "relative_strength"):
        n = sum(1 for e in ev if e["cond"][cname])
        print(f"   {cname:<24}{n:>7} / {len(ev)}  ({n/max(1,len(ev)):.2%})")
    dist = defaultdict(int)
    for e in ev:
        dist[e["confluence"]] += 1
    print("confluence distribution:", dict(sorted(dist.items())))

    setups = [e for e in ev if e["confluence"] >= MIN_CONFLUENCE and e["spread_ok"]]
    describe_sample(setups, "\nSETUPS (confluence>=3, spread ok)")
    if not setups:
        print("no setups -- nothing to calibrate")
        return None, None

    for e in setups:
        e["pred"] = predicted_move(e["sigma"], e["confluence"])

    # ---------------- realized vs predicted -------------------------------------
    section("1. PREDICTED vs REALIZED (gross, and net of %.2f%% round trip)" % COST_RT)
    print(f"{'horizon':<9}{'n':>6}{'days':>6}{'pred':>9}{'real':>9}{'t_cl':>8}"
          f"{'demeaned':>10}{'t_cl':>8}{'median':>9}{'net_real':>10}{'net_dmn':>9}")
    for h in (1, 2, 3):
        dates = [e["ts"] for e in setups]
        raw = [e[f"r{h}"] for e in setups]
        dmn = [e[f"x{h}"] for e in setups]
        mr, _, tr, n, G = clustered_mean(raw, dates)
        md, _, td, _, _ = clustered_mean(dmn, dates)
        pr = st.mean(e["pred"] for e in setups)
        print(f"{h}d{'':<7}{n:>6}{G:>6}{pr:>8.2f}%{mr:>+8.2f}%{tr:>+8.2f}"
              f"{md:>+9.2f}%{td:>+8.2f}{st.median(raw):>+8.2f}%"
              f"{mr-COST_RT:>+9.2f}%{md-COST_RT:>+8.2f}%")

    print("\nMFE / MAE profile (daily high/low, entry at decision close):")
    print(f"{'horizon':<9}{'mean_MFE':>10}{'med_MFE':>10}{'mean_MAE':>10}{'med_MAE':>10}"
          f"{'MFE/MAE':>9}{'MFE/pred':>10}{'P(MFE>pred)':>13}")
    for h in (1, 2, 3):
        mfe = [e[f"mfe{h}"] for e in setups]
        mae = [e[f"mae{h}"] for e in setups]
        pr = [e["pred"] for e in setups]
        hit = sum(1 for a, b in zip(mfe, pr) if a >= b) / len(mfe)
        print(f"{h}d{'':<7}{st.mean(mfe):>+9.2f}%{st.median(mfe):>+9.2f}%"
              f"{st.mean(mae):>+9.2f}%{st.median(mae):>+9.2f}%"
              f"{abs(st.mean(mfe)/st.mean(mae)):>9.2f}"
              f"{st.mean(mfe)/st.mean(pr):>10.2f}{hit:>12.1%}")

    ttp = [e["ttp_h"] for e in setups if e.get("ttp_h")]
    if ttp:
        print(f"\ntime-to-peak over 3d window (4h resolution): median {st.median(ttp):.0f}h, "
              f"mean {st.mean(ttp):.0f}h, "
              f"share peaking in first 24h {sum(1 for t in ttp if t <= 24)/len(ttp):.1%}")

    # ---------------- calibration table -----------------------------------------
    section("2. CALIBRATION TABLE -- when the model predicts X%, what happens?")
    print("buckets on predicted_move_pct; realized = 3d close-to-close (gross)")
    print(f"{'pred bucket':<14}{'n':>5}{'days':>6}{'mean_pred':>11}{'mean_real':>11}"
          f"{'P(>pred)':>10}{'P(>3%)':>9}{'P(>1%)':>9}{'P(<0)':>8}{'P(MFE>pred)':>13}")
    edges = [(0, 2), (2, 3), (3, 4), (4, 6), (6, 100)]
    for lo, hi in edges:
        b = [e for e in setups if lo <= e["pred"] < hi]
        if not b:
            continue
        nd = len({e["ts"] for e in b})
        r = [e["r3"] for e in b]
        print(f"{f'{lo}-{hi}%':<14}{len(b):>5}{nd:>6}{st.mean(e['pred'] for e in b):>10.2f}%"
              f"{st.mean(r):>10.2f}%"
              f"{sum(1 for e in b if e['r3'] > e['pred'])/len(b):>9.1%}"
              f"{sum(1 for x in r if x > 3)/len(b):>8.1%}"
              f"{sum(1 for x in r if x > 1)/len(b):>8.1%}"
              f"{sum(1 for x in r if x < 0)/len(b):>7.1%}"
              f"{sum(1 for e in b if e['mfe3'] > e['pred'])/len(b):>12.1%}"
              f"{lowconf(nd)}")

    print("\nsame table on DEMEANED 3d returns (selection skill, market removed):")
    print(f"{'pred bucket':<14}{'n':>5}{'days':>6}{'mean_pred':>11}{'mean_dmn':>11}"
          f"{'P(>pred)':>10}{'P(>3%)':>9}{'P(>1%)':>9}{'P(<0)':>8}")
    for lo, hi in edges:
        b = [e for e in setups if lo <= e["pred"] < hi]
        if not b:
            continue
        nd = len({e["ts"] for e in b})
        x = [e["x3"] for e in b]
        print(f"{f'{lo}-{hi}%':<14}{len(b):>5}{nd:>6}{st.mean(e['pred'] for e in b):>10.2f}%"
              f"{st.mean(x):>10.2f}%"
              f"{sum(1 for e in b if e['x3'] > e['pred'])/len(b):>9.1%}"
              f"{sum(1 for v in x if v > 3)/len(b):>8.1%}"
              f"{sum(1 for v in x if v > 1)/len(b):>8.1%}"
              f"{sum(1 for v in x if v < 0)/len(b):>7.1%}{lowconf(nd)}")

    # ---------------- sigma multiplier fit ---------------------------------------
    section("3. FITTED SIGMA MULTIPLIER  (target = k * sigma, through origin, cluster-robust)")
    print("production uses k = 0.50 (before the confluence uplift)")
    print(f"{'target':<26}{'k_hat':>8}{'se':>7}{'95% CI (cluster)':>22}{'95% CI (block boot)':>24}{'n':>6}{'days':>6}")
    dates = [e["ts"] for e in setups]
    sig = [e["sigma"] for e in setups]
    targets = [
        ("3d return (raw)",        [e["r3"] for e in setups]),
        ("3d return (demeaned)",   [e["x3"] for e in setups]),
        ("3d |return| (raw)",      [abs(e["r3"]) for e in setups]),
        ("3d MFE (raw)",           [e["mfe3"] for e in setups]),
        ("3d |MAE| (raw)",         [abs(e["mae3"]) for e in setups]),
        ("1d return (raw)",        [e["r1"] for e in setups]),
        ("1d MFE (raw)",           [e["mfe1"] for e in setups]),
    ]
    fits = {}
    for name, y in targets:
        f = ols_origin(y, sig, dates)
        if not f:
            continue
        bb = block_bootstrap_k(y, sig, dates)
        bbs = f"[{bb[0]:+.3f}, {bb[1]:+.3f}]" if bb else "n/a"
        ci = "[%+.3f, %+.3f]" % (f["lo"], f["hi"])
        print(f"{name:<26}{f['k']:>+8.3f}{f['se']:>7.3f}{ci:>22}"
              f"{bbs:>24}{f['n']:>6}{f['n_days']:>6}")
        fits[name] = (f, bb)

    print("\nk by confluence level (target = 3d MFE, the most charitable reading):")
    print(f"{'conf':<6}{'n':>6}{'days':>6}{'k_MFE':>9}{'k_ret':>9}{'k_ret_dmn':>11}{'model k':>9}")
    for cf in (3, 4, 5):
        b = [e for e in setups if e["confluence"] == cf]
        if len(b) < 5:
            continue
        nd = len({e["ts"] for e in b})
        d2 = [e["ts"] for e in b]
        s2 = [e["sigma"] for e in b]
        km = ols_origin([e["mfe3"] for e in b], s2, d2)
        kr = ols_origin([e["r3"] for e in b], s2, d2)
        kx = ols_origin([e["x3"] for e in b], s2, d2)
        mk = 0.5 * (1 + 0.15 * max(0, cf - 3))
        print(f"{cf:<6}{len(b):>6}{nd:>6}{km['k']:>+9.3f}{kr['k']:>+9.3f}{kx['k']:>+11.3f}"
              f"{mk:>9.3f}{lowconf(nd)}")

    # ---------------- success probability ----------------------------------------
    section("4. SUCCESS-PROBABILITY ANCHOR  p = min(0.50 + 0.03*confluence, 0.62)")
    print(f"{'conf':<6}{'n':>6}{'days':>6}{'model_p':>9}{'P(r3>0)':>10}{'95% CI':>18}"
          f"{'P(x3>0)':>10}{'P(r3>cost)':>12}{'P(x3>cost)':>12}")
    for cf in (3, 4, 5):
        b = [e for e in setups if e["confluence"] == cf]
        if not b:
            continue
        nd = len({e["ts"] for e in b})
        d2 = [e["ts"] for e in b]
        pr = clustered_prop([e["r3"] > 0 for e in b], d2)
        px = clustered_prop([e["x3"] > 0 for e in b], d2)
        pc = clustered_prop([e["r3"] > COST_RT for e in b], d2)
        pxc = clustered_prop([e["x3"] > COST_RT for e in b], d2)
        ci = "[%.3f, %.3f]" % (pr["lo"], pr["hi"])
        print(f"{cf:<6}{len(b):>6}{nd:>6}{predicted_p(cf):>9.3f}{pr['p']:>10.3f}{ci:>18}"
              f"{px['p']:>10.3f}{pc['p']:>12.3f}{pxc['p']:>12.3f}{lowconf(nd)}")
    allb = setups
    d2 = [e["ts"] for e in allb]
    pr = clustered_prop([e["r3"] > 0 for e in allb], d2)
    px = clustered_prop([e["x3"] > 0 for e in allb], d2)
    ci = "[%.3f, %.3f]" % (pr["lo"], pr["hi"])
    print(f"{'all':<6}{len(allb):>6}{len(set(d2)):>6}{'--':>9}{pr['p']:>10.3f}{ci:>18}"
          f"{px['p']:>10.3f}")

    # baseline: what does an unconditional observation do?
    base = [e for e in ev]
    db = [e["ts"] for e in base]
    pb = clustered_prop([e["r3"] > 0 for e in base], db)
    pbx = clustered_prop([e["x3"] > 0 for e in base], db)
    mb, _, tb, nb, Gb = clustered_mean([e["x3"] for e in base], db)
    print(f"\nUNCONDITIONAL baseline (every pair, every day): n={nb} days={Gb} "
          f"P(r3>0)={pb['p']:.3f} P(x3>0)={pbx['p']:.3f} mean demeaned 3d={mb:+.3f}% t={tb:+.2f}")

    # ---------------- net EV of the production rule -------------------------------
    section("5. NET EV OF ACTUALLY TAKING THESE SETUPS")
    for h in (1, 2, 3):
        raw = [e[f"r{h}"] - COST_RT for e in setups]
        dmn = [e[f"x{h}"] - COST_RT for e in setups]
        m1, _, t1, n, G = clustered_mean(raw, dates)
        m2, _, t2, _, _ = clustered_mean(dmn, dates)
        bb = block_bootstrap_mean(raw, dates)
        bbs = f"[{bb[0]:+.2f}%, {bb[1]:+.2f}%]" if bb else "n/a"
        print(f"{h}d hold: net raw {m1:+.2f}% (t={t1:+.2f}, boot CI {bbs}) | "
              f"net demeaned {m2:+.2f}% (t={t2:+.2f}) | median net {st.median(raw):+.2f}% | "
              f"P(profit) {sum(1 for x in raw if x>0)/len(raw):.1%}")

    # a trailing/target exit is the model's implied plan: exit at +pred, stop at -1 sigma
    print("\nimplied production exit plan (target = predicted move, stop = -1 sigma, 3d window,"
          "\ndaily high/low, pessimistic: if both touched in the same day, assume the stop):")
    wins = losses = timeout = 0
    pnl = []
    for e in setups:
        tgt, stop = e["pred"], -e["sigma"]
        res = None
        for h in (1, 2, 3):
            if e[f"mae{h}"] <= stop:
                res = stop
                break
            if e[f"mfe{h}"] >= tgt:
                res = tgt
                break
        if res is None:
            res = e["r3"]
            timeout += 1
        elif res == tgt:
            wins += 1
        else:
            losses += 1
        pnl.append(res - COST_RT)
    m, _, t, n, G = clustered_mean(pnl, dates)
    print(f"   target hit {wins}  stop hit {losses}  timeout {timeout}  (n={n}, days={G})")
    print(f"   mean net P&L/trade {m:+.2f}%  t_cl={t:+.2f}  median {st.median(pnl):+.2f}%  "
          f"P(profit) {sum(1 for x in pnl if x>0)/len(pnl):.1%}")

    if mode == "exact":
        section("6. EXIT PATH ON 4h BARS (finer ordering) + PRODUCTION GATE PASS-RATE")
        for tie in ("pessimistic", "optimistic"):
            w = l = to = 0
            pnl2 = []
            for e in setups:
                tgt, stop = e["pred"], -e["sigma"]
                T = e["ts"] + DAY
                res = None
                for j in range(18):                      # 3 days of 4h bars
                    row = D4[e["pair"]].get(T + j * H4)
                    if row is None:
                        continue
                    up = (row["h"] / e["close"] - 1) * 100 >= tgt
                    dn = (row["l"] / e["close"] - 1) * 100 <= stop
                    if up and dn:
                        res = stop if tie == "pessimistic" else tgt
                    elif up:
                        res = tgt
                    elif dn:
                        res = stop
                    if res is not None:
                        break
                if res is None:
                    res, to = e["r3"], to + 1
                elif res == tgt:
                    w += 1
                else:
                    l += 1
                pnl2.append(res - COST_RT)
            m2, _, t2, n2, G2 = clustered_mean(pnl2, dates)
            ph = w / len(setups)
            print(f"   [{tie:<11}] target-before-stop {w} ({ph:.1%})  stop {l}  timeout {to}  "
                  f"| mean net {m2:+.2f}%  t_cl={t2:+.2f}  median {st.median(pnl2):+.2f}%  "
                  f"P(profit) {sum(1 for x in pnl2 if x > 0)/len(pnl2):.1%}")
        print("   (the model's success_probability is the analogue of target-before-stop)")

        print("\n   production EV gate: expected_move >= %.1fx all-in cost (%.2f%%) "
              "=> needs predicted move >= %.2f%%" % (3.0, COST_RT, 3.0 * COST_RT))
        g = [e for e in setups if e["pred"] >= 3.0 * COST_RT]
        print(f"   setups clearing the gate: {len(g)} / {len(setups)} "
              f"({len(g)/len(setups):.1%}) on {len({e['ts'] for e in g})} distinct days")
        if g:
            gr = [e["r3"] for e in g]
            print("   their realized 3d: mean %+.2f%%  median %+.2f%%  net mean %+.2f%%  "
                  "(n=%d -- far too few to evaluate)"
                  % (st.mean(gr), st.median(gr), st.mean(gr) - COST_RT, len(g)))

    section("7. TARGET / STOP GEOMETRY SWEEP  (net of %.2f%%; DESCRIPTIVE -- a grid on %d\n"
            "   events / %d days will overfit. Read the shape, not the best cell.)"
            % (COST_RT, len(setups), len({e["ts"] for e in setups})))
    use4h = (mode == "exact")
    print("   exit path on " + ("4h bars" if use4h else "daily bars (pessimistic ties)"))
    print(f"   {'tgt_x_sigma':>12}{'stop_x_sigma':>14}{'P(target)':>11}{'mean_net':>10}"
          f"{'t_cl':>8}{'median':>9}{'P(profit)':>11}")
    for tm in (0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
        for sm in (0.75, 1.0, 1.5):
            pnl3, w = [], 0
            for e in setups:
                tgt, stop = tm * e["sigma"], -sm * e["sigma"]
                res = None
                if use4h:
                    T = e["ts"] + DAY
                    for j in range(18):
                        row = D4[e["pair"]].get(T + j * H4)
                        if row is None:
                            continue
                        up = (row["h"] / e["close"] - 1) * 100 >= tgt
                        dn = (row["l"] / e["close"] - 1) * 100 <= stop
                        res = (stop if dn else tgt) if (up or dn) else None
                        if res is not None:
                            break
                else:
                    for h in (1, 2, 3):
                        if e[f"mae{h}"] <= stop:
                            res = stop
                            break
                        if e[f"mfe{h}"] >= tgt:
                            res = tgt
                            break
                if res is None:
                    res = e["r3"]
                elif res == tgt:
                    w += 1
                pnl3.append(res - COST_RT)
            m3, _, t3, _, _ = clustered_mean(pnl3, dates)
            print(f"   {tm:>12.2f}{sm:>14.2f}{w/len(setups):>10.1%}{m3:>+9.2f}%{t3:>+8.2f}"
                  f"{st.median(pnl3):>+8.2f}%{sum(1 for x in pnl3 if x>0)/len(pnl3):>10.1%}")

    return setups, ev


if __name__ == "__main__":
    s_exact, ev_exact = run("exact")
    print("\n\n" + "#" * 92)
    print("# PROXY STUDY -- longer history, but mom_4h/mom_12h REPLACED by 1d/3d daily")
    print("# momentum because the 4h cache only spans ~115 days. This is NOT the")
    print("# production signal definition. Directional evidence only.")
    print("#" * 92)
    run("proxy")
