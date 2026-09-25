"""DECISIVE CONTROL: does the trailing stop ADD anything over naked buy-and-hold?

The previous run showed t>2 at wide trails. Before believing it, three controls:
  C1. Same entries, NO stop (pure buy-and-hold of the same asset over the same window).
      If the stop adds nothing, the "edge" is just beta in a bullish sample.
  C2. RANDOM entry days on the same assets -- if random entries score the same, the
      "setup" contributes nothing and we are measuring the asset class, not a signal.
  C3. Asset selection WITHOUT look-ahead: pick the volatile basket using only data
      available BEFORE each entry, not end-of-sample volatility.
"""
import json, os, statistics, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = json.load(open(os.path.join(ROOT,"data","cache","meta.json")))
H1 = json.load(open(os.path.join(ROOT,"data","cache","ohlc_1h.json")))
COST, STOP_SLIP = 0.92, 0.35
random.seed(11)
pairs=[p for p in H1 if not META.get(p,{}).get("is_stable") and p not in ("EURUSD","GBPUSD","PAXGUSD")]
B={p:[(r[0],r[2],r[3],r[4]) for r in H1[p]] for p in pairs}   # t,h,l,c

def vol_before(p,i,look=168):
    b=B[p]; lo=max(1,i-look)
    r=[(b[j][3]/b[j-1][3]-1) for j in range(lo,i)]
    return statistics.pstdev(r) if len(r)>30 else 0

def run(p,i,trail,hz,use_stop=True):
    b=B[p]
    if i+hz>=len(b): return None
    e=b[i][3]; peak=e; stop=e*(1-trail/100)
    for j in range(i+1,i+1+hz):
        _,hi,lo,c=b[j]
        if use_stop and lo<=stop: return (stop/e-1)*100-STOP_SLIP
        if hi>peak: peak=hi; stop=peak*(1-trail/100)
    return (b[i+hz][3]/e-1)*100

def stats(v,step):
    ms,ts=[],[]
    for ph in range(max(step,1)):
        s=v[ph::max(step,1)]
        if len(s)<8: continue
        m=statistics.mean(s); se=statistics.pstdev(s)/len(s)**0.5
        ms.append(m); ts.append(m/se if se else 0)
    return (statistics.mean(ms),statistics.mean(ts)) if ms else (None,None)

print(f"{'trail':>6}{'hz':>5} | {'WITH stop':>22} | {'NO stop (control C1)':>22} | {'stop adds':>10}")
print(f"{'':>11} | {'net':>8}{'t':>7}{'win%':>7} | {'net':>8}{'t':>7}{'win%':>7} | {'delta':>10}")
for trail in (5,8,12):
    for hz in (24,72):
        withs, without = [], []
        for p in pairs:
            b=B[p]; step=hz   # NON-overlapping entries
            for i in range(200, len(b)-hz-1, step):
                if vol_before(p,i) < 0.008: continue      # C3: no look-ahead selection
                a=run(p,i,trail,hz,True); c_=run(p,i,trail,hz,False)
                if a is not None and c_ is not None:
                    withs.append(a-COST); without.append(c_-COST)
        if len(withs)<40: continue
        m1,t1=stats(withs,1); m2,t2=stats(without,1)
        w1=sum(1 for x in withs if x>0)/len(withs)*100
        w2=sum(1 for x in without if x>0)/len(without)*100
        print(f"{trail:>6}{hz:>5} | {m1:>+8.2f}{t1:>+7.2f}{w1:>6.0f}% | {m2:>+8.2f}{t2:>+7.2f}{w2:>6.0f}% | {m1-m2:>+10.2f}")

print("\n=== C2: random entries, same assets, trail=8 hz=72 ===")
for label, filt in (("vol-filtered entries", True), ("RANDOM entries", False)):
    v=[]
    for p in pairs:
        b=B[p]
        for i in range(200, len(b)-73, 72):
            if filt and vol_before(p,i) < 0.008: continue
            idx = i if filt else random.randrange(200, len(b)-73)
            r=run(p,idx,8,72,True)
            if r is not None: v.append(r-COST)
    if v:
        m,t=stats(v,1)
        print(f"  {label:<22} n={len(v):<5} net {m:+.2f}%  t={t:+.2f}")
