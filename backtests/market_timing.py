"""Q1/Q6: MARKET TIMING -- the axis my entire framework is blind to.

Every signal tested so far is cross-sectional (which alt to hold), and cross-sectional
demeaning REMOVES the market factor by construction. So market-wide predictability has
never been tested at all. The live decision (hold LINK vs hold USD) is precisely a timing
decision, and it was resolved with UNCONDITIONAL statistics.

Hypothesis: majors (BTC/ETH) lead the broad alt complex, so majors' trailing return
predicts the universe's forward return. If true it is monetisable at 2 legs (~0.92%):
be in crypto, or be in USD.

Standing rule applied (registry D7): every horizon>1 result reports a NON-OVERLAPPING /
phase-averaged t, never just the clustered one.
"""
import json, os, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = json.load(open(os.path.join(ROOT, "data", "cache", "meta.json")))
COST = 0.92


def load(tf):
    C = json.load(open(os.path.join(ROOT, "data", "cache", f"ohlc_{tf}.json")))
    pairs = [p for p in C if not META.get(p, {}).get("is_stable")
             and p not in ("EURUSD", "GBPUSD", "PAXGUSD")]
    s = {p: {r[0]: r[4] for r in C[p]} for p in pairs}
    t = sorted(set.intersection(*[set(v) for v in s.values()]))
    return s, t, pairs


def phase_t(vals, step):
    """Non-overlapping t, averaged across all phase offsets."""
    ms, ts, ns = [], [], []
    for ph in range(step):
        sub = vals[ph::step]
        if len(sub) < 8: continue
        m = statistics.mean(sub); se = statistics.pstdev(sub)/len(sub)**0.5
        ms.append(m); ts.append(m/se if se else 0); ns.append(len(sub))
    if not ms: return None
    return statistics.mean(ms), statistics.mean(ts), int(statistics.mean(ns))


for tf, bars_per_day in (("4h", 6), ("1h", 24)):
    S, T, P = load(tf)
    leaders = [p for p in ("XBTUSD", "ETHUSD") if p in S]
    print(f"\n=== {tf} bars, {len(P)} assets, {len(T)} common bars, leaders {leaders} ===")
    print(f"{'lead_lb':>8}{'fwd':>5}{'n_all':>7}{'mean_on':>9}{'mean_off':>10}{'spread':>8}"
          f"{'t_overlap':>11}{'t_nonov':>9}{'n_eff':>7}{'net_vs_hold':>12}")
    for lb in (1, 2, 3, 6):
        for fw in (1, 2, 3, 6):
            on, off, allr = [], [], []
            for i in range(max(lb, 2), len(T)-fw):
                t0, t, t1 = T[i-lb], T[i], T[i+fw]
                lead = [S[p][t]/S[p][t0]-1 for p in leaders if t0 in S[p] and t in S[p]]
                if not lead: continue
                fwd = [(S[p][t1]/S[p][t]-1)*100 for p in P if t in S[p] and t1 in S[p]]
                if len(fwd) < 10: continue
                mkt = statistics.mean(fwd)
                allr.append(mkt)
                (on if statistics.mean(lead) > 0 else off).append(mkt)
            if len(on) < 40 or len(off) < 40: continue
            # strategy: hold crypto when leaders were up, else USD (earning 0)
            diff = [x for x in on]
            po = phase_t(diff, fw)
            if not po: continue
            m_on, t_no, neff = po
            m_all = statistics.mean(allr)
            se_ov = statistics.pstdev(on)/len(on)**0.5
            # switching cost: pay 0.92% each time we change state
            print(f"{lb:>8}{fw:>5}{len(allr):>7}{statistics.mean(on):>+9.2f}{statistics.mean(off):>+10.2f}"
                  f"{statistics.mean(on)-statistics.mean(off):>+8.2f}{statistics.mean(on)/se_ov:>+11.2f}"
                  f"{t_no:>+9.2f}{neff:>7}{m_on-m_all:>+12.2f}")
