"""Decisive check on the apparent momentum edge: does it survive NON-OVERLAPPING windows?

reversal.py date-clusters (one obs per calendar day) but that does NOT fix SERIAL overlap.
At fw=14, consecutive days share 13/14 of their forward window, so ~212 'independent' days
are really ~15 effective observations. That inflates t by roughly sqrt(14) = 3.7x.

Test: resample every `fw` days so forward windows never overlap, and average over all
`fw` possible phase offsets so the answer does not depend on where we start counting.
"""
import json, os, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = json.load(open(os.path.join(ROOT, "data", "cache", "ohlc_1d.json")))
META = json.load(open(os.path.join(ROOT, "data", "cache", "meta.json")))
COST = 0.92
pairs = [p for p in C if not META.get(p, {}).get("is_stable")
         and p not in ("EURUSD", "GBPUSD", "PAXGUSD")]
series = {p: {r[0]: r[4] for r in C[p]} for p in pairs}
times = sorted(set.intersection(*[set(v) for v in series.values()]))

def daily_excess(lookback, horizon, k):
    out = {}
    for i in range(lookback, len(times) - horizon):
        t0, t, t1 = times[i-lookback], times[i], times[i+horizon]
        trail, fwd = {}, {}
        for p in pairs:
            if t0 in series[p] and t in series[p] and t1 in series[p] and series[p][t0] > 0:
                trail[p] = series[p][t]/series[p][t0]-1
                fwd[p] = (series[p][t1]/series[p][t]-1)*100
        if len(trail) < 10: continue
        mkt = statistics.mean(fwd.values())
        sel = sorted(trail, key=lambda p: -trail[p])[:k]
        out[i] = statistics.mean(fwd[p]-mkt for p in sel)
    return out

print(f"{'lb':>4}{'fw':>4}{'k':>3} | {'OVERLAPPING (as reported)':>28} | {'NON-OVERLAPPING (honest)':>30}")
print(f"{'':>11} | {'n':>5}{'mean':>8}{'t':>7}{'':>8} | {'n_eff':>6}{'mean':>8}{'t':>7}{'net':>8}")
for lb, fw, k in ((14,14,3),(30,14,3),(14,14,1),(7,14,3),(14,7,3),(30,7,3)):
    d = daily_excess(lb, fw, k)
    idx = sorted(d)
    m_ov = statistics.mean(d.values()); n_ov = len(d)
    se_ov = statistics.pstdev(list(d.values()))/n_ov**0.5
    # average across all phase offsets so the result is not an artefact of the start index
    phase_means, phase_ts, neffs = [], [], []
    for ph in range(fw):
        sub = [d[i] for j, i in enumerate(idx) if j % fw == ph]
        if len(sub) < 8: continue
        mm = statistics.mean(sub); ss = statistics.pstdev(sub)/len(sub)**0.5
        phase_means.append(mm); phase_ts.append(mm/ss if ss else 0); neffs.append(len(sub))
    m_no = statistics.mean(phase_means); t_no = statistics.mean(phase_ts)
    print(f"{lb:>4}{fw:>4}{k:>3} | {n_ov:>5}{m_ov:>+8.2f}{m_ov/se_ov:>+7.2f}{'':>8} | "
          f"{int(statistics.mean(neffs)):>6}{m_no:>+8.2f}{t_no:>+7.2f}{m_no-COST:>+8.2f}")

print("\nInflation factor if serial overlap is ignored: ~sqrt(fw).")
for fw in (7,14): print(f"  fw={fw}: t inflated by ~{fw**0.5:.1f}x")
