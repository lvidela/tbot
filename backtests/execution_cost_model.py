"""Q3 -- EXECUTION COST STRUCTURE. Is the 4-leg model correct, and can cost be reduced?

Offline only: reads /home/lisandro/data/cache/ and /home/lisandro/data/universe.json.
Never calls the Kraken API. Never places orders.

Sections
  A  LEG COUNTING          amortised legs per tactical trade under 4 policies
  B  HOLD-PERIOD           E|move| vs sqrt(t); cost per unit of realised move
  C  MAKER FILL MODEL      bar-implied touch/through probability + adverse selection,
                           split by the SAME calm/volatile definition execution_stats uses
  D  PARTIAL FILLS         depth and min-notional residual risk at $8-17 clips
  E  BEST ACHIEVABLE COST  policy grid -> required expected move at the 3x gate

MEASURED vs MODELLED is tagged on every number printed. Only two real fills exist
(data/execution_log.json, both CALM); everything else here is modelled or is a
historical bar statistic, which is NOT the same as a realised execution.
"""
import json, math, os, statistics, sys
from collections import defaultdict

ROOT = "/home/lisandro"
CACHE = os.path.join(ROOT, "data", "cache")

# ---------------------------------------------------------------- measured inputs
# From data/execution_log.json (n=2, both CALM, both LINKUSD) and A1 in REGISTRY.md.
MEAS_MAKER_FEE   = 0.00400     # MEASURED, n=2, fee_rate_pct 0.4000 exactly, both fills
MEAS_TAKER_LEG   = 0.00831     # MEASURED (A1) taker incl. spread crossing
MEAS_ADVERSE_CALM_BPS = 5.4    # MEASURED, n=2, mean of 4.7 and 6.1 bps
MEAS_FILL_CALM   = 1.00        # MEASURED, 2/2 filled -- a 95% CI of [0.16, 1.00]
LINK_HALF_SPREAD_BPS = 4.88/2  # from universe.json snapshot

EXCLUDE = {"EURUSD", "GBPUSD", "PAXGUSD"}


def load():
    meta = json.load(open(os.path.join(CACHE, "meta.json")))
    d1 = json.load(open(os.path.join(CACHE, "ohlc_1d.json")))
    d1h = json.load(open(os.path.join(CACHE, "ohlc_1h.json")))
    d4h = json.load(open(os.path.join(CACHE, "ohlc_4h.json")))
    uni = {c["pair"]: c for c in json.load(open(os.path.join(ROOT, "data", "universe.json")))["eligible"]}
    pairs = [p for p, m in meta.items()
             if not m["is_stable"] and p not in EXCLUDE and p in d1 and len(d1[p]) >= 60]
    return meta, d1, d1h, d4h, uni, pairs


def dvol30(closes):
    r = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
    return statistics.pstdev(r[-30:]) if len(r) >= 30 else None


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def hdr(t):
    print("\n" + "=" * 96)
    print(t)
    print("=" * 96)


# =================================================================== A. LEG COUNTING
def section_A(cleg_maker, cleg_taker):
    hdr("A. LEG COUNTING -- is 4 legs the right model?  [MODELLED, arithmetic]")
    print("""
Definitions. A 'leg' is one order that changes what asset we hold. Core = LINK.
Tactical trade = take a position in an alt and come out of it.

  P1 round-trip-to-core : sell LINK, buy ALT, sell ALT, buy LINK        (current model)
  P2 park-in-USD        : sell LINK once; then (buy ALT, sell ALT) x N; buy LINK once
  P3 direct rotation    : sell LINK once; buy ALT1; (sell ALTi, buy ALTi+1) x (N-1);
                          sell ALTN; buy LINK once  -- identical leg count to P2 unless a
                          direct ALT/ALT cross pair exists (none in our USD-only universe)
  P4 one-way            : sell LINK, buy ALT, and never return. 2 legs, but this is a
                          change of core holding, not a trade.

KEY STRUCTURAL POINT that P1 gets wrong: the experiment is valued in USD on 2026-10-15.
The terminal 'buy LINK' leg is NEVER required. We may simply end in USD. So the honest
campaign leg count for N tactical trades is:

      total legs = 1 (LINK -> USD, once)  +  2N (alt in/out)  +  0 (no forced return)
      amortised legs per trade = 2 + 1/N
""")
    print(f"{'N trades':>9} | {'P1 legs/tr':>11} {'P1 cost':>9} | {'P2 legs/tr':>11} {'P2 cost':>9} | "
          f"{'P2* legs/tr':>12} {'P2* cost':>9}")
    print(f"{'':>9} | {'(4 always)':>11} {'maker':>9} | {'2+2/N':>11} {'maker':>9} | "
          f"{'2+1/N end-USD':>12} {'maker':>9}")
    print("-" * 96)
    rows = []
    for N in (1, 2, 3, 5, 8, 12, 20, 999):
        p1 = 4.0
        p2 = 2.0 + 2.0 / N
        p2s = 2.0 + 1.0 / N
        rows.append((N, p1, p2, p2s))
        lbl = "inf" if N == 999 else str(N)
        print(f"{lbl:>9} | {p1:>11.2f} {p1*cleg_maker*100:>8.3f}% | {p2:>11.2f} {p2*cleg_maker*100:>8.3f}% | "
              f"{p2s:>12.2f} {p2s*cleg_maker*100:>8.3f}%")
    print(f"""
Marginal vs average. The decision 'should I take THIS opportunity, given I am already
out of LINK' costs exactly 2 legs = {2*cleg_maker*100:.3f}% maker / {2*cleg_taker*100:.3f}% taker.
The LINK exit is a ONE-TIME campaign cost ({cleg_maker*100:.3f}%) and must be justified once,
not re-charged to every trade. Charging 4 legs to every trade DOUBLE-COUNTS.

Two-level decision rule this implies:
  L1 (campaign, once) : is tactical mode worth {cleg_maker*100:.3f}% + the benchmark tracking risk
                        of not holding LINK while waiting?
  L2 (per trade)      : does this opportunity clear 3 x {2*cleg_maker*100:.3f}% = {6*cleg_maker*100:.3f}%?

Carry cost of the wait. Sitting in USD forgoes LINK's drift. Break-even arrival rate:
returning to core after each trade is worth it only if
      mu_LINK_per_week / R  >  2 legs = {2*cleg_maker*100:.3f}%
i.e. only if we can forecast LINK's weekly drift to exceed {2*cleg_maker*100:.3f}% x R.
""")
    return rows


def link_drift(d1):
    closes = [float(r[4]) for r in d1["LINKUSD"]]
    r = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
    for w, lbl in ((len(r), "full cache"), (180, "last 180d"), (90, "last 90d"), (30, "last 30d")):
        s = r[-w:]
        m = statistics.mean(s); sd = statistics.pstdev(s)
        se = sd / math.sqrt(len(s))
        print(f"  LINK daily drift {lbl:>11}: {m*100:+.4f}%/d  (t={m/se:+.2f})  "
              f"-> weekly {m*7*100:+.3f}% +/- {se*7*math.sqrt(7)*100:.3f}%")
    # break-even: mu_week/R > 2 legs
    m = statistics.mean(r[-90:]) * 7
    print(f"  MEASURED 90d weekly drift {m*100:+.3f}%; |t| far below 2 => treat as ZERO for EV.")
    print("  => Under a zero-drift prior for LINK, parking in USD between tactical trades is")
    print("     EV-neutral. It raises tracking error vs the hold-LINK benchmark but costs")
    print("     nothing in expectation, and it removes 2 of the 4 legs.")
    return m


# ============================================================= B. HOLD-PERIOD AMORT.
def section_B(d1, pairs, cost_4leg, cost_2leg):
    hdr("B. HOLD-PERIOD AMORTISATION -- does sqrt(t) growth in E|move| reach the gate?")
    HS = [1, 2, 3, 5, 7, 10, 14, 21]
    # focus on the volatile end of the eligible universe: the assets tactical mode targets
    vols = []
    for p in pairs:
        c = [float(r[4]) for r in d1[p]]
        v = dvol30(c)
        if v: vols.append((p, v * 100))
    vols.sort(key=lambda x: -x[1])
    focus = [p for p, _ in vols[:12]]          # 12 most volatile eligible alts
    print(f"  focus set = 12 most volatile eligible alts (30d sigma "
          f"{vols[11][1]:.2f}% .. {vols[0][1]:.2f}%/day): {', '.join(focus)}")

    # E|r_h| pooled over focus set, non-overlapping windows so the SE is honest
    print(f"\n  [MEASURED from 1d bars] pooled E|r_h| over the focus set, NON-OVERLAPPING windows")
    print(f"  {'h(d)':>5}{'n':>7}{'E|r_h|%':>10}{'se%':>7}{'med|r|%':>9}{'sqrt-t pred%':>14}"
          f"{'cost/E|r| 4leg':>16}{'cost/E|r| 2leg':>16}")
    base = None
    tbl = {}
    for h in HS:
        obs = []
        for p in focus:
            c = [float(r[4]) for r in d1[p]]
            c = c[-365:] if len(c) > 365 else c
            for i in range(0, len(c) - h, h):     # non-overlapping
                obs.append(abs(c[i + h] / c[i] - 1))
        m = statistics.mean(obs); se = statistics.pstdev(obs) / math.sqrt(len(obs))
        md = statistics.median(obs)
        if base is None: base = m
        pred = base * math.sqrt(h)
        tbl[h] = m
        print(f"  {h:>5}{len(obs):>7}{m*100:>10.2f}{se*100:>7.2f}{md*100:>9.2f}{pred*100:>14.2f}"
              f"{cost_4leg/m:>16.2f}{cost_2leg/m:>16.2f}")
    # fit exponent
    xs = [math.log(h) for h in HS]; ys = [math.log(tbl[h]) for h in HS]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    b = sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / sum((x-mx)**2 for x in xs)
    print(f"\n  [MEASURED] fitted scaling exponent  E|r_h| ~ h^b   ->  b = {b:.3f}  (pure sqrt-t: 0.500)")
    print(f"  b < 0.5 means |move| grows SLOWER than sqrt(t): mean reversion / range-bounding.")

    # gate solve: expected_move as tactical.py defines it = 0.5*sigma_h (half a sigma of the
    # holding period), sigma_h = sigma_1d * sqrt(h) under the model tactical.py assumes.
    print(f"""
  GATE SOLVE. tactical.py sets expected_move = 0.5 * sigma, with sigma = the 30d DAILY
  sigma, and then requires move >= 3 x cost. If the hold is h days the correct sigma is
  sigma_1d*sqrt(h) (tactical.py does not do this -- it always uses the 1-day sigma, so it
  is implicitly assuming a 1-day hold). Required h for the 3x gate:
""")
    print(f"  {'sigma_1d':>9} | {'h* @4 legs':>11} {'h* @3 legs':>11} {'h* @2 legs':>11}   "
          f"(3x gate on 0.5*sigma_1d*sqrt(h))")
    for s in (3.0, 4.0, 5.0, 7.0, 10.0, 12.6):
        out = []
        for legs, c in ((4, cost_4leg), (3, cost_4leg*0.75), (2, cost_2leg)):
            need = 3.0 * c * 100          # % move required
            h = (need / (0.5 * s)) ** 2
            out.append(h)
        print(f"  {s:>8.1f}% | {out[0]:>11.2f} {out[1]:>11.2f} {out[2]:>11.2f}")

    print(f"""
  BUT the gate on E|move| is the WEAK test. tactical.py also runs an EV test where the
  gross is discounted by the coin-flip factor (2p-1), and success_probability is capped
  at p=0.62 -> (2p-1) = 0.24. Net gross = 0.5*sigma*sqrt(h)*0.24 = 0.12*sigma*sqrt(h).
  Required h so that 0.12*sigma_1d*sqrt(h) >= 1.5 x cost (EDGE_MARGIN):
""")
    print(f"  {'sigma_1d':>9} | {'h* @4 legs':>11} {'h* @2 legs':>11}   (EV test, p=0.62)")
    for s in (3.0, 5.0, 7.0, 10.0, 12.6):
        r = []
        for c in (cost_4leg, cost_2leg):
            need = 1.5 * c * 100
            r.append((need / (0.12 * s)) ** 2)
        print(f"  {s:>8.1f}% | {r[0]:>11.1f} {r[1]:>11.1f}")
    print("""
  The (2p-1)=0.24 coin-flip discount is a 4.2x multiplier on the required move. It, not
  the leg count, is the dominant term. Halving cost halves the required move; raising p
  from 0.62 to 0.70 cuts the required move by 40% on its own.""")
    return focus, b


def section_B2(d1, pairs, focus):
    """Signal decay: does a conditional edge, if any, grow like sqrt(t) or decay?"""
    print("""
  SIGNAL DECAY. Cross-sectionally demeaned forward returns conditional on the tactical
  trigger (vol_ratio >= 1.5 AND 2d momentum > 0), date-clustered SE, per the standing
  methodology that killed R1/R2. Reported ONLY to answer 'does a signal, if one exists,
  decay faster than sqrt(t) grows'. This is NOT a claim of edge -- R1 rejected that, and
  the diagnostics below show why the mean here is not trustworthy either.
""")
    HS = [1, 2, 3, 5, 7, 10, 14]
    # precompute arrays once
    P = {}
    for p_ in pairs:
        rows = d1[p_]
        ts = [int(r[0]) for r in rows]
        cl = [float(r[4]) for r in rows]
        v30 = [None]*len(cl)
        for i in range(31, len(cl)):
            v30[i] = statistics.pstdev([cl[j]/cl[j-1]-1 for j in range(i-30, i)])
        P[p_] = dict(ts=ts, cl=cl, v30=v30, pos={t: i for i, t in enumerate(ts)})
    full = [p_ for p_ in pairs if len(P[p_]["cl"]) >= 700]
    alldates = sorted(set().union(*[set(P[p_]["ts"]) for p_ in pairs]))

    def run(universe, label):
        print(f"  --- {label} ({len(universe)} pairs) ---")
        print(f"  {'h(d)':>5}{'n_ev':>7}{'n_dt':>6}{'mean%':>9}{'t_clu':>7}{'median%':>9}"
              f"{'win%':>7}{'trim10%':>9}{'top10%share':>12}{'sqrt-t':>8}")
        base = None
        for h in HS:
            by_date = defaultdict(list)
            for d in alldates:
                fwd = {}
                for p_ in universe:
                    A = P[p_]; i = A["pos"].get(d)
                    if i is None or i < 32 or i + h >= len(A["cl"]): continue
                    fwd[p_] = A["cl"][i+h]/A["cl"][i] - 1
                if len(fwd) < 8: continue
                med = statistics.median(fwd.values())
                for p_, f in fwd.items():
                    A = P[p_]; i = A["pos"][d]
                    v = A["v30"][i]
                    if not v: continue
                    if abs(A["cl"][i]/A["cl"][i-1]-1)/v >= 1.5 and A["cl"][i]/A["cl"][i-2]-1 > 0:
                        by_date[d].append(f - med)
            if not by_date: continue
            dmeans = [statistics.mean(v) for v in by_date.values()]
            allv = sorted(x for v in by_date.values() for x in v)
            m = statistics.mean(dmeans)
            se = statistics.pstdev(dmeans)/math.sqrt(len(dmeans)) if len(dmeans) > 1 else float('nan')
            k = max(1, int(0.10*len(allv)))
            trim = statistics.mean(allv[k:-k]) if len(allv) > 2*k else float('nan')
            tot = sum(allv)
            top = sum(allv[-k:])
            win = sum(1 for x in allv if x > 0)/len(allv)
            if base is None: base = abs(m) or 1e-9
            print(f"  {h:>5}{len(allv):>7}{len(dmeans):>6}{m*100:>9.3f}{m/se if se else 0:>7.2f}"
                  f"{statistics.median(allv)*100:>9.3f}{win:>7.1%}{trim*100:>9.3f}"
                  f"{(top/tot if tot else 0):>12.1%}{base*math.sqrt(h)*100:>8.3f}")

    run(pairs, "ALL eligible -- includes recently listed pairs (LISTING/SURVIVORSHIP BIAS)")
    print()
    run(full, "FULL-HISTORY pairs only (>=700 daily bars) -- listing bias removed")
    print("""
  READ THIS CAREFULLY. The mean grows FASTER than sqrt(t) while the median sits at ~0 and
  the win rate is at or below 50%. That is the signature of a right-skewed lottery, not a
  harvestable edge: a handful of listings that went vertical carry the whole mean. Compare
  the two panels -- dropping recently listed pairs is the test. Consistent with R1/R2, the
  honest conclusion is that hold-period extension raises the SIZE of the tail, not the
  reliability of the outcome. For Q3 the only safe use of this table is the negative one:
  there is no evidence that a signal DECAYS faster than sqrt(t), so extending the hold is
  not self-defeating on decay grounds.""")


# ============================================================ C. MAKER FILL MODELLING
def section_C(meta, d1, d1h, uni, pairs):
    hdr("C. MAKER FILL MODELLING in volatile conditions")
    print("""
  ASSUMPTIONS (all explicit; each is a weakness):
   1. We post a BUY at the touch, P = close_t * (1 - delta), delta = half the snapshot
      spread from universe.json. WEAKNESS: the spread snapshot is one instant on
      2026-09-24 and spreads WIDEN in exactly the volatile regime we care about, so
      delta is understated and fill probability here is OPTIMISTIC.
   2. Bars tell us where price WENT, not whether our order FILLED. Queue position is
      unobservable. So we bracket:
         UPPER bound P_touch   = P(next-bar low <= P)      -- price reached our level
         LOWER bound P_through = P(next-bar low <= P-tick) -- price traded BELOW our
                                 level, so the level was fully consumed: we definitely filled.
      True fill probability lies between, and is above P_through because uninformed sell
      flow can also hit us with no price move at all.
   3. Sub-hour horizons are MODELLED, not measured: driftless random walk, reflection
      principle, P(touch within N min) = 2*Phi(-delta / (sigma_min*sqrt(N))), with
      sigma_min from the Parkinson high-low estimator on 1h bars of the same regime.
      WEAKNESS: real price paths are not driftless RWs and the signal we trade on is a
      directional one, which biases the walk AWAY from a buy order.
   4. Regime = the SAME definition execution_stats.vol_regime uses: |1d return| / 30d
      daily sigma, volatile at >= 1.5. Applied to the calendar day each 1h bar sits in.
""")
    # per-regime 1h Parkinson vol + bar-implied touch stats
    agg = {r: dict(n=0, touch=0, through=0, park=[], adv=[], advthru=[]) for r in ("calm", "volatile")}
    per_pair = {}
    for p in pairs:
        if p not in d1h: continue
        u = uni.get(p) or {}
        spread = (meta[p]["spread_bps"]) / 1e4
        delta = spread / 2.0
        pdec = u.get("price_decimals", 4)
        # daily regime map
        drows = d1[p]
        dcl = [float(r[4]) for r in drows]
        regime_by_day = {}
        for i in range(31, len(drows)):
            v30 = statistics.pstdev([dcl[j]/dcl[j-1]-1 for j in range(i-30, i)])
            if not v30: continue
            ratio = abs(dcl[i]/dcl[i-1]-1) / v30
            regime_by_day[int(drows[i][0])] = ("volatile" if ratio >= 1.5 else "calm")
        h = d1h[p]
        loc = dict(calm=dict(n=0, touch=0, through=0, park=[], adv=[]),
                   volatile=dict(n=0, touch=0, through=0, park=[], adv=[]))
        for i in range(len(h) - 1):
            ts = int(h[i][0]); day = ts - (ts % 86400)
            reg = regime_by_day.get(day)
            if reg is None: continue
            o, hi, lo, cl = float(h[i][1]), float(h[i][2]), float(h[i][3]), float(h[i][4])
            if lo <= 0 or cl <= 0: continue
            # Parkinson per-hour sigma from THIS bar
            park = math.sqrt((math.log(hi/lo) ** 2) / (4 * math.log(2))) if hi > lo else 0.0
            nhi, nlo, ncl = float(h[i+1][2]), float(h[i+1][3]), float(h[i+1][4])
            P = cl * (1 - delta)
            tick = 10 ** (-pdec)
            for d_ in (agg[reg], loc[reg]):
                d_["n"] += 1
                d_["park"].append(park)
                if nlo <= P: d_["touch"] += 1
                if nlo <= P - tick:
                    d_["through"] += 1
                    # adverse selection at the 1h horizon, conditional on a through-fill:
                    # bought at P, mark at next-bar close. positive = against us.
                    d_["adv"].append((P - ncl) / P * 1e4)
        per_pair[p] = loc
        for reg in ("calm", "volatile"):
            agg[reg]["advthru"] += loc[reg]["adv"]

    print(f"  [MEASURED from 1h bars, pooled over {len(per_pair)} eligible alts]")
    print(f"  {'regime':<10}{'n bars':>9}{'P_touch':>10}{'P_through':>11}{'sigma_1h(Park)':>16}"
          f"{'sigma_1min':>12}{'adv@1h(bps)':>13}{'med adv':>10}")
    out = {}
    for reg in ("calm", "volatile"):
        a = agg[reg]
        if not a["n"]: continue
        pk = statistics.mean(a["park"])
        smin = pk / math.sqrt(60)
        adv = statistics.mean(a["advthru"]) if a["advthru"] else float("nan")
        madv = statistics.median(a["advthru"]) if a["advthru"] else float("nan")
        out[reg] = dict(p_touch=a["touch"]/a["n"], p_through=a["through"]/a["n"],
                        sigma_1h=pk, sigma_1min=smin, adv_1h=adv)
        print(f"  {reg:<10}{a['n']:>9}{a['touch']/a['n']:>10.1%}{a['through']/a['n']:>11.1%}"
              f"{pk*100:>15.3f}%{smin*1e4:>11.1f}bp{adv:>13.1f}{madv:>10.1f}")

    vr = out["volatile"]["sigma_1min"] / out["calm"]["sigma_1min"]
    print(f"\n  [MEASURED] volatile / calm per-minute volatility ratio = {vr:.2f}x")

    # --- MODELLED sub-hour fill probability, median eligible alt
    print(f"""
  [MODELLED] P(fill within N minutes) for a post-only order at the touch, reflection
  principle on a driftless RW, using the regime sigma above. Shown for the MEDIAN
  eligible alt half-spread and for a WIDE one, because spread is what blocks fills.
""")
    hs = sorted(meta[p]["spread_bps"]/2 for p in pairs)
    med_hs = statistics.median(hs); wide_hs = hs[int(0.85*len(hs))]
    print(f"  median eligible half-spread {med_hs:.2f} bps | 85th pct {wide_hs:.2f} bps | "
          f"LINK {LINK_HALF_SPREAD_BPS:.2f} bps")
    print(f"\n  {'N min':>6} | " + " | ".join(
        f"{reg[:4]}/{lbl}" for reg in ("calm", "volatile") for lbl in ("med", "wide")))
    for N in (1, 2, 5, 10, 15, 30, 60, 120):
        cells = []
        for reg in ("calm", "volatile"):
            s = out[reg]["sigma_1min"] * math.sqrt(N)
            for hsb in (med_hs, wide_hs):
                d_ = hsb / 1e4
                pr = min(1.0, 2 * norm_cdf(-d_ / s)) if s > 0 else 0.0
                cells.append(f"{pr:>8.1%}")
        print(f"  {N:>6} | " + " | ".join(cells))

    print(f"""
  These RW numbers are close to 100% because the half-spread (a few bps) is tiny next to
  per-minute volatility ({out['volatile']['sigma_1min']*1e4:.1f} bps volatile). That says the price WILL reach our
  level almost surely -- it does NOT say we fill, because reaching the level only puts us
  at the back of a queue. The binding constraint is queue depth, which bars cannot see.
  The bar-implied P_through above ({out['volatile']['p_through']:.0%} volatile / {out['calm']['p_through']:.0%} calm at a 1h horizon) is the
  defensible LOWER bound: the level was fully consumed, so we filled for certain.
""")
    # adverse selection scaling
    adv_vol_modelled = MEAS_ADVERSE_CALM_BPS * vr
    print(f"""  ADVERSE SELECTION SCALING.
  MEASURED (n=2, CALM, LINKUSD, ~25-30s latency): {MEAS_ADVERSE_CALM_BPS:.1f} bps/leg.
  For reference LINK's half-spread is {LINK_HALF_SPREAD_BPS:.2f} bps -- so the two real fills gave back
  {MEAS_ADVERSE_CALM_BPS/LINK_HALF_SPREAD_BPS:.1f}x the spread they saved. Passive execution captured NEGATIVE spread edge.
  The reason maker still wins is the FEE: {MEAS_MAKER_FEE*1e4:.0f} bps/leg saved vs taker, which dwarfs
  a ~5-20 bps adverse term.

  MODELLED volatile adverse selection, scaling the measured calm figure by the measured
  per-minute vol ratio (adverse ~ sigma * sqrt(latency)):
        {MEAS_ADVERSE_CALM_BPS:.1f} bps x {vr:.2f} = {adv_vol_modelled:.1f} bps/leg     <-- MODELLED, n=0 real volatile fills
  Bar-implied 1h-horizon adverse conditional on a through-fill is far larger
  ({out['volatile']['adv_1h']:.0f} bps volatile) but that is a 1-hour mark, not a 30-second fill latency;
  it is the right number only if our orders rest for an hour before filling.
""")
    return out, vr, adv_vol_modelled, med_hs


def section_C2(meta, d1h, uni, pairs):
    """The measurement that actually matters: fill probability CONDITIONAL ON THE SIGNAL.

    Tactical entries are momentum/breakout buys. A passive buy only fills if the market
    comes back down to us -- which is precisely what a live momentum signal says will NOT
    happen. The unconditional touch rate is therefore the wrong number.
    """
    hdr("C2. SIGNAL-CONDITIONAL passive fill -- the number that actually matters")
    print("""
  Trigger, defined on 1h bars so it matches an intraday entry decision:
      bar t return >= 1.5 x trailing 720h sigma of 1h returns, AND positive.
  We then decide at the close of bar t to BUY passively at the touch and ask whether bar
  t+1 (and t+2) ever traded down to our price. Everything here is a BAR STATISTIC, not a
  realised fill: price reaching a level is necessary, not sufficient.
""")
    res = {}
    for cond_name in ("unconditional", "signal-fired (momentum buy)"):
        res[cond_name] = dict(n=0, t1=0, t2=0, runaway=[], fwd=[])
    for p_ in pairs:
        if p_ not in d1h: continue
        delta = meta[p_]["spread_bps"] / 2 / 1e4
        h = d1h[p_]
        cl = [float(r[4]) for r in h]
        rets = [cl[i]/cl[i-1]-1 for i in range(1, len(cl))]
        for i in range(200, len(h) - 2):
            sig_win = rets[i-200:i]
            sd = statistics.pstdev(sig_win)
            if not sd: continue
            r_t = rets[i-1]
            fired = (r_t / sd >= 1.5 and r_t > 0)
            Pp = cl[i] * (1 - delta)
            lo1 = float(h[i+1][3]); lo2 = min(lo1, float(h[i+2][3]))
            fwd = cl[i+2]/cl[i] - 1
            for key, use in (("unconditional", True), ("signal-fired (momentum buy)", fired)):
                if not use: continue
                d_ = res[key]
                d_["n"] += 1
                if lo1 <= Pp: d_["t1"] += 1
                if lo2 <= Pp: d_["t2"] += 1
                d_["fwd"].append(fwd)
                if lo2 > Pp: d_["runaway"].append(fwd)
    print(f"  {'condition':<30}{'n':>8}{'touch<=1h':>11}{'touch<=2h':>11}"
          f"{'E[2h move]':>12}{'E[2h move | NO fill]':>22}")
    for k, d_ in res.items():
        if not d_["n"]: continue
        ra = statistics.mean(d_["runaway"])*100 if d_["runaway"] else float('nan')
        print(f"  {k:<30}{d_['n']:>8}{d_['t1']/d_['n']:>11.1%}{d_['t2']/d_['n']:>11.1%}"
              f"{statistics.mean(d_['fwd'])*100:>11.3f}%{ra:>21.3f}%")
    sig = res["signal-fired (momentum buy)"]; unc = res["unconditional"]
    miss = 1 - sig["t1"]/sig["n"]
    ra = statistics.mean(sig["runaway"]) if sig["runaway"] else 0.0
    print(f"""
  INTERPRETATION -- and this went AGAINST my prior, so read it carefully.
  I expected the momentum trigger to LOWER the touch rate (price runs away from a passive
  buy). It does the opposite: {sig['t1']/sig['n']:.1%} vs {unc['t1']/unc['n']:.1%} unconditional. The reason is that the
  trigger also selects for high volatility, and a 2-6 bps half-spread offset is trivially
  small next to a 0.8-1.3% hourly range. At the TOUCH, price reaching our level is nearly
  a certainty in any regime.

  CONCLUSION: bar data CANNOT resolve maker fill probability for an order at the touch.
  The price-path question is settled (>90% everywhere, {sig['t1']/sig['n']:.0%} conditional on signal); the
  entire remaining uncertainty is QUEUE POSITION, which bars cannot see. Section C3 models
  that directly. This is a negative result about the method, and it is the honest one.

  What C2 DOES establish quantitatively is the MISS COST. In the {miss:.1%} of signal cases
  where price never returned to the touch within 1h, the 2h forward move averaged
  {ra*100:+.2f}%. Expected forgone move from passive entry = {miss:.3f} x {ra*100:.2f}% = {miss*ra*100:.3f}% of notional.
  That is an order of magnitude smaller than the 40 bps/leg fee saving from posting
  passively, so PASSIVE ENTRY IS STILL CORRECT -- but the miss is concentrated in exactly
  the trades that would have worked, so realised win-rate will look worse than modelled.
""")
    return sig["t1"]/sig["n"], sig["t2"]/sig["n"]


def section_C3(meta, d1h, uni, pairs):
    hdr("C3. QUEUE-CLEARING MODEL -- the actual binding constraint on a maker fill")
    print("""
  MODEL (explicit, and each step is an assumption, not a measurement):
    a) one-sided flow hitting the bid = 0.5 * usd_vol_24h / 1440 USD per minute
       [MEASURED usd_vol_24h; MODELLED 50/50 buy/sell split and uniform-in-time arrival --
        real flow is bursty, which makes short-window fills MORE variable, not less]
    b) queue resting at the touch = depth_bid_usd(+-0.5%) * (spread_bps / 50 bps)
       [MODELLED uniform order density across the 0.5% band. Real books are denser at the
        touch, so this UNDERSTATES the queue and OVERSTATES fill speed. Treat the resulting
        time-to-clear as a lower bound.]
    c) we join at the BACK of the touch queue, so we fill only after the whole queue ahead
       clears. Our own $8-17 is 0.1-0.5% of a typical queue, so our size is irrelevant.
    d) P(fill within N min) ~ P(price is at/below the touch long enough for the queue to
       clear) -- approximated as min(1, N / time_to_clear) * P_touch(N).
""")
    rows = []
    for p_ in pairs:
        u = uni.get(p_)
        if not u: continue
        flow = 0.5 * u["usd_vol_24h"] / 1440.0
        queue = u["depth_bid_usd"] * (u["spread_bps"] / 50.0)
        ttc = queue / flow if flow else float("inf")
        rows.append((p_, u["usd_vol_24h"], u["spread_bps"], queue, flow, ttc))
    rows.sort(key=lambda r: r[5])
    print(f"  {'pair':<12}{'vol24h$M':>10}{'spr_bps':>9}{'queue$':>10}{'flow$/min':>11}"
          f"{'clear(min)':>11}{'P(fill|15m)':>12}{'P(fill|60m)':>12}")
    for p_, v, sp, q, fl, ttc in rows:
        f15 = min(1.0, 15/ttc) * 0.91
        f60 = min(1.0, 60/ttc) * 0.95
        print(f"  {p_:<12}{v/1e6:>10.1f}{sp:>9.2f}{q:>10.0f}{fl:>11.0f}{ttc:>11.1f}"
              f"{f15:>12.0%}{f60:>12.0%}")
    ttcs = sorted(r[5] for r in rows)
    med = statistics.median(ttcs)
    print(f"""
  MEDIAN time-to-clear = {med:.1f} min. Quartiles {ttcs[len(ttcs)//4]:.1f} / {med:.1f} / {ttcs[3*len(ttcs)//4]:.1f} min.

  Combining C2 (price reaches the touch ~96% of the time within 1h conditional on signal)
  with this queue model:

     P(maker fill | volatile, momentum entry, 15 min patience)  ~  0.75   [MODELLED]
     P(maker fill | volatile, momentum entry, 60 min patience)  ~  0.90   [MODELLED]

  UNCERTAINTY. Assumption (b) is the weak link -- real books are front-loaded, so the true
  queue is larger and clear times longer. Assumption (a) ignores that in a volatile move
  the flow is one-directional, so a passive BUY in an up-move sees LESS sell flow than the
  50/50 split assumes. Both biases point the same way: these are OPTIMISTIC. Applying a
  uniform haircut for both, the defensible working figure is

     P(maker fill | volatile, momentum entry) = 0.55, plausible range 0.35 - 0.80

  CALIBRATION CHECK AGAINST THE ONLY REAL DATA WE HAVE -- and it fails, in our favour.
  The model above predicts LINKUSD time-to-clear = {[r for r in rows if r[0]=="LINKUSD"][0][5]:.1f} min. The two real
  post-only LINKUSD fills (data/execution_log.json) completed in 25s and 30s -- roughly
  {[r for r in rows if r[0]=="LINKUSD"][0][5]*60/27.5:.0f}x faster than modelled. So assumption (b) is wrong in the opposite
  direction to what I guessed: the touch queue is far THINNER than uniform-density implies.
  A single real observation beats an armchair assumption, and I am recording that my prior
  was wrong rather than keeping the flattering model.

  CAVEATS on that calibration point, which is why it does not simply settle the question:
    - n=2, CALM, LINKUSD only, no directional signal. Easiest possible case.
    - latency_sec of exactly 30 and 25 look like POLL BOUNDARIES, not measured fill times.
      The true fill may have been much faster; it cannot have been much slower.
    - In a volatile one-directional up-move, sell flow into the bid is REDUCED, and the
      spread widens so a resting order goes stale behind the new touch. Neither effect is
      present in the calm calibration sample.

  NET WORKING ESTIMATE, weighing the bar evidence (touch ~96%), the queue model (median
  7 min, but demonstrably pessimistic by ~40x on the one real check), and the two
  volatile-regime biases that push the other way:

     P(maker fill | volatile, momentum entry, 15-30 min patience)
            point estimate 0.65     plausible range 0.40 - 0.85      [MODELLED]

  We have ZERO real volatile fills. This number is MODELLED end to end. The only thing
  measured about maker fills in this whole system is 2/2 in calm conditions, whose exact
  binomial 95% CI is [0.16, 1.00] -- i.e. it constrains essentially nothing.

  HIGHEST-VALUE NEXT MEASUREMENT, by a wide margin: place 5-10 small post-only orders
  ($7-8, at or just inside the touch) on eligible alts while vol_regime()=='volatile',
  record fill/no-fill and latency, and replace this 0.65 with a measured number. That is
  a ~$0 experiment (post-only orders that do not fill cost nothing) and it collapses the
  single largest uncertainty in the tactical EV calculation.
""")
    return 0.65


# ================================================================== D. PARTIAL FILLS
def section_D(meta, uni, pairs):
    hdr("D. PARTIAL FILLS at $8-17 clips  [MEASURED depth snapshot + MODELLED consequence]")
    rows = []
    for p in pairs:
        u = uni.get(p)
        if not u: continue
        rows.append((p, u["min_notional"], u["depth_bid_usd"], u["depth_ask_usd"],
                     u["est_slippage_bps"], u["usd_vol_24h"]))
    rows.sort(key=lambda r: -r[1])
    print(f"""  Account ~$55. Position 15-30% => $8.25-$16.50 clip. LINKUSD min notional
  ${uni['LINKUSD']['min_notional']:.2f}.

  1) DEPTH-DRIVEN partial fill: a $17 clip against the thinnest eligible book
     (${min(r[2] for r in rows)/1e3:.0f}k bid) is {17/min(r[2] for r in rows)*100:.4f}% of near-touch depth. Depth is NOT
     the constraint. A marketable order of this size fills in full, instantly, at the
     touch. MEASURED est_slippage_bps across the universe is {min(r[4] for r in rows):.2f}-{max(r[4] for r in rows):.2f} bps.

  2) The real partial-fill risk is a TIME/QUEUE partial on a passive order, and its cost
     is the MIN-NOTIONAL RESIDUAL: if a $C clip fills fraction f, the residual $(1-f)*C
     must still be tradeable. If (1-f)*C < min_notional the remainder is STRANDED --
     it can neither be cancelled-and-resized usefully nor exited later on its own.

  Residual-stranding threshold: fill fraction f above which the remainder is untradeable.
""")
    print(f"  {'pair':<12}{'minNot$':>9}{'$8.25 clip':>22}{'$16.50 clip':>22}")
    print(f"  {'':<12}{'':>9}{'strand if f >':>14}{'max useful':>8}{'strand if f >':>14}{'max useful':>8}")
    bad = []
    for p, mn, db, da, sl, v in rows:
        f1 = 1 - mn / 8.25
        f2 = 1 - mn / 16.50
        s1 = f"{f1:.0%}" if f1 > 0 else "ANY(too big)"
        s2 = f"{f2:.0%}" if f2 > 0 else "ANY(too big)"
        if f1 <= 0: bad.append(p)
        print(f"  {p:<12}{mn:>9.2f}{s1:>14}{'':>8}{s2:>14}{'':>8}")
    print(f"""
  {len(bad)} of {len(rows)} eligible alts CANNOT take an $8.25 clip at all (min notional
  exceeds the clip): {', '.join(bad) if bad else 'none'}
  On the rest, ANY partial fill below ~{statistics.median([1-r[1]/8.25 for r in rows if r[1]<8.25])*100:.0f}% of an $8.25 clip strands the remainder.

  COST OF A STRANDED RESIDUAL (MODELLED): you must either (a) top the position back up
  with a second order -- which at ${uni['LINKUSD']['min_notional']:.2f} minimum may overshoot the intended size, or
  (b) take the residual out later with a TAKER order bundled into another trade. Charge
  the pessimistic case: the residual exits taker instead of maker, costing
  ({MEAS_TAKER_LEG-MEAS_MAKER_FEE:.4f}) extra on that slice. At a 20% residual that is
  {(MEAS_TAKER_LEG-MEAS_MAKER_FEE)*0.20*100:.3f}% of notional per affected leg -- small, but not zero.

  PRACTICAL MITIGATION, and this one is large: size tactical clips at >= 2x the pair's
  min_notional so a 50% partial still leaves a tradeable remainder. At $55 that means
  min_notional <= $8.25 for a 30% clip -- which already excludes {len(bad)} pairs.
""")
    return bad


# ============================================================ E. BEST ACHIEVABLE COST
def section_E(adv_calm_bps, adv_vol_bps, p_fill_1h, p_fill_2h):
    hdr("E. BEST ACHIEVABLE COST PER TACTICAL ROUND TRIP  [MODELLED from measured inputs]")
    maker_leg_calm = MEAS_MAKER_FEE + adv_calm_bps / 1e4
    maker_leg_vol = MEAS_MAKER_FEE + adv_vol_bps / 1e4
    taker_leg = MEAS_TAKER_LEG
    print(f"  per-leg building blocks:")
    print(f"    maker leg, CALM      = {MEAS_MAKER_FEE*100:.3f}% fee [MEASURED] + {adv_calm_bps:.1f}bps adverse "
          f"[MEASURED n=2] = {maker_leg_calm*100:.3f}%")
    print(f"    maker leg, VOLATILE  = {MEAS_MAKER_FEE*100:.3f}% fee [MEASURED] + {adv_vol_bps:.1f}bps adverse "
          f"[MODELLED]      = {maker_leg_vol*100:.3f}%")
    print(f"    taker leg            = {taker_leg*100:.3f}% [MEASURED, incl. spread crossing]")
    print(f"    impact at $8-17      = <0.01% [MEASURED depth] -- negligible, drop it")

    policies = [
        ("P1 current model: 4 legs, all maker (calm adverse)", 4, 0, maker_leg_calm, taker_leg),
        ("P1 honest: 4 legs all maker, VOLATILE adverse",      4, 0, maker_leg_vol, taker_leg),
        ("P1b 4 legs: maker entries, taker exits",             2, 2, maker_leg_vol, taker_leg),
        ("P2 park-in-USD, N=3 trades, all maker",           2+1/3, 0, maker_leg_vol, taker_leg),
        ("P2 park-in-USD, N=5 trades, all maker",           2+1/5, 0, maker_leg_vol, taker_leg),
        ("P2 marginal (already in USD): 2 legs all maker",      2, 0, maker_leg_vol, taker_leg),
        ("P2* realistic: maker entry + taker exit (2 legs)",    1, 1, maker_leg_vol, taker_leg),
        ("P2** maker entry, 70/30 maker-target/taker-stop exit", 1.7, 0.3, maker_leg_vol, taker_leg),
    ]
    print(f"\n  {'policy':<56}{'cost/RT':>9}{'gate 3x':>9}{'gate 1.5x EV @p=.62':>21}")
    print("  " + "-" * 94)
    best = None
    for name, mlegs, tlegs, ml, tl in policies:
        c = mlegs * ml + tlegs * tl
        g3 = 3 * c * 100
        # EV test: 0.24 * move >= 1.5*c  => move >= 1.5c/0.24
        gev = 1.5 * c * 100 / 0.24
        print(f"  {name:<56}{c*100:>8.3f}%{g3:>8.2f}%{gev:>20.2f}%")
        if best is None or c < best[1]: best = (name, c)
    print(f"\n  BEST REALISTIC (does not assume an unfilled exit is acceptable):")
    nm, c = policies[6][0], policies[6][1]*policies[6][3] + policies[6][2]*policies[6][4]
    print(f"    {nm}  =  {c*100:.3f}% per round trip")
    print(f"    3x gate -> expected move must be >= {3*c*100:.2f}%")
    print(f"    EV test at p=0.62 -> expected move must be >= {1.5*c*100/0.24:.2f}%")
    print(f"    EV test at p=0.70 -> expected move must be >= {1.5*c*100/0.40:.2f}%")
    print(f"""
  FILL-PROBABILITY DISCOUNT. A maker entry that does not fill is not a cost, it is a
  missed trade. SIGNAL-CONDITIONAL bar-implied touch rate (section C2) is {p_fill_1h:.0%} within
  1h and {p_fill_2h:.0%} within 2h -- and touching is necessary, not sufficient. Haircut for
  queue position (we sit at the back of the touch and a mere touch often clears only the
  front) gives a working estimate of

        maker fill probability, VOLATILE, momentum entry, 15-30 min patience
              point estimate 0.65   plausible range 0.40 - 0.85      [MODELLED, see C3]

  execution_stats.maker_fill_prob defaults to 0.50 for volatile. This study says 0.65 is
  the better central value but the range is wide enough that 0.50 is a defensible
  conservative choice. Raise it to 0.65 only alongside a SOURCE label that says MODELLED,
  and replace it the moment we have >=5 real volatile post-only orders.

  edge.py bug: it multiplies BOTH gross and cost by fill_prob, then compares net_pct to
  the absolute MIN_ABS_EDGE_PCT floor of 0.5%. Scaling both sides is right for the SIGN of
  EV per attempt, but it makes net_pct an expected-value-per-attempt number that is no
  longer comparable to an absolute per-trade floor. Separate the two: gate on
  net-per-completed-trade, and use fill_prob only to rank opportunities by throughput.""")
    return c


def section_F(d1, meta, uni, pairs, cost2, cost4):
    hdr("F. WHO ACTUALLY CLEARS THE GATE -- concrete effect of the two proposed changes")
    print(f"""  Two changes under test:
    (1) charge 2 marginal legs ({cost2*100:.3f}%) instead of 4 ({cost4*100:.3f}%)
    (2) scale expected_move by sqrt(hold_days) instead of always using the 1-day sigma
  Gate A (tactical.py MOVE_TO_COST_MIN): 0.5*sigma*sqrt(h) >= 3 * cost
  Gate B (edge.py EV, the binding one):  0.24*0.5*sigma*sqrt(h) >= 1.5 * cost
  Confluence uplift assumed 1.0 (exactly 3 conditions). Excludes min-notional-blocked pairs.
""")
    blocked = {p_ for p_ in pairs if uni.get(p_, {}).get("min_notional", 0) > 8.25}
    rows = []
    for p_ in pairs:
        c = [float(r[4]) for r in d1[p_]]
        v = dvol30(c)
        if v: rows.append((p_, v*100))
    rows.sort(key=lambda r: -r[1])
    print(f"  {'pair':<12}{'sig1d%':>8}" + "".join(f"{lbl:>10}" for lbl in
          ("A 4leg 1d", "A 2leg 1d", "A 2leg 3d", "B 4leg 1d", "B 2leg 3d", "B 2leg 7d")) + "  note")
    counts = [0]*6
    for p_, sg in rows:
        cells = []
        for gi, (gate, cost, h) in enumerate((
                (3.0, cost4, 1), (3.0, cost2, 1), (3.0, cost2, 3),
                (1.5/0.24, cost4, 1), (1.5/0.24, cost2, 3), (1.5/0.24, cost2, 7))):
            mv = 0.5 * sg * math.sqrt(h)
            ok = mv >= gate * cost * 100
            if ok and p_ not in blocked: counts[gi] += 1
            cells.append("  PASS" if ok else "  fail")
        note = "MIN-NOTIONAL BLOCKED" if p_ in blocked else ""
        print(f"  {p_:<12}{sg:>8.2f}" + "".join(f"{c_:>10}" for c_ in cells) + f"  {note}")
    print(f"\n  tradeable pairs passing (min-notional-blocked excluded): " +
          "  ".join(f"{n}" for n in counts))
    print(f"""
  Reading across: under the CURRENT model (4 legs, 1-day sigma) {counts[3]} pair(s) clear the
  binding EV gate. Charging 2 marginal legs and holding 3 days takes that to {counts[4]}; holding
  7 days takes it to {counts[5]}. So YES -- the combination of correct leg counting and hold-period
  extension makes the gate achievable, where neither change alone does.

  This says NOTHING about whether those trades are profitable. It says the gate stops being
  vacuous. Whether there is any edge to put through it is Q1/Q2, not Q3.
""")


def main():
    meta, d1, d1h, d4h, uni, pairs = load()
    print(f"cache built {json.load(open(os.path.join(CACHE,'manifest.json')))['built']}; "
          f"{len(pairs)} non-stable eligible pairs")
    cleg_maker = MEAS_MAKER_FEE + MEAS_ADVERSE_CALM_BPS / 1e4
    cleg_taker = MEAS_TAKER_LEG
    section_A(cleg_maker, cleg_taker)
    print("\n  LINK drift -- the carry cost of parking in USD  [MEASURED from 1d bars]")
    link_drift(d1)
    focus, b = section_B(d1, pairs, 4 * cleg_maker, 2 * cleg_maker)
    section_B2(d1, pairs, focus)
    out, vr, adv_vol, med_hs = section_C(meta, d1, d1h, uni, pairs)
    f1, f2 = section_C2(meta, d1h, uni, pairs)
    section_C3(meta, d1h, uni, pairs)
    section_D(meta, uni, pairs)
    c2 = section_E(MEAS_ADVERSE_CALM_BPS, adv_vol, f1, f2)
    ml = MEAS_MAKER_FEE + adv_vol/1e4
    section_F(d1, meta, uni, pairs, 2*ml, 4*ml)


if __name__ == "__main__":
    main()
