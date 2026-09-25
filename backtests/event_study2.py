"""Rigorous version: is the trigger predictive RELATIVE TO THE MARKET, with honest errors?

Fixes three flaws in the naive study:
  1. Cross-sectional demeaning -- subtract the same-day equal-weight universe return,
     so we measure selection skill, not "the whole market went up that day".
  2. Date clustering -- all events on one day collapse to ONE observation, because
     32 correlated assets firing together is not 32 independent samples.
  3. Report median and P(win) alongside the mean, since a right-skewed mean can be
     driven by a handful of outliers you would never reliably catch.
"""
import json, os, sys, statistics
from collections import defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import kraken

COST = 1.69
u = json.load(open("data/universe.json"))
pairs = [c["pair"] for c in u["eligible"] if not c["is_stable"] and c["pair"] not in ("EURUSD","GBPUSD","PAXGUSD")]
S = {}
for p in pairs:
    try:
        d = kraken.public("OHLC", pair=p, interval=1440)
        k = [x for x in d if x != "last"][0]
        S[p] = {int(r[0]): (float(r[4]), float(r[6])*float(r[4])) for r in d[k]}
    except Exception: pass
times = sorted(set.intersection(*[set(v) for v in S.values()]))
print(f"{len(S)} assets, {len(times)} common bars\n")

def fwd_ret(p, i, h):
    if i+h >= len(times): return None
    a, b = S[p].get(times[i]), S[p].get(times[i+h])
    return (b[0]/a[0]-1)*100 if a and b else None

for h in (3, 7):
    # same-day universe mean forward return, for demeaning
    mkt = {}
    for i in range(len(times)-h):
        rs = [fwd_ret(p,i,h) for p in S]
        rs = [x for x in rs if x is not None]
        if rs: mkt[i] = statistics.mean(rs)

    print(f"=== forward {h}d EXCESS return vs same-day universe (cost hurdle {COST}%) ===")
    print(f"{'trigger':<16}{'events':>8}{'days':>7}{'mean_exc':>10}{'t(clustered)':>14}{'median':>9}{'P(>cost)':>10}")
    for trig in ("breakout","breakdown","vol_expansion","volume_spike"):
        by_day = defaultdict(list); nev=0
        for p in S:
            cl=[S[p][t][0] for t in times]; vo=[S[p][t][1] for t in times]
            for i in range(60, len(times)-h):
                w=cl[i-30:i]; c=cl[i]; rng=max(w)-min(w)
                if rng<=0: continue
                pos=(c-min(w))/rng
                rets=[(cl[j]/cl[j-1]-1) for j in range(i-30,i)]
                v30=statistics.pstdev(rets); v1=abs(cl[i]/cl[i-1]-1)
                q30=statistics.mean(vo[i-30:i])
                hit=((trig=="breakout" and pos>=1.0 and rng/c>=0.03) or
                     (trig=="breakdown" and pos<=0.0 and rng/c>=0.03) or
                     (trig=="vol_expansion" and v30>0 and v1/v30>=2.5) or
                     (trig=="volume_spike" and q30>0 and vo[i]/q30>=3.0))
                if not hit: continue
                r=fwd_ret(p,i,h)
                if r is None or i not in mkt: continue
                by_day[i].append(r-mkt[i]); nev+=1
        if len(by_day)<10:
            print(f"{trig:<16}{nev:>8}{len(by_day):>7}   too few clusters"); continue
        day_means=[statistics.mean(v) for v in by_day.values()]
        allx=[x for v in by_day.values() for x in v]
        m=statistics.mean(day_means); sd=statistics.pstdev(day_means); n=len(day_means)
        t=m/(sd/n**0.5) if sd else 0
        win=sum(1 for x in allx if x>COST)/len(allx)*100
        flag="  <== TRADEABLE" if (t>2 and m>COST) else ("  <== significant" if abs(t)>2 else "")
        print(f"{trig:<16}{nev:>8}{n:>7}{m:>+10.2f}%{t:>+14.2f}{statistics.median(allx):>+9.2f}%{win:>9.1f}%{flag}")
    print()
