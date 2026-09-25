"""THE decision that actually matters: hold LINK, or move to USD, for the final 21 days?

The adversarial review (Q4 finding 2) caught a real inconsistency: I priced LINK's
volatility drag at 1.46% to reject diversification, then justified holding LINK on a
+0.117%/day in-sample drift -- the exact kind of estimate I reject as noise everywhere
else. Either drag is decision-relevant (and cash, which has none, wins) or it is not
(and the diversification rejection was void). Both cannot stand.

Resolution: stop modelling drag separately. Realised returns ALREADY include it. Measure
LINK's empirical 21-day forward return distribution directly, with honest error bars, and
compare against cash minus the one-way switch cost.
"""
import json, os, statistics, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
c = json.load(open(os.path.join(ROOT, "data", "cache", "ohlc_1d.json")))
closes = [r[4] for r in c["LINKUSD"]]
H = 21
SWITCH_COST = 0.81      # one-way maker out of LINK into USD, incl. adverse selection (2 legs worth
                        # if we ever come back; 0.40 one-way if we simply stay in cash to the end)

fwd = [(closes[i+H]/closes[i]-1)*100 for i in range(len(closes)-H)]
n = len(fwd)
mean = statistics.mean(fwd); med = statistics.median(fwd)
print(f"LINK {H}-day forward returns, n={n} overlapping windows ({len(closes)} daily bars)")
print(f"  mean {mean:+.2f}%   median {med:+.2f}%   share positive {sum(1 for x in fwd if x>0)/n:.0%}")
s = sorted(fwd)
print(f"  p05 {s[n//20]:+.1f}%  p25 {s[n//4]:+.1f}%  p75 {s[3*n//4]:+.1f}%  p95 {s[19*n//20]:+.1f}%")

# Overlapping windows are ~H-fold pseudo-replicated. Use non-overlapping blocks AND a
# moving-block bootstrap for an honest standard error.
nonov = [fwd[i] for i in range(0, len(fwd), H)]
se_nonov = statistics.pstdev(nonov)/len(nonov)**0.5
print(f"\n  non-overlapping windows: n={len(nonov)}  mean {statistics.mean(nonov):+.2f}%  se {se_nonov:.2f}  "
      f"t={statistics.mean(nonov)/se_nonov:+.2f}")

random.seed(7)
boots = []
nb = max(1, len(fwd)//H)
for _ in range(5000):
    samp = []
    for _ in range(nb):
        st = random.randrange(0, len(fwd)-H) if len(fwd) > H else 0
        samp.extend(fwd[st:st+H])
    boots.append(statistics.mean(samp))
boots.sort()
lo, hi = boots[int(.025*len(boots))], boots[int(.975*len(boots))]
print(f"  moving-block bootstrap 95% CI for the mean: [{lo:+.2f}%, {hi:+.2f}%]")

print(f"\n=== DECISION ===")
print(f"  hold LINK 21d : expected {mean:+.2f}%  (95% CI [{lo:+.2f}, {hi:+.2f}])")
print(f"  move to USD   : 0.00% minus one-way switch cost {SWITCH_COST:.2f}% = {-SWITCH_COST:+.2f}%")
print(f"  difference    : {mean+SWITCH_COST:+.2f}% in favour of {'LINK' if mean+SWITCH_COST>0 else 'CASH'}")
print(f"  CI contains zero: {lo < 0 < hi}   CI contains -{SWITCH_COST}: {lo < -SWITCH_COST < hi}")
straddles = lo < -SWITCH_COST
print(f"\n  Is the LINK-vs-cash decision statistically resolvable? {'NO' if straddles else 'YES'}")
print(f"  Median outcome favours: {'LINK' if med > -SWITCH_COST else 'CASH'} ({med:+.2f}% vs {-SWITCH_COST:+.2f}%)")
