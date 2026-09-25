"""Decision-grade checks on weekly time-series momentum (TSMOM) before any handoff.

tsmom_pooled.py found: vs random timing at equal exposure, mom4 p=0.009 (log); vs hold, t~0.
Before that can be acted on, four questions remain (all fixed before running):

  V1 FAMILY-WISE: 9 rules were searched. Max-statistic common-shift permutation across all 9
     rules (each rule's pooled stat standardised by its own null mean/sd), 2,000 draws.
  V2 ARITHMETIC: the objective is E[final USD]. Same permutation on ARITHMETIC excess, and the
     pooled week-averaged arithmetic excess vs hold, by era.
  V3 ATTRIBUTION: per-calendar-year pooled log excess for mom4 / sma20 — is the whole result
     two bear markets (2018, 2022)? If so the effective sample is ~2 events, not 600 weeks.
  V4 EXPOSURE CONTROL: static exposure equal to each rule's own average exposure, weekly
     rebalanced, charging rebalancing cost. Timing must beat de-risking, not just holding.

Closed form (pos in {0,1}, one leg per switch, cost c):
  log excess_t   = log(1 - c*sw_t) - (1 - p_t) * log(1 + r_t)
  arith excess_t = -(1 - p_t) * r_t - c*sw_t*(1 + p_t*r_t)
"""
import math
import random
import time

from tsmom import COSTS, RULES, WARMUP, fmt_rule, hac_t, load, signal

SPLIT = 1609459200  # 2021-01-01
C = COSTS["maker"]
DRAWS = 2000


def prep(data):
    out = {}
    for a, bars in data.items():
        c = [b[1] for b in bars]
        ts = [b[0] for b in bars]
        r = [c[i + 1] / c[i] - 1 for i in range(WARMUP, len(c) - 1)]
        out[a] = dict(c=c, r=r, ts=ts[WARMUP + 1:],
                      pos={rule: [signal(c, i, rule) for i in range(WARMUP, len(c) - 1)] for rule in RULES})
    return out


def excess(r, pos, kind):
    out, prev = [], 1
    for p, x in zip(pos, r):
        sw = 1 if p != prev else 0
        if kind == "log":
            out.append((math.log(1 - C) if sw else 0.0) - (0.0 if p else math.log(1 + x)))
        else:
            out.append(-(0.0 if p else x) - (C * (1 + p * x) if sw else 0.0))
        prev = p
    return out


def pooled_stat(P, rule, kind, shift_u=None):
    """Mean over assets of total excess (log) or mean weekly excess (arith)."""
    vals = []
    for a, d in P.items():
        pos = d["pos"][rule]
        if shift_u is not None:
            k = 1 + int(shift_u * (len(pos) - 1))
            pos = pos[k:] + pos[:k]
        e = excess(d["r"], pos, kind)
        vals.append(sum(e) if kind == "log" else sum(e) / len(e))
    return sum(vals) / len(vals)


def week_avg(P, rule, kind, lo=0, hi=1e12):
    byw = {}
    for d in P.values():
        for t, v in zip(d["ts"], excess(d["r"], d["pos"][rule], kind)):
            if lo <= t < hi:
                byw.setdefault(t, []).append(v)
    return [sum(byw[w]) / len(byw[w]) for w in sorted(byw)]


def main():
    P = prep(load())
    rng = random.Random(2026)

    for kind in ("log", "arith"):
        obs = {rule: pooled_stat(P, rule, kind) for rule in RULES}
        null = {rule: [] for rule in RULES}
        for _ in range(DRAWS):
            u = rng.random()
            for rule in RULES:
                null[rule].append(pooled_stat(P, rule, kind, u))
        mu = {k: sum(v) / len(v) for k, v in null.items()}
        sd = {k: math.sqrt(sum((x - mu[k]) ** 2 for x in v) / (len(v) - 1)) for k, v in null.items()}
        zmax_null = [max((null[k][i] - mu[k]) / sd[k] for k in RULES) for i in range(DRAWS)]
        print("=== V1/V2 common-shift permutation, %s excess, %d draws ===" % (kind, DRAWS))
        print("%-6s %10s %10s %7s %8s %8s" % ("rule", "obs", "null_mu", "z", "p_rule", "p_FWER"))
        for rule in RULES:
            z = (obs[rule] - mu[rule]) / sd[rule]
            p_rule = (sum(1 for x in null[rule] if x >= obs[rule]) + 1) / (DRAWS + 1)
            p_fw = (sum(1 for x in zmax_null if x >= z) + 1) / (DRAWS + 1)
            scale = 1 if kind == "log" else 100
            print("%-6s %+10.4f %+10.4f %+7.2f %8.3f %8.3f" % (fmt_rule(rule), obs[rule] * scale,
                                                              mu[rule] * scale, z, p_rule, p_fw))
        print()

    print("=== V2 pooled week-averaged ARITHMETIC excess vs hold (%/wk, HAC t) ===")
    for rule in RULES:
        cells = []
        for lo, hi in ((0, 1e12), (0, SPLIT), (SPLIT, 1e12)):
            m, t = hac_t(week_avg(P, rule, "arith", lo, hi))
            cells.append("%+7.3f t=%+5.2f" % (m * 100, t))
        print("%-6s all %s | pre21 %s | 21+ %s" % (fmt_rule(rule), *cells))

    print("\n=== V3 per-year pooled LOG excess (sum of week-averaged), and asset count ===")
    for rule in (("mom", 4), ("mom", 8), ("sma", 20)):
        byw = {}
        for d in P.values():
            for t, v in zip(d["ts"], excess(d["r"], d["pos"][rule], "log")):
                byw.setdefault(t, []).append(v)
        by_year = {}
        for w, v in byw.items():
            y = time.gmtime(w).tm_year
            by_year.setdefault(y, [0.0, 0])
            by_year[y][0] += sum(v) / len(v)
            by_year[y][1] = max(by_year[y][1], len(v))
        print("%-6s %s" % (fmt_rule(rule), " ".join("%d:%+.2f(n%d)" % (y, s, n) for y, (s, n) in sorted(by_year.items()))))

    print("\n=== V4 static exposure control (same avg exposure, weekly rebalanced, cost charged) ===")
    print("%-6s %6s %10s %10s %10s" % ("rule", "expo", "timing", "static", "timing-static"))
    for rule in RULES:
        t_tot, s_tot = [], []
        for d in P.values():
            pos, r = d["pos"][rule], d["r"]
            e = sum(pos) / len(pos)
            t_tot.append(sum(excess(r, pos, "log")))
            s, w = 0.0, e
            for x in r:
                # drift then rebalance back to e; turnover |w_drift - e| charged at maker cost
                w_drift = e * (1 + x) / (1 + e * x)
                s += math.log(1 + e * x) + math.log(1 - C * abs(w_drift - e)) - math.log(1 + x)
            s_tot.append(s)
        mt, ms = sum(t_tot) / len(t_tot), sum(s_tot) / len(s_tot)
        wins = sum(1 for a, b in zip(t_tot, s_tot) if a > b)
        e_all = sum(sum(d["pos"][rule]) / len(d["pos"][rule]) for d in P.values()) / len(P)
        print("%-6s %6.2f %+10.3f %+10.3f %+10.3f  (timing>static in %d/%d assets)" % (
            fmt_rule(rule), e_all, mt, ms, mt - ms, wins, len(P)))


if __name__ == "__main__":
    main()
