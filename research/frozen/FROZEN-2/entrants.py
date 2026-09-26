"""FROZEN-2 entrant code (FROZEN: sha256 in FREEZE.json; any edit voids the experiment).

Question (audit open question 2 / P4): is the ARITHMETIC mean excess of high-volatility names over LINK positive
after costs, forward and uncontaminated? Pure functions over closes {pair: {bar_open_ts: close}};
close(t) = close of the bar opened at t - 1 day.
"""
import math

import numpy as np

DAY = 86400
H = 28 * DAY
RT4 = 0.0183           # A1: LINK -> basket -> LINK, 4 maker legs incl. adverse selection
LINK = "LINKUSD"


def close(s, t):
    return s.get(t - DAY)


def close_upto(s, t):
    """Last close at or before t (a delisted pair keeps its last traded price)."""
    ks = [k for k in s if k <= t - DAY]
    return s[max(ks)] if ks else None


def vol60(s, t):
    cl = [close(s, t - k * DAY) for k in range(60, -1, -1)]
    if any(c is None for c in cl):
        return None
    return float(np.std(np.diff(np.log(cl)), ddof=1))


def first_monday_after(ts):
    d = (int(ts) // DAY + 1) * DAY
    while (d // DAY + 3) % 7 != 0:       # 1970-01-01 was a Thursday; Monday <=> (days + 3) % 7 == 0
        d += DAY
    return d


def periods(closes, universe, t0, now_ts):
    """Non-overlapping 28-day periods from t0 whose end is <= now_ts."""
    out, t = [], t0
    link = closes.get(LINK, {})
    while t + H <= now_ts:
        l0, l1 = close(link, t), close(link, t + H)
        vols = {p: v for p in universe if p != LINK and p in closes and close(closes[p], t)
                and (v := vol60(closes[p], t)) is not None and v >= 0.005}
        if l0 and l1 and len(vols) >= 10:
            n = max(1, math.ceil(len(vols) / 5))
            order = sorted(vols, key=vols.get)
            rl = l1 / l0 - 1.0

            def basket(names):
                rs = []
                for p in names:
                    c0, c1 = close(closes[p], t), close_upto(closes[p], t + H)
                    rs.append(c1 / c0 - 1.0 if (c0 and c1) else -1.0)
                return float(np.mean(rs)), float(np.median(rs))

            q5m, q5med = basket(order[-n:])
            q1m, q1med = basket(order[:n])
            out.append({"t": t, "n_universe": len(vols), "n_basket": n, "link": rl,
                        "q5_net": q5m - rl - RT4, "q1_net": q1m - rl - RT4, "spread_q5_q1": q5m - q1m,
                        "q5_median_asset_minus_link": q5med - rl, "q1_median_asset_minus_link": q1med - rl})
        t += H
    return out
