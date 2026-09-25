"""Test the hypothesis my own data pointed at and I never ran: REVERSAL (bottom-k).

Q4 (adversarial) finding: 11 of 12 IC cells were NEGATIVE and monotone in lookback --
that is a mild reversal signature -- yet rotation.py sorted descending only. I tested
momentum, concluded "no edge", and never ran the complement the numbers indicated.
This is the D5 error (absence of evidence reported as evidence of absence) in its most
concrete form.

Methodology matches Q1: cross-sectional demeaning, date clustering, MDE reported,
costs charged, and the multiple-testing burden stated.
"""
import json, os, statistics, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = json.load(open(os.path.join(ROOT, "data", "cache", "ohlc_1d.json")))
META = json.load(open(os.path.join(ROOT, "data", "cache", "meta.json")))
COST_2LEG = 0.92      # corrected per Q3

pairs = [p for p in C if not META.get(p, {}).get("is_stable")
         and p not in ("EURUSD", "GBPUSD", "PAXGUSD")]
series = {p: {r[0]: r[4] for r in C[p]} for p in pairs}
times = sorted(set.intersection(*[set(v) for v in series.values()]))
print(f"{len(pairs)} assets, {len(times)} common daily bars\n")


def study(lookback, horizon, k, direction):
    """direction: -1 = buy the WORST performers (reversal), +1 = buy the best (momentum)."""
    by_day = []
    for i in range(lookback, len(times) - horizon):
        t0, t, t1 = times[i - lookback], times[i], times[i + horizon]
        trail, fwd = {}, {}
        for p in pairs:
            if t0 in series[p] and t in series[p] and t1 in series[p] and series[p][t0] > 0:
                trail[p] = series[p][t] / series[p][t0] - 1
                fwd[p] = (series[p][t1] / series[p][t] - 1) * 100
        if len(trail) < 10:
            continue
        mkt = statistics.mean(fwd.values())                      # cross-sectional demean
        sel = sorted(trail, key=lambda p: direction * -trail[p])[:k]
        by_day.append(statistics.mean(fwd[p] - mkt for p in sel))
    if len(by_day) < 15:
        return None
    m = statistics.mean(by_day); sd = statistics.pstdev(by_day); n = len(by_day)
    se = sd / n ** 0.5
    return dict(mean=m, t=m / se if se else 0, n=n, median=statistics.median(by_day),
                mde=2.8 * se, net=m - COST_2LEG,
                winrate=sum(1 for x in by_day if x > COST_2LEG) / n)


print(f"{'dir':<10}{'lb':>4}{'fw':>4}{'k':>3}{'n_days':>8}{'mean_exc':>10}{'median':>9}{'t':>7}{'MDE':>7}{'net':>8}{'P(>cost)':>10}")
rows = []
for direction, name in ((-1, "REVERSAL"), (+1, "momentum")):
    for lb in (7, 14, 30):
        for fw in (3, 7, 14):
            for k in (1, 3):
                r = study(lb, fw, k, direction)
                if not r: continue
                rows.append((name, lb, fw, k, r))
                print(f"{name:<10}{lb:>4}{fw:>4}{k:>3}{r['n']:>8}{r['mean']:>+10.2f}{r['median']:>+9.2f}"
                      f"{r['t']:>+7.2f}{r['mde']:>7.2f}{r['net']:>+8.2f}{r['winrate']:>9.0%}")

n_tests = len(rows)
print(f"\nmultiple testing: {n_tests} cells -> Bonferroni |t| threshold ~ {2.8 + 0.5:.2f} (approx 0.05/{n_tests})")
rev = [r for r in rows if r[0] == "REVERSAL"]
mom = [r for r in rows if r[0] == "momentum"]
print(f"REVERSAL cells with positive NET: {sum(1 for _,_,_,_,r in rev if r['net']>0)}/{len(rev)}")
print(f"momentum cells with positive NET: {sum(1 for _,_,_,_,r in mom if r['net']>0)}/{len(mom)}")
best = max(rows, key=lambda x: x[4]['t'])
print(f"largest |t| anywhere: {best[0]} lb={best[1]} fw={best[2]} k={best[3]} t={best[4]['t']:+.2f} net={best[4]['net']:+.2f}%")
surv = [r for r in rows if abs(r[4]['t']) > 3.3]
print(f"cells surviving a Bonferroni-scale |t|>3.3: {len(surv)}")
print(f"\nMDE range across cells: {min(r['mde'] for *_ ,r in rows):.2f}% to {max(r['mde'] for *_ ,r in rows):.2f}%")
print("=> any true edge SMALLER than the MDE is undetectable here; a null is not proof of absence.")
