"""Time-series trend timing: hold ASSET or USD, decided weekly at the bar close.

Question: does a trend rule on weekly bars beat buy-and-hold of the same asset, net of costs?
This is exactly the live decision (LINK vs USD). It had never been tested: every prior study
was cross-sectional (market factor removed by demeaning) or intraday (Idea B, 1h/4h bars).

Design (all choices fixed before looking at results):
  * signal at week t close uses only bars <= t; position applies to week t+1 return. No look-ahead.
  * the last (incomplete) weekly bar is dropped.
  * a switch ASSET<->USD is ONE leg. Cost per switch: maker 0.45% (0.40% fee + 5.4 bps measured
    adverse selection) and taker 0.83% (measured) — both reported.
  * excess_t = pos_t * r_t - switch_cost_t - r_t   (benchmark = hold the same asset, costless)
    so every number here is already benchmark-relative (the D8 lesson).
  * 1-week holding periods do not overlap; t-stats use Newey-West HAC (lag 4) anyway because
    positions persist and excess returns are serially correlated through the position.
  * rule family fixed a priori from the TSMOM literature (Moskowitz-Ooi-Pedersen 2012;
    Liu-Tsyvinski 2021 for crypto): sign of trailing L-week return, L in {1,2,4,8,13,26};
    close above N-week SMA, N in {10,20,40}. 9 rules. Bonferroni over 9 => |t| >= 2.77.

Pooled cross-asset test: assets are highly correlated, so the pooled statistic averages
excess across assets WITHIN each week first (one observation per week), then HAC over weeks.
Survivorship: only currently-listed assets are included. Dead coins went to ~0, which a trend
rule would largely have exited — so survivorship biases AGAINST timing here, not for it.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COSTS = {"maker": 0.0045, "taker": 0.0083}
RULES = [("mom", L) for L in (1, 2, 4, 8, 13, 26)] + [("sma", N) for N in (10, 20, 40)]
WARMUP = 40  # identical start for every rule within an asset


def load():
    with open(os.path.join(HERE, "ohlc_long.json")) as fh:
        d = json.load(fh)
    out = {}
    for p, v in d.items():
        bars = v["10080"][:-1]  # drop incomplete current week
        out[p] = [(b[0], b[4]) for b in bars]
    return out


def signal(closes, i, rule):
    kind, n = rule
    if kind == "mom":
        return 1 if closes[i] > closes[i - n] else 0
    sma = sum(closes[i - n + 1:i + 1]) / n
    return 1 if closes[i] > sma else 0


def series(bars, rule, cost):
    """Return list of (week_ts, excess_simple, strat_simple, hold_simple, pos, switched)."""
    ts = [b[0] for b in bars]
    c = [b[1] for b in bars]
    rows = []
    prev = 1  # start invested, like the benchmark: entering the rule costs a switch only if it says out
    for i in range(WARMUP, len(c) - 1):
        pos = signal(c, i, rule)
        sw = 1 if pos != prev else 0
        r = c[i + 1] / c[i] - 1
        strat = (1 - cost * sw) * (1 + pos * r) - 1
        rows.append((ts[i + 1], strat - r, strat, r, pos, sw))
        prev = pos
    return rows


def hac_t(x, lags=4):
    n = len(x)
    if n < 10:
        return float("nan"), float("nan")
    m = sum(x) / n
    d = [v - m for v in x]
    g0 = sum(v * v for v in d) / n
    s = g0
    for k in range(1, lags + 1):
        gk = sum(d[j] * d[j - k] for j in range(k, n)) / n
        s += 2 * (1 - k / (lags + 1)) * gk
    se = math.sqrt(max(s, 1e-18) / n)
    return m, m / se


def summarize(rows):
    ex = [r[1] for r in rows]
    m, t = hac_t(ex)
    w_s = math.prod(1 + r[2] for r in rows)
    w_h = math.prod(1 + r[3] for r in rows)
    switches = sum(r[5] for r in rows)
    years = len(rows) / 52.18
    exposure = sum(r[4] for r in rows) / len(rows)
    # max drawdown of the strategy equity
    eq, peak, mdd = 1.0, 1.0, 0.0
    for r in rows:
        eq *= 1 + r[2]
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    eqh, peakh, mddh = 1.0, 1.0, 0.0
    for r in rows:
        eqh *= 1 + r[3]
        peakh = max(peakh, eqh)
        mddh = min(mddh, eqh / peakh - 1)
    return dict(n=len(rows), mean_wk_excess=m, t_hac=t, wealth_strat=w_s, wealth_hold=w_h,
                log_ratio=math.log(w_s / w_h), switches_per_yr=switches / years,
                exposure=exposure, mdd_strat=mdd, mdd_hold=mddh)


def pooled(data, assets, rule, cost, t_from=None, t_to=None):
    by_week = {}
    for a in assets:
        for r in series(data[a], rule, cost):
            if (t_from and r[0] < t_from) or (t_to and r[0] >= t_to):
                continue
            by_week.setdefault(r[0], []).append(r[1])
    weeks = sorted(by_week)
    x = [sum(by_week[w]) / len(by_week[w]) for w in weeks]
    m, t = hac_t(x)
    return dict(weeks=len(x), mean_wk_excess=m, t_hac=t)


def fmt_rule(r):
    return "%s%d" % r


def main():
    data = load()
    out = {}
    target = sys.argv[1] if len(sys.argv) > 1 else "LINKUSD"
    print("=== %s: timing vs buy-and-hold, weekly, %d bars ===" % (target, len(data[target])))
    for cname, cost in COSTS.items():
        print("-- cost/switch %s %.2f%%" % (cname, cost * 100))
        print("%-6s %4s %9s %7s %8s %8s %7s %6s %7s %7s" % (
            "rule", "n", "wk_exc%", "t_hac", "W_strat", "W_hold", "sw/yr", "expo", "mdd_s", "mdd_h"))
        for rule in RULES:
            s = summarize(series(data[target], rule, cost))
            out.setdefault(target, {}).setdefault(cname, {})[fmt_rule(rule)] = s
            print("%-6s %4d %+9.3f %+7.2f %8.2f %8.2f %7.1f %6.2f %+7.2f %+7.2f" % (
                fmt_rule(rule), s["n"], s["mean_wk_excess"] * 100, s["t_hac"], s["wealth_strat"],
                s["wealth_hold"], s["switches_per_yr"], s["exposure"], s["mdd_strat"], s["mdd_hold"]))

    others = [a for a in data if a != target]
    print("\n=== POOLED across %d other assets (week-averaged, HAC over weeks), maker cost ===" % len(others))
    split = 1609459200  # 2021-01-01: discovery (before) vs holdout (after)
    print("%-6s | %-26s | %-26s | %-26s" % ("rule", "all", "pre-2021", "2021+"))
    for rule in RULES:
        a = pooled(data, others, rule, COSTS["maker"])
        b = pooled(data, others, rule, COSTS["maker"], t_to=split)
        c = pooled(data, others, rule, COSTS["maker"], t_from=split)
        out.setdefault("pooled_ex_" + target, {})[fmt_rule(rule)] = dict(all=a, pre2021=b, post2021=c)
        print("%-6s | n=%3d %+7.3f%% t=%+5.2f | n=%3d %+7.3f%% t=%+5.2f | n=%3d %+7.3f%% t=%+5.2f" % (
            fmt_rule(rule), a["weeks"], a["mean_wk_excess"] * 100, a["t_hac"],
            b["weeks"], b["mean_wk_excess"] * 100, b["t_hac"],
            c["weeks"], c["mean_wk_excess"] * 100, c["t_hac"]))
    with open(os.path.join(HERE, "tsmom_results_%s.json" % target), "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
