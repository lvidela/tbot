"""Repeated triangular snapshots -- does a dislocation EVER reach the 120bps hurdle?
A single snapshot can miss transients, so sample over time and keep the running max."""
import json, os, sys, time, statistics
sys.path.insert(0,"/home/lisandro/scripts"); import kraken
ROOT="/home/lisandro"
tri=json.load(open(f"{ROOT}/research/micro_arb/triangles.json"))
ap=kraken.public("AssetPairs"); alt2key={}
for k,v in ap.items(): alt2key.setdefault(v["altname"],k)
out=[]
N=int(sys.argv[1]) if len(sys.argv)>1 else 30
for n in range(N):
    try:
        tk=kraken.public("Ticker")
    except Exception as e:
        time.sleep(10); continue
    def q(alt):
        k=alt2key.get(alt)
        if not k or k not in tk: return None
        t=tk[k]
        try:
            b,a=float(t["b"][0]),float(t["a"][0])
            return (b,a) if b>0 and a>=b else None
        except Exception: return None
    best=-9e9; bestname=None
    for legA,legB,legC,base,qq in tri:
        A,B,C=q(legA),q(legB),q(legC)
        if not(A and B and C): continue
        f=((1.0/A[1])*B[0]*C[0]-1)*100
        r=((1.0/C[1])/B[1]*A[0]-1)*100
        m=max(f,r)
        if m>best: best,bestname=m,f"{base}/{qq}"
    out.append(dict(ts=time.strftime("%H:%M:%SZ",time.gmtime()), best=best, tri=bestname))
    print(f"  sample {n+1:>3}/{N} {out[-1]['ts']} best gross {best:+.4f}% ({bestname})", flush=True)
    time.sleep(18)
json.dump(out, open(f"{ROOT}/research/micro_arb/tri_timeseries.json","w"), indent=1)
b=[x["best"] for x in out]
print(f"\nover {len(b)} snapshots: max {max(b):+.4f}%  mean {statistics.mean(b):+.4f}%")
print(f"snapshots clearing the 1.20% all-maker hurdle: {sum(1 for x in b if x>1.20)}/{len(b)}")
