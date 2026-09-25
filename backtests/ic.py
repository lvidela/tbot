"""Information-coefficient test: does trailing return predict forward return?

Spearman rank correlation between each asset's trailing-N-day return and its
subsequent forward-M-day return, pooled across the eligible universe.
This is the parameter-free way to ask whether momentum/reversal carries signal,
without a strategy wrapper that can be tuned until something looks good.
"""
import json, os, sys, statistics
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import kraken

def rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0]*len(xs)
    for pos, i in enumerate(order): r[i] = pos
    return r

def spearman(a, b):
    ra, rb = rank(a), rank(b)
    n = len(a)
    if n < 3: return 0.0
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((ra[i]-ma)*(rb[i]-mb) for i in range(n))
    da = sum((x-ma)**2 for x in ra)**0.5
    db = sum((x-mb)**2 for x in rb)**0.5
    return num/(da*db) if da*db else 0.0

u = json.load(open("data/universe.json"))
pairs = [c["pair"] for c in u["eligible"] if not c["is_stable"] and c["pair"] not in ("EURUSD","GBPUSD")]
series = {}
for p in pairs:
    try:
        d = kraken.public("OHLC", pair=p, interval=1440)
        k = [x for x in d if x != "last"][0]
        series[p] = {int(r[0]): float(r[4]) for r in d[k]}
    except Exception: pass
times = sorted(set.intersection(*[set(s) for s in series.values()]))
print(f"{len(series)} assets, {len(times)} common daily bars\n")

print("Spearman IC: trailing return (lookback) vs forward return (horizon)")
print(f"{'lookback':>9}{'horizon':>9}{'mean IC':>10}{'t-stat':>9}{'n obs':>8}   verdict")
for lb in (7,14,30,60):
    for fw in (7,14,21):
        ics=[]
        for i in range(lb, len(times)-fw):
            t0,t,t1 = times[i-lb], times[i], times[i+fw]
            trail, fwd = [], []
            for p in series:
                if t0 in series[p] and t in series[p] and t1 in series[p]:
                    trail.append(series[p][t]/series[p][t0]-1)
                    fwd.append(series[p][t1]/series[p][t]-1)
            if len(trail)>=8: ics.append(spearman(trail,fwd))
        if not ics: continue
        m=statistics.mean(ics); sd=statistics.pstdev(ics)
        # observations overlap heavily; deflate n by the forward horizon
        neff=max(1,len(ics)//fw)
        t_stat=m/(sd/neff**0.5) if sd else 0
        v = "momentum" if t_stat>2 else "reversal" if t_stat<-2 else "NO SIGNAL"
        print(f"{lb:>9}{fw:>9}{m:>+10.4f}{t_stat:>+9.2f}{neff:>8}   {v}")
