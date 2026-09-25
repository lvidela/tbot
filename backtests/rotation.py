"""Backtest cross-sectional momentum / relative-strength rotation vs. buy-and-hold.

Realistic costs: 0.80% taker each side, plus each pair's measured spread.
A rotation (sell A, buy B) therefore costs ~1.6% + spreads.

Reports the FULL parameter grid, not just the best cell, so overfitting is visible.
"""
import json, os, sys, statistics, itertools
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import kraken

TAKER = 0.0080

def load(pairs, interval=1440):
    out = {}
    for p in pairs:
        try:
            d = kraken.public("OHLC", pair=p, interval=interval)
            k = [x for x in d if x != "last"][0]
            out[p] = {int(r[0]): float(r[4]) for r in d[k]}
        except Exception as e:
            print("  skip", p, e)
    return out

def run(series, spreads, lookback, hold_days, topk, start_idx=60):
    times = sorted(set.intersection(*[set(s) for s in series.values()]))
    pairs = sorted(series)
    if len(times) < start_idx + 30: return None
    cash, holding, ntrades, fees = 1.0, None, 0, 0.0
    equity=[]
    i = start_idx
    while i < len(times):
        t = times[i]
        # rank by trailing return
        scores = {}
        for p in pairs:
            t0 = times[i - lookback]
            if t0 in series[p] and t in series[p] and series[p][t0] > 0:
                scores[p] = series[p][t] / series[p][t0] - 1
        if scores:
            target = sorted(scores, key=lambda p: -scores[p])[:topk]
        else:
            target = []
        # rebalance
        if set(target) != set(holding or []):
            if holding:
                for p in holding:
                    c = TAKER + spreads.get(p, 0.0005)
                    cash *= (1 - c/len(holding))*0 + 1  # cost applied below per-leg
                # simpler: apply cost on full notional turned over
            # BUGFIX 2026-09-24 (found by adversarial review Q4): the symmetric difference
            # counts BOTH the exited and the entered name, so dividing by len(target)
            # double-counts. Swapping 1 of 3 names read as 1.33 turnover instead of 0.33 --
            # a 4x fee overstatement. This inflated costs in 24 of 36 grid cells and pushed
            # the result toward the "rotation loses" conclusion I then reported.
            if holding is None:
                turn = 1.0
            else:
                entered = len(set(target) - set(holding))
                turn = entered / max(len(target) or 1, 1)
            turn = min(turn, 1.0)
            cost = turn * (TAKER*2 + statistics.mean([spreads.get(p,0.0005) for p in (target or pairs)])*2)
            if holding is None: cost = turn*(TAKER + statistics.mean([spreads.get(p,0.0005) for p in (target or pairs)]))
            cash *= (1-cost); fees += cost; ntrades += 1
            holding = target
        # hold for hold_days
        j = min(i+hold_days, len(times)-1)
        if holding:
            r = statistics.mean([series[p][times[j]]/series[p][t]-1 for p in holding if times[j] in series[p] and t in series[p]])
            cash *= (1+r)
        equity.append(cash)
        i = j if j>i else i+1
    dd = 0.0; peak=equity[0] if equity else 1
    for e in equity:
        peak=max(peak,e); dd=min(dd,e/peak-1)
    return dict(final=cash, ntrades=ntrades, fees=fees, maxdd=dd)

if __name__ == "__main__":
    u = json.load(open("data/universe.json"))
    pairs = [c["pair"] for c in u["eligible"] if not c["is_stable"] and c["pair"] not in ("EURUSD","GBPUSD")]
    spreads = {c["pair"]: c["spread_bps"]/1e4 for c in u["eligible"]}
    print(f"loading {len(pairs)} pairs...")
    series = load(pairs)
    common = set.intersection(*[set(s) for s in series.values()])
    print(f"{len(series)} pairs, {len(common)} common daily bars\n")

    # buy and hold baselines
    times = sorted(common)
    print("=== buy & hold over the common window ===")
    bh={}
    for p in sorted(series):
        r = series[p][times[-1]]/series[p][times[60]]-1
        bh[p]=r
    for p,r in sorted(bh.items(), key=lambda x:-x[1])[:5]: print(f"  best  {p:<12}{r*100:+9.1f}%")
    print(f"  LINKUSD{'':<6}{bh.get('LINKUSD',0)*100:+9.1f}%   <- benchmark asset")
    print(f"  median{'':<7}{statistics.median(bh.values())*100:+9.1f}%")

    print("\n=== rotation grid (final multiple of capital; 1.00 = flat) ===")
    print(f"{'lookback':>9}{'hold':>6}{'topk':>6}{'final':>9}{'trades':>8}{'fees':>8}{'maxDD':>8}")
    results=[]
    for lb, hd, tk in itertools.product((7,14,30,60),(3,7,14),(1,2,3)):
        r = run(series, spreads, lb, hd, tk)
        if not r: continue
        results.append((lb,hd,tk,r))
        print(f"{lb:>9}{hd:>6}{tk:>6}{r['final']:>9.3f}{r['ntrades']:>8}{r['fees']*100:>7.0f}%{r['maxdd']*100:>7.0f}%")
    fins=[r['final'] for *_ ,r in results]
    hold_link = 1+bh.get('LINKUSD',0)
    print(f"\ngrid median final = {statistics.median(fins):.3f}   best = {max(fins):.3f}   worst = {min(fins):.3f}")
    print(f"hold-LINK over same window = {hold_link:.3f}")
    print(f"cells beating hold-LINK: {sum(1 for f in fins if f>hold_link)}/{len(fins)}")
