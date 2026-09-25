"""Audit measurement A4 -- how many INDEPENDENT regime episodes does the available history hold?

OUTCOME-BLIND: only the regime variable is computed, never a forward return. A regime-conditioned
strategy is evaluated on regime *episodes*, not on bars: 300 weeks inside 4 high-vol episodes is
~4 observations of "what happens in high vol" (registry R12 / X1 made this point informally).
This counts episodes for common regime definitions on Kraken weekly data (research/tsmom/
ohlc_long.json, 20 assets, ~7 years for the oldest), using only trailing information.

Regimes (all trailing, point-in-time):
  btc_vol_high     BTC 12-week realised vol above its own expanding median
  btc_trend_up     BTC close above its 26-week simple moving average
  alt_led          median alt 4-week return minus BTC 4-week return > 0
  high_corr        median pairwise 12-week correlation of alts with BTC above expanding median
An episode is a maximal run of consecutive weeks in one state; runs shorter than 3 weeks are
merged into the surrounding state (so noise flicker does not inflate the count).

Usage: python3 research/audits/regime_episodes.py
"""
import json, math, os, statistics, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "results", "regime_episodes.json")


def closes(d, pair):
    return {int(r[0]): float(r[4]) for r in d[pair]["10080"]}


def episodes(states, min_run=3):
    runs = []
    for s in states:
        if runs and runs[-1][0] == s:
            runs[-1][1] += 1
        else:
            runs.append([s, 1])
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for i, (s, n) in enumerate(runs):
            if n < min_run:
                j = i - 1 if i > 0 else i + 1
                runs[j][1] += n
                runs.pop(i)
                merged = []
                for r in runs:
                    if merged and merged[-1][0] == r[0]:
                        merged[-1][1] += r[1]
                    else:
                        merged.append(r)
                runs = merged
                changed = True
                break
    return runs


def main():
    d = json.load(open(os.path.join(ROOT, "research", "tsmom", "ohlc_long.json")))
    btc = closes(d, "XBTUSD")
    ts = sorted(btc)
    alts = {p: closes(d, p) for p in d if p != "XBTUSD"}
    lr = lambda s, t0, t1: math.log(s[t1] / s[t0])
    reg = {"btc_vol_high": [], "btc_trend_up": [], "alt_led": [], "high_corr": []}
    vols, corrs = [], []
    for i in range(26, len(ts)):
        t = ts[i]
        br = [lr(btc, ts[k - 1], ts[k]) for k in range(i - 11, i + 1)]
        v = statistics.pstdev(br); vols.append(v)
        reg["btc_vol_high"].append(v > statistics.median(vols))
        reg["btc_trend_up"].append(btc[t] > statistics.mean(btc[ts[k]] for k in range(i - 25, i + 1)))
        a4 = [lr(s, ts[i - 4], t) for s in alts.values() if ts[i - 4] in s and t in s]
        reg["alt_led"].append(bool(a4) and statistics.median(a4) - lr(btc, ts[i - 4], t) > 0)
        cs = []
        for s in alts.values():
            if all(ts[k] in s for k in range(i - 12, i + 1)):
                ar = [lr(s, ts[k - 1], ts[k]) for k in range(i - 11, i + 1)]
                try:
                    cs.append(statistics.correlation(ar, br))
                except statistics.StatisticsError:
                    pass
        c = statistics.median(cs) if cs else 0.0; corrs.append(c)
        reg["high_corr"].append(c > statistics.median(corrs))
    res = dict(generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               weeks=len(ts) - 26,
               span=[time.strftime("%Y-%m-%d", time.gmtime(ts[26])),
                     time.strftime("%Y-%m-%d", time.gmtime(ts[-1]))], regimes={})
    for name, st in reg.items():
        runs = episodes(st)
        on = [n for s, n in runs if s]; off = [n for s, n in runs if not s]
        res["regimes"][name] = dict(episodes_total=len(runs), episodes_on=len(on),
                                    episodes_off=len(off), weeks_on=sum(on), weeks_off=sum(off),
                                    median_on_length_weeks=statistics.median(on) if on else None)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
