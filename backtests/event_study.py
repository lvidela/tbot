"""Event study: do the monitor's own detectors precede tradeable moves?

For each trigger type, find historical occurrences across the eligible universe and
measure the forward return distribution. This is the test that matters for aggressive
opportunistic mode: the triggers are only worth acting on if they carry information.
"""
import json, os, sys, statistics
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import kraken

COST = 1.69  # % round trip, measured

u = json.load(open("data/universe.json"))
pairs = [c["pair"] for c in u["eligible"] if not c["is_stable"] and c["pair"] not in ("EURUSD","GBPUSD","PAXGUSD")]
S = {}
for p in pairs:
    try:
        d = kraken.public("OHLC", pair=p, interval=1440)
        k = [x for x in d if x != "last"][0]
        S[p] = [(int(r[0]), float(r[2]), float(r[3]), float(r[4]), float(r[6])) for r in d[k]]
    except Exception: pass
print(f"{len(S)} assets\n")

def stats(name, fwd):
    if len(fwd) < 20:
        print(f"{name:<34} n={len(fwd):<5} (too few)"); return
    m = statistics.mean(fwd); sd = statistics.pstdev(fwd); se = sd/len(fwd)**0.5
    t = m/se if se else 0
    win = sum(1 for x in fwd if x > COST)/len(fwd)*100
    flag = ""
    if t > 2 and m > COST: flag = "  <== TRADEABLE"
    elif abs(t) > 2: flag = "  <== significant"
    print(f"{name:<34} n={len(fwd):<5} mean={m:+6.2f}%  t={t:+5.2f}  median={statistics.median(fwd):+6.2f}%  "
          f"P(>cost)={win:4.1f}%{flag}")

for horizon in (3, 7):
    print(f"=== forward {horizon}d return after each trigger (cost hurdle {COST}%) ===")
    base = []
    for p, rows in S.items():
        for i in range(60, len(rows)-horizon):
            base.append((rows[i+horizon][3]/rows[i][3]-1)*100)
    stats(f"[baseline] any day", base)

    for trig in ("breakout","breakdown","vol_expansion","volume_spike"):
        fwd = []
        for p, rows in S.items():
            closes = [r[3] for r in rows]
            vols   = [r[4]*r[3] for r in rows]
            for i in range(60, len(rows)-horizon):
                w = closes[i-30:i]; c = closes[i]
                rng = max(w)-min(w)
                if rng <= 0: continue
                pos = (c-min(w))/rng
                rets = [(closes[j]/closes[j-1]-1) for j in range(i-30,i)]
                v30 = statistics.pstdev(rets) if len(rets)>2 else 0
                v1 = abs(closes[i]/closes[i-1]-1)
                q30 = statistics.mean(vols[i-30:i]) if i>=30 else 0
                hit = False
                if trig=="breakout" and pos>=1.0 and rng/c>=0.03: hit=True
                if trig=="breakdown" and pos<=0.0 and rng/c>=0.03: hit=True
                if trig=="vol_expansion" and v30>0 and v1/v30>=2.5: hit=True
                if trig=="volume_spike" and q30>0 and vols[i]/q30>=3.0: hit=True
                if hit: fwd.append((closes[i+horizon]/c-1)*100)
        stats(trig, fwd)
    print()
