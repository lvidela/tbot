"""THE session's key hypothesis: can an ASYMMETRIC PAYOFF be +EV at p = 0.50?

Every EV model so far assumed I needed a directional edge (p > 0.5). A trailing stop
changes the PAYOFF SHAPE: downside capped at the trail, upside runs with the peak. At
p = 0.50 that is still +EV if mean win > mean loss.

Q2 calibration found mean MFE +16.6% vs mean MAE -7.1% (ratio 2.33) on confluence setups.
A trailing stop is the instrument that monetises exactly that asymmetry -- and Kraken
accepts it exchange-side, attached at entry (verified today via validate=true).

ADVERSARIAL CONTROL THAT MATTERS MOST: with OHLC bars I cannot see the intrabar path, so
I cannot know whether the low preceded the high. I therefore simulate on 1h bars (finer
path) and report BOTH orderings as a bracket:
  - PESSIMISTIC: within each bar, assume the low happens first (stop hit before any gain)
  - OPTIMISTIC:  assume the high happens first
The honest result is the pessimistic one. If the edge only exists optimistically, it is
a path artefact, not an edge.
"""
import json, os, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = json.load(open(os.path.join(ROOT, "data", "cache", "meta.json")))
H1 = json.load(open(os.path.join(ROOT, "data", "cache", "ohlc_1h.json")))
D1 = json.load(open(os.path.join(ROOT, "data", "cache", "ohlc_1d.json")))
COST = 0.92          # 2 maker legs incl. adverse selection
STOP_SLIP = 0.35     # stop-loss triggers become MARKET orders: taker 0.80% is already in
                     # COST for the exit leg... charge extra slippage for gapping through.

pairs = [p for p in H1 if not META.get(p, {}).get("is_stable")
         and p not in ("EURUSD", "GBPUSD", "PAXGUSD")]

def bars(p):
    return [(r[0], r[1], r[2], r[3], r[4]) for r in H1[p]]   # t,o,h,l,c

def simulate(p, start_idx, trail_pct, horizon_bars, pessimistic=True):
    b = bars(p)
    if start_idx + horizon_bars >= len(b): return None
    entry = b[start_idx][4]
    peak = entry
    stop = entry * (1 - trail_pct/100)
    for j in range(start_idx+1, start_idx+1+horizon_bars):
        _, o, hi, lo, c = b[j]
        if pessimistic:
            if lo <= stop: return (stop/entry - 1)*100 - STOP_SLIP
            if hi > peak:
                peak = hi; stop = peak * (1 - trail_pct/100)
        else:
            if hi > peak:
                peak = hi; stop = peak * (1 - trail_pct/100)
            if lo <= stop: return (stop/entry - 1)*100 - STOP_SLIP
    return (b[start_idx+horizon_bars][4]/entry - 1)*100

def phase_stats(vals, step):
    ms, ts = [], []
    for ph in range(step):
        sub = vals[ph::step]
        if len(sub) < 8: continue
        m = statistics.mean(sub); se = statistics.pstdev(sub)/len(sub)**0.5
        ms.append(m); ts.append(m/se if se else 0)
    if not ms: return None, None, 0
    return statistics.mean(ms), statistics.mean(ts), len(vals)//step

# entry universe: high-volatility liquid alts (where several-percent moves are plausible)
d_series = {p: [r[4] for r in D1[p]] for p in pairs if p in D1}
vols = {}
for p, c in d_series.items():
    r = [(c[i]/c[i-1]-1) for i in range(1, len(c))]
    if len(r) > 60: vols[p] = statistics.pstdev(r[-60:])
top = sorted(vols, key=lambda p: -vols[p])[:12]
print(f"12 most volatile eligible alts: {', '.join(top)}")
print(f"cost model: {COST}% round trip + {STOP_SLIP}% stop slippage\n")

print(f"{'trail%':>7}{'horiz_h':>9}{'n':>6}{'mean_gross':>12}{'mean_net':>10}{'median':>9}"
      f"{'win%':>7}{'t_nonov':>9}  verdict")
for trail in (3, 5, 8, 12):
    for hz in (24, 72, 168):
        pess, opt = [], []
        for p in top:
            b = bars(p)
            step = max(hz//4, 6)
            for i in range(50, len(b)-hz-1, step):
                r1 = simulate(p, i, trail, hz, pessimistic=True)
                r2 = simulate(p, i, trail, hz, pessimistic=False)
                if r1 is not None: pess.append(r1)
                if r2 is not None: opt.append(r2)
        if len(pess) < 40: continue
        net = [x - COST for x in pess]
        m, t, neff = phase_stats(net, max(hz//24, 1))
        if m is None: continue
        wins = [x for x in net if x > 0]
        mw = statistics.mean(wins) if wins else 0
        ml = statistics.mean([x for x in net if x <= 0]) or 0
        verdict = "ASYMMETRY HOLDS" if m > 0 and abs(t) > 2 else ("positive but weak" if m > 0 else "negative")
        print(f"{trail:>7}{hz:>9}{len(pess):>6}{statistics.mean(pess):>+12.2f}{m:>+10.2f}"
              f"{statistics.median(net):>+9.2f}{len(wins)/len(net)*100:>6.0f}%{t:>+9.2f}  {verdict}")
        if trail == 5 and hz == 72:
            print(f"         -> win/loss asymmetry: mean win {mw:+.2f}% vs mean loss {ml:+.2f}% "
                  f"(ratio {abs(mw/ml) if ml else 0:.2f}), optimistic-path mean {statistics.mean(opt)-COST:+.2f}%")
