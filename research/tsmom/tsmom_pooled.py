"""Pooled cross-asset test of compounded (log) excess, correcting for cross-asset correlation.

"Timing wins in 18/20 assets" is NOT 18 independent observations: crypto assets share one
dominant factor, so a rule that sidestepped 2018 and 2022 wins almost everywhere at once.
Two corrections:
  1. week-average log excess across assets (one observation per week), HAC t over weeks,
     split pre-2021 (discovery era) vs 2021+ (holdout era, overlaps LINK's modern history).
  2. COMMON circular shift permutation: every asset's position series is shifted by the same
     k, preserving cross-asset correlation, exposure and switch frequency; only timing is
     destroyed. Statistic: mean over assets of total log ratio. 1,000 draws.
Also reports the static 50% rebalanced control (no timing, same average exposure), which
isolates the pure de-risking (variance-drag) component from any timing skill.
"""
import math
import random

from tsmom import COSTS, RULES, WARMUP, fmt_rule, hac_t, load
from tsmom_log import log_excess, positions

SPLIT = 1609459200  # 2021-01-01


def main():
    data = load()
    cost = COSTS["maker"]
    assets = sorted(data)
    closes = {a: [b[1] for b in data[a]] for a in assets}
    tss = {a: [b[0] for b in data[a]][WARMUP + 1:] for a in assets}

    # static 50% weekly-rebalanced control, ignoring rebalancing cost (favours the control)
    def static_log_ratio(c):
        s = 0.0
        for i in range(WARMUP, len(c) - 1):
            r = c[i + 1] / c[i] - 1
            s += math.log(1 + 0.5 * r) - math.log(1 + r)
        return s
    st = [static_log_ratio(closes[a]) for a in assets]
    print("static 50%% control: mean log ratio %+.2f, wins %d/%d, LINK %+.2f" % (
        sum(st) / len(st), sum(1 for v in st if v > 0), len(st), static_log_ratio(closes["LINKUSD"])))

    rng = random.Random(11)
    print("%-6s | %-22s | %-22s | %-22s | %s" % ("rule", "all wk-avg", "pre-2021", "2021+", "common-shift perm"))
    for rule in RULES:
        pos = {a: positions(closes[a], rule) for a in assets}
        le = {a: log_excess(closes[a], pos[a], cost) for a in assets}
        byw = {}
        for a in assets:
            for t, v in zip(tss[a], le[a]):
                byw.setdefault(t, []).append(v)
        wk = sorted(byw)
        x = [(w, sum(byw[w]) / len(byw[w])) for w in wk]
        cells = []
        for lo, hi in ((0, 1e12), (0, SPLIT), (SPLIT, 1e12)):
            xs = [v for w, v in x if lo <= w < hi]
            m, t = hac_t(xs)
            cells.append("n=%3d %+6.3f%% t=%+5.2f" % (len(xs), m * 100, t))
        obs = sum(sum(le[a]) for a in assets) / len(assets)
        ge = 0
        draws = 1000
        for _ in range(draws):
            u = rng.random()
            tot = 0.0
            for a in assets:
                n = len(pos[a])
                k = 1 + int(u * (n - 1))
                sh = pos[a][k:] + pos[a][:k]
                tot += sum(log_excess(closes[a], sh, cost))
            if tot / len(assets) >= obs:
                ge += 1
        print("%-6s | %s | %s | %s | obs %+5.2f p=%.3f" % (fmt_rule(rule), cells[0], cells[1], cells[2], obs, (ge + 1) / (draws + 1)))


if __name__ == "__main__":
    main()
