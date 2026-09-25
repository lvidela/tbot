"""Companion to tsmom.py: tests COMPOUNDED (log) excess, plus robustness controls.

Why a second statistic: tsmom.py showed LINK mom4/mom8 ending at ~2x the hold wealth while the
ARITHMETIC mean weekly excess is negative. Both are true at once: missing a few huge up-weeks
costs arithmetic mean; skipping deep drawdowns saves variance drag, which drives compounding.
  * arithmetic mean excess -> what a risk-neutral maximiser of E[final USD] should use
  * log excess (sum = log wealth ratio) -> the median / realised-path outcome
The live objective ("maximize final USD") is a single realised path, so both are reported.

Controls, all fixed before running:
  C1 phase: weekly bars start on Thursday; rerun on daily data resampled to weeks anchored on
     each of the 7 weekdays (last ~2 years only — daily history is capped at 720 bars).
  C2 permutation: circularly shift the position series against returns (keeps signal
     persistence and exposure, destroys timing). 2,000 shifts. One-sided p for log excess.
  C3 leave-one-out-year: the log ratio with each calendar year removed.
  C4 cross-asset: same rules, per asset, log ratio, counting assets where timing wins.
"""
import json
import math
import os
import random
import time

from tsmom import COSTS, RULES, WARMUP, fmt_rule, hac_t, load, signal

HERE = os.path.dirname(os.path.abspath(__file__))


def positions(closes, rule):
    return [signal(closes, i, rule) for i in range(WARMUP, len(closes) - 1)]


def log_excess(closes, pos, cost):
    rets = [closes[i + 1] / closes[i] - 1 for i in range(WARMUP, len(closes) - 1)]
    out, prev = [], 1
    for p, r in zip(pos, rets):
        sw = 1 if p != prev else 0
        strat = (1 - cost * sw) * (1 + p * r)
        out.append(math.log(strat) - math.log(1 + r))
        prev = p
    return out


def perm_p(closes, pos, cost, draws=2000, seed=7):
    obs = sum(log_excess(closes, pos, cost))
    rng = random.Random(seed)
    n = len(pos)
    ge = 0
    for _ in range(draws):
        k = rng.randrange(1, n)
        shifted = pos[k:] + pos[:k]
        if sum(log_excess(closes, shifted, cost)) >= obs:
            ge += 1
    return obs, (ge + 1) / (draws + 1)


def weekly_from_daily(daily, anchor_wd):
    """Resample daily bars to weekly closes, week ending on weekday anchor_wd (0=Mon)."""
    out = []
    for b in daily:
        if time.gmtime(b[0]).tm_wday == anchor_wd:
            out.append(b[4])
    return out


def main():
    data = load()
    with open(os.path.join(HERE, "ohlc_long.json")) as fh:
        raw = json.load(fh)
    cost = COSTS["maker"]
    res = {}

    print("=== LINKUSD log excess (compounded), maker cost; HAC t; circular-shift permutation p ===")
    c = [b[1] for b in data["LINKUSD"]]
    ts = [b[0] for b in data["LINKUSD"]]
    for rule in RULES:
        pos = positions(c, rule)
        le = log_excess(c, pos, cost)
        m, t = hac_t(le)
        obs, p = perm_p(c, pos, cost)
        res[fmt_rule(rule)] = dict(log_ratio=obs, t_hac=t, perm_p=p)
        print("%-6s log_ratio %+6.3f (x%.2f)  t_hac %+5.2f  perm_p %.3f" % (fmt_rule(rule), obs, math.exp(obs), t, p))

    print("\n=== C3 leave-one-year-out, LINK, log ratio ===")
    years = sorted({time.gmtime(t).tm_year for t in ts[WARMUP + 1:]})
    for rule in (("mom", 4), ("mom", 8), ("sma", 20)):
        pos = positions(c, rule)
        le = log_excess(c, pos, cost)
        yrs = [time.gmtime(t).tm_year for t in ts[WARMUP + 1:]]
        by = {y: sum(v for v, yy in zip(le, yrs) if yy == y) for y in years}
        loo = {y: sum(le) - by[y] for y in years}
        print("%-6s per-year: %s" % (fmt_rule(rule), "  ".join("%d:%+.2f" % (y, by[y]) for y in years)))
        print("       drop-year: %s" % "  ".join("%d:%+.2f" % (y, loo[y]) for y in years))

    print("\n=== C1 weekday phase (daily->weekly, last ~2y only), LINK, log ratio ===")
    for rule in (("mom", 4), ("mom", 8), ("sma", 20)):
        vals = []
        for wd in range(7):
            cc = weekly_from_daily(raw["LINKUSD"]["1440"][:-1], wd)
            if len(cc) - 1 <= WARMUP + 5:
                continue
            vals.append(sum(log_excess(cc, positions(cc, rule), cost)))
        print("%-6s by weekday: %s" % (fmt_rule(rule), " ".join("%+.2f" % v for v in vals)))

    print("\n=== C4 cross-asset: per-asset log ratio (timing vs hold), maker ===")
    for rule in RULES:
        lrs = {}
        for a, bars in data.items():
            cc = [b[1] for b in bars]
            lrs[a] = sum(log_excess(cc, positions(cc, rule), cost))
        wins = sum(1 for v in lrs.values() if v > 0)
        med = sorted(lrs.values())[len(lrs) // 2]
        print("%-6s timing wins %2d/%d  median log ratio %+.2f" % (fmt_rule(rule), wins, len(lrs), med))
        res.setdefault("cross_asset", {})[fmt_rule(rule)] = dict(wins=wins, n=len(lrs), median=med)

    with open(os.path.join(HERE, "tsmom_log_results.json"), "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()
