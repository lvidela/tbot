#!/usr/bin/env python3
"""
Q1 -- Which COMBINATION of conditions produces positive net expected value?

Pure-stdlib (no numpy on this VM). Reads ONLY the local cache at
/home/lisandro/data/cache/. Never calls Kraken. Places no orders.

METHODOLOGY (see REGISTRY.md R1/R2 for why each of these is mandatory)
---------------------------------------------------------------------
* Decision timestamp T = close of daily bar t (00:00 UTC of day t+1). EVERY
  condition uses only data whose bar closes at or before T.
* Cross-sectional demeaning: forward return minus the same-day equal-weight
  mean forward return over the eligible universe -> selection skill, not beta.
* Date clustering: all events on one calendar day collapse to ONE observation
  (equal-weight mean of their excess returns) before means / t-stats.
* Costs: NET excess = mean excess - 1.83% (4 legs @ 0.40% maker + 5.4bp/leg
  adverse selection; registry A1).
* Universe: is_stable pairs excluded, plus EURUSD, GBPUSD, PAXGUSD.
* Multiple testing: 31 subsets x 3 horizons = 93 tests -> Bonferroni alpha.
* Chronological 50/50 split reported for every combination.
"""

import json, math, os, itertools, datetime
from statistics import mean, median, pstdev

CACHE = "/home/lisandro/data/cache"
COST = 0.0183                      # tactical round trip, registry A1
HORIZONS = (1, 2, 3)
LOOKBACK = 30                      # trading days for vol / volume / range
MIN_EVENTS_DAYS = 5                # below this, stats are not reported as meaningful
EXCLUDE = {"EURUSD", "GBPUSD", "PAXGUSD"}
DAY = 86400

CONDS = ["vol_exp", "vol_conf", "momentum", "breakout", "rel_str"]

# ---------------------------------------------------------------- statistics
def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 200, 3.0e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN: d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS: break
    return h

def betai(a, b, x):
    """Regularized incomplete beta I_x(a,b)."""
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbeta) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta) * _betacf(b, a, 1.0 - x) / b

def t_sf2(t, df):
    """Two-sided p-value for Student-t."""
    if df <= 0: return float("nan")
    return betai(0.5 * df, 0.5, df / (df + t * t))

def sample_sd(xs):
    n = len(xs)
    if n < 2: return float("nan")
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))

# ---------------------------------------------------------------- load cache
def load():
    d1 = json.load(open(os.path.join(CACHE, "ohlc_1d.json")))
    d4 = json.load(open(os.path.join(CACHE, "ohlc_4h.json")))
    meta = json.load(open(os.path.join(CACHE, "meta.json")))
    pairs = sorted(p for p in d1
                   if p not in EXCLUDE
                   and not meta.get(p, {}).get("is_stable", False))
    return d1, d4, meta, pairs

def build_features(d1, d4, pairs):
    """feat[pair][t_index] = dict of everything known at close of daily bar t."""
    feat, dates = {}, {}
    for p in pairs:
        rows = d1[p]
        ts    = [r[0] for r in rows]
        close = [r[4] for r in rows]
        high  = [r[2] for r in rows]
        low   = [r[3] for r in rows]
        vwap  = [r[5] for r in rows]
        vol   = [r[6] for r in rows]
        usdvol = [vol[i] * (vwap[i] if vwap[i] > 0 else close[i]) for i in range(len(rows))]
        ret = [None] + [close[i] / close[i - 1] - 1.0 if close[i - 1] > 0 else None
                        for i in range(1, len(rows))]

        # 4h closes keyed by bar-start timestamp
        c4 = {r[0]: r[4] for r in d4.get(p, [])}

        f = {}
        for i in range(len(rows)):
            T = ts[i] + DAY                      # decision timestamp
            rec = {"ts": ts[i], "T": T, "close": close[i], "ret1d": ret[i]}

            # --- trailing stats over the 30 days BEFORE today (strictly prior)
            if i >= LOOKBACK:
                prev_rets = [ret[j] for j in range(i - LOOKBACK, i)]
                if all(r is not None for r in prev_rets):
                    sd = sample_sd(prev_rets)
                    rec["sd30"] = sd
                    if sd and sd > 0 and ret[i] is not None:
                        rec["vol_ratio"] = abs(ret[i]) / sd
                prev_vol = usdvol[i - LOOKBACK:i]
                mv = sum(prev_vol) / len(prev_vol)
                rec["usdvol"] = usdvol[i]
                if mv > 0:
                    rec["vol_mult"] = usdvol[i] / mv
                # 30d high/low range INCLUDING today (known at close)
                hi = max(high[i - LOOKBACK + 1:i + 1])
                lo = min(low[i - LOOKBACK + 1:i + 1])
                rec["hi30"], rec["lo30"] = hi, lo
                if close[i] > 0 and hi > lo:
                    rec["range_pos"] = (close[i] - lo) / (hi - lo)
                    rec["range_w"] = (hi - lo) / close[i]

            # --- intraday, from 4h bars closing exactly at T
            c_T   = c4.get(T - 4 * 3600)         # bar 20:00 -> closes at T
            c_T4  = c4.get(T - 8 * 3600)         # bar 16:00 -> closes at T-4h
            c_T12 = c4.get(T - 16 * 3600)        # bar 08:00 -> closes at T-12h
            if c_T and c_T4 and c_T4 > 0:
                rec["ret4h"] = c_T / c_T4 - 1.0
            if c_T and c_T12 and c_T12 > 0:
                rec["ret12h"] = c_T / c_T12 - 1.0

            # --- forward returns (used only as outcomes)
            for h in HORIZONS:
                if i + h < len(rows) and close[i] > 0:
                    rec["fwd%d" % h] = close[i + h] / close[i] - 1.0
            f[ts[i]] = rec
            dates.setdefault(ts[i], []).append(p)
        feat[p] = f
    return feat, dates

def add_relative_strength(feat, dates):
    """Same-day cross-sectional MEDIAN 12h return -> excess 12h return."""
    for ts, ps in dates.items():
        vals = [feat[p][ts]["ret12h"] for p in ps if "ret12h" in feat[p][ts]]
        if len(vals) < 5:
            continue
        med = median(vals)
        for p in ps:
            rec = feat[p][ts]
            if "ret12h" in rec:
                rec["rs"] = rec["ret12h"] - med

# ---------------------------------------------------------------- conditions
def cond_flags(rec):
    """Each condition -> True / False / None (undeterminable at decision time)."""
    out = {}
    out["vol_exp"]  = (rec["vol_ratio"] >= 1.5) if "vol_ratio" in rec else None
    out["vol_conf"] = (rec["vol_mult"] >= 3.0) if "vol_mult" in rec else None
    if "ret4h" in rec and "ret12h" in rec:
        out["momentum"] = (rec["ret4h"] >= 0.02 and rec["ret12h"] > 0)
    else:
        out["momentum"] = None
    if "range_pos" in rec and rec.get("ret1d") is not None:
        out["breakout"] = (rec["range_pos"] >= 0.95 and rec["range_w"] >= 0.03
                           and rec["ret1d"] > 0)
    else:
        out["breakout"] = None
    out["rel_str"] = (rec["rs"] >= 0.03) if "rs" in rec else None
    return out

# ---------------------------------------------------------------- core study
def universe_means(feat, dates, pairs):
    """Same-day equal-weight universe forward return, per horizon."""
    um = {}
    for ts, ps in dates.items():
        for h in HORIZONS:
            vals = [feat[p][ts]["fwd%d" % h] for p in ps if "fwd%d" % h in feat[p][ts]]
            if len(vals) >= 5:
                um[(ts, h)] = sum(vals) / len(vals)
    return um

def collect(feat, dates, flags, subset, h, um):
    """Return (per-event excess list, {date: [excess,...]}) for one subset/horizon."""
    events, byday = [], {}
    for ts, ps in dates.items():
        if (ts, h) not in um:
            continue
        base = um[(ts, h)]
        for p in ps:
            fl = flags[p][ts]
            if any(fl[c] is None for c in subset):
                continue
            if not all(fl[c] for c in subset):
                continue
            rec = feat[p][ts]
            key = "fwd%d" % h
            if key not in rec:
                continue
            ex = rec[key] - base
            events.append((ts, p, ex))
            byday.setdefault(ts, []).append(ex)
    return events, byday

def stats(byday):
    if not byday:
        return None
    days = sorted(byday)
    obs = [mean(byday[d]) for d in days]
    n = len(obs)
    m = sum(obs) / n
    sd = sample_sd(obs) if n > 1 else float("nan")
    se = sd / math.sqrt(n) if n > 1 and sd == sd else float("nan")
    t = m / se if se and se == se and se > 0 else float("nan")
    p = t_sf2(t, n - 1) if t == t else float("nan")
    return {
        "n_days": n,
        "mean": m,
        "median": median(obs),
        "sd": sd,
        "t": t,
        "p": p,
        "net": m - COST,
        "p_gt_cost": sum(1 for x in obs if x > COST) / n,
        "first": days[0],
        "last": days[-1],
    }

def sample_domain(flags, dates, subset):
    """Calendar days on which every condition in the subset is computable."""
    ds = set()
    for ts, ps in dates.items():
        for p in ps:
            fl = flags[p][ts]
            if all(fl[c] is not None for c in subset):
                ds.add(ts)
                break
    return sorted(ds)


# ------------------------------------------------- permutation / power extras
def eligible_pool(feat, dates, flags, subset, h, um):
    """Per day: assets whose subset conditions are COMPUTABLE and which have fwd_h."""
    pool = {}
    for ts, ps in dates.items():
        if (ts, h) not in um:
            continue
        ok = [p for p in ps
              if all(flags[p][ts][c] is not None for c in subset)
              and ("fwd%d" % h) in feat[p][ts]]
        if ok:
            pool[ts] = ok
    return pool

def perm_family_test(feat, dates, flags, um, results, n_perm=2000, seed=20260924):
    """Family-wise max-|t| permutation test.

    For each test we keep the realised (day -> n_events) schedule and re-draw the
    selected assets at random from that day's eligible pool. This preserves the
    date clustering, the number of events per day, and the cross-sectional
    correlation structure, and destroys only the signal->asset link.
    Reported: distribution of max |t| over all 93 tests under the null.
    """
    import random
    rng = random.Random(seed)
    specs = []
    for r in results:
        subset, h = r["subset"], r["h"]
        pool = eligible_pool(feat, dates, flags, subset, h, um)
        sched = []
        for d in sorted(r["_byday_counts"]):
            k = r["_byday_counts"][d]
            cand = pool.get(d, [])
            if len(cand) >= k:
                sched.append((d, k, cand))
        specs.append((r, sched, h))

    fwd = {}
    for p in feat:
        for ts, rec in feat[p].items():
            for h in HORIZONS:
                key = "fwd%d" % h
                if key in rec:
                    fwd[(p, ts, h)] = rec[key]

    obs_max = max(abs(r["t"]) for r in results if r["t"] == r["t"])
    maxts = []
    per_test_ge = [0] * len(specs)
    for _ in range(n_perm):
        mt = 0.0
        for i, (r, sched, h) in enumerate(specs):
            obs = []
            for d, k, cand in sched:
                base = um[(d, h)]
                picks = rng.sample(cand, k)
                obs.append(sum(fwd[(p, d, h)] - base for p in picks) / k)
            n = len(obs)
            if n < 2:
                continue
            m = sum(obs) / n
            sd = sample_sd(obs)
            if not sd or sd != sd or sd <= 0:
                continue
            t = m / (sd / math.sqrt(n))
            if abs(t) > mt:
                mt = abs(t)
            if abs(t) >= abs(r["t"]):
                per_test_ge[i] += 1
        maxts.append(mt)
    maxts.sort()
    q95 = maxts[int(0.95 * len(maxts))]
    fw_p = sum(1 for x in maxts if x >= obs_max) / len(maxts)
    for i, (r, _, _) in enumerate(specs):
        r["perm_p"] = per_test_ge[i] / n_perm
    return {"obs_max_t": obs_max, "null_max_t_q95": q95,
            "null_max_t_median": maxts[len(maxts) // 2],
            "familywise_p": fw_p, "n_perm": n_perm}

def mde(st, alpha_t):
    """Minimum detectable mean excess at the given |t| threshold."""
    if st is None or st["n_days"] < 2 or st["sd"] != st["sd"]:
        return float("nan")
    return alpha_t * st["sd"] / math.sqrt(st["n_days"])

def main():
    d1, d4, meta, pairs = load()
    feat, dates = build_features(d1, d4, pairs)
    add_relative_strength(feat, dates)
    flags = {p: {ts: cond_flags(rec) for ts, rec in feat[p].items()} for p in pairs}
    um = universe_means(feat, dates, pairs)

    subsets = []
    for k in range(1, 6):
        subsets.extend(itertools.combinations(CONDS, k))
    n_tests = len(subsets) * len(HORIZONS)
    alpha_b = 0.05 / n_tests
    # Bonferroni |t| threshold, large-df normal reference
    def z_for(p):
        lo, hi = 0.0, 10.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if math.erfc(mid / math.sqrt(2)) > p: lo = mid
            else: hi = mid
        return (lo + hi) / 2
    z_b = z_for(alpha_b)

    results = []
    for subset in subsets:
        dom = sample_domain(flags, dates, subset)
        if not dom:
            continue
        mid = dom[len(dom) // 2]
        for h in HORIZONS:
            events, byday = collect(feat, dates, flags, subset, h, um)
            st = stats(byday)
            if st is None:
                continue
            st["_byday_counts"] = {d: len(v) for d, v in byday.items()}
            st["subset"] = subset
            st["h"] = h
            st["n_events"] = len(events)
            st["dom_first"], st["dom_last"], st["dom_n"] = dom[0], dom[-1], len(dom)
            st["split_ts"] = mid
            in_d  = {d: v for d, v in byday.items() if d < mid}
            out_d = {d: v for d, v in byday.items() if d >= mid}
            st["is"]  = stats(in_d)
            st["oos"] = stats(out_d)
            st["sig_bonf"] = (st["t"] == st["t"] and abs(st["t"]) >= z_b)
            results.append(st)

    out = {
        "_feat": feat, "_dates": dates, "_flags": flags, "_um": um,
        "n_tests": n_tests,
        "alpha_bonferroni": alpha_b,
        "z_bonferroni": z_b,
        "cost": COST,
        "universe": pairs,
        "n_universe": len(pairs),
        "results": results,
    }
    return out

def fmt(x, pct=True, nd=2):
    if x is None or (isinstance(x, float) and x != x):
        return "  n/a"
    return ("%+.*f%%" % (nd, 100 * x)) if pct else ("%.*f" % (nd, x))

def dstr(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d")

if __name__ == "__main__":
    import sys
    out = main()
    res = out["results"]
    zb = out["z_bonferroni"]
    print("universe n=%d: %s" % (out["n_universe"], ",".join(out["universe"])))
    print("tests=%d  bonferroni alpha=%.3e  |t| threshold=%.3f  cost=%.2f%%"
          % (out["n_tests"], out["alpha_bonferroni"], zb, 100 * out["cost"]))
    print()
    hdr = ("%-44s %2s %5s %5s %8s %8s %6s %7s %8s %5s %8s %6s %8s %6s %9s"
           % ("subset", "h", "nev", "nday", "mean", "median", "t", "p",
              "NET", "P>c", "ISmean", "ISt", "OOSmean", "OOSt", "MDE"))
    print(hdr); print("-" * len(hdr))
    for r in sorted(res, key=lambda r: -r["net"]):
        i_, o = r["is"], r["oos"]
        print("%-44s %2d %5d %5d %8s %8s %6.2f %7.4f %8s %5.2f %8s %6s %8s %6s %9s"
              % ("+".join(r["subset"]), r["h"], r["n_events"], r["n_days"],
                 fmt(r["mean"]), fmt(r["median"]), r["t"], r["p"],
                 fmt(r["net"]), r["p_gt_cost"],
                 fmt(i_["mean"]) if i_ else "n/a",
                 ("%.2f" % i_["t"]) if i_ and i_["t"] == i_["t"] else "n/a",
                 fmt(o["mean"]) if o else "n/a",
                 ("%.2f" % o["t"]) if o and o["t"] == o["t"] else "n/a",
                 fmt(mde(r, zb))))
    print()
    print("SAMPLE WINDOWS (days on which the subset is computable at all):")
    seen = set()
    for r in sorted(res, key=lambda r: "+".join(r["subset"])):
        k = "+".join(r["subset"])
        if k in seen: continue
        seen.add(k)
        print("  %-44s %s .. %s  (%d days)" % (k, dstr(r["dom_first"]), dstr(r["dom_last"]), r["dom_n"]))
    print()
    surv = [r for r in res if r["sig_bonf"]]
    print("SURVIVING BONFERRONI (|t| >= %.3f): %d" % (zb, len(surv)))
    for r in surv:
        print("  %s h=%d t=%.2f" % ("+".join(r["subset"]), r["h"], r["t"]))
    print()
    nperm = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    pf = perm_family_test(out["_feat"], out["_dates"], out["_flags"], out["_um"], res, n_perm=nperm)
    print("PERMUTATION FAMILY-WISE TEST (%d draws, schedule-preserving):" % pf["n_perm"])
    print("  observed max |t| over all %d tests : %.3f" % (out["n_tests"], pf["obs_max_t"]))
    print("  null median max |t|                : %.3f" % pf["null_max_t_median"])
    print("  null 95th pct max |t|              : %.3f" % pf["null_max_t_q95"])
    print("  family-wise p-value                : %.4f" % pf["familywise_p"])
    print()
    print("TOP 10 BY NET EXCESS, with permutation p (single-test, not corrected):")
    for r in sorted(res, key=lambda r: -r["net"])[:10]:
        print("  %-44s h=%d net=%s t=%.2f perm_p=%.3f n_days=%d"
              % ("+".join(r["subset"]), r["h"], fmt(r["net"]), r["t"], r["perm_p"], r["n_days"]))
    for r in res:
        r.pop("_byday_counts", None)
    json.dump({"meta": {k: v for k, v in out.items() if not k.startswith("_") and k != "results"},
               "perm": pf, "results": res},
              open("/home/lisandro/backtests/q1_results.json", "w"), default=str, indent=1)
    print("\nwrote /home/lisandro/backtests/q1_results.json")

# ----------------------------------------------------------------- diagnostics
def diagnostics(top_n=6, n_drop=1):
    """Fragility checks for the best-looking combinations:
       naive (un-demeaned, un-clustered) t vs corrected t, and leave-one-day-out."""
    out = main()
    res = out["results"]
    rows = []
    for r in sorted(res, key=lambda r: -r["net"])[:top_n]:
        subset, h = r["subset"], r["h"]
        events, byday = collect(out["_feat"], out["_dates"], out["_flags"], subset, h, out["_um"])
        # naive: raw forward returns, one obs per EVENT
        raw = []
        for ts, p, ex in events:
            raw.append(out["_feat"][p][ts]["fwd%d" % h])
        n = len(raw); m = sum(raw) / n; sd = sample_sd(raw)
        t_naive = m / (sd / math.sqrt(n))
        # event-level demeaned but unclustered
        exs = [e[2] for e in events]
        m2 = sum(exs) / len(exs); sd2 = sample_sd(exs)
        t_dm = m2 / (sd2 / math.sqrt(len(exs)))
        # leave-worst/best-day-out on the clustered series
        days = sorted(byday); obs = {d: mean(byday[d]) for d in days}
        best = max(days, key=lambda d: obs[d]); worst = min(days, key=lambda d: obs[d])
        wo_best = stats({d: v for d, v in byday.items() if d != best})
        wo_worst = stats({d: v for d, v in byday.items() if d != worst})
        rows.append({
            "subset": "+".join(subset), "h": h,
            "naive_mean": m, "naive_t": t_naive,
            "dm_event_mean": m2, "dm_event_t": t_dm,
            "clustered_mean": r["mean"], "clustered_t": r["t"], "median": r["median"],
            "drop_best_mean": wo_best["mean"], "drop_best_t": wo_best["t"],
            "drop_worst_mean": wo_worst["mean"], "drop_worst_t": wo_worst["t"],
            "best_day": dstr(best), "best_day_val": obs[best],
            "n_days": r["n_days"], "n_events": r["n_events"],
        })
    return rows
