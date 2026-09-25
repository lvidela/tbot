"""FROZEN-1 entrant signal code. FROZEN: sha256 recorded in spec.json at freeze time; any edit voids the
entrant (research/frozen/evaluate.py refuses to run on a hash mismatch).

All functions are pure: they take a price panel {pair: {bar_open_ts: close}} (Kraken public daily OHLC,
close(t) = close of the bar opened at t - 1 day) and return decisions / per-period returns.
"""
import numpy as np

DAY = 86400
MAKER_LEG = 0.0046
TACTICAL_RT = 0.0183


def close(s, t):
    return s.get(t - DAY)


def fwd_simple(s, t, days):
    c0, c1 = close(s, t), close(s, t + days * DAY)
    return (c1 / c0 - 1.0) if c0 and c1 else None


def vol60(s, t):
    cl = [close(s, t - k * DAY) for k in range(60, -1, -1)]
    if any(c is None for c in cl):
        return None
    return float(np.std(np.diff(np.log(cl)), ddof=1))


# ---------------------------------------------------------------- A1: S2 alone, h = 5, vs static exposure
def a1_s2_windows(panel, t0, t_end, h=5):
    """Decision every h days from t0: w = 1 (LINK) if BTC close(t) > SMA50 of the 50 closes ending at close(t),
    else 0 (USD). Returns [(t, w, r_link)] for windows fully inside [t0, t_end]."""
    btc, link = panel["XBTUSD"], panel["LINKUSD"]
    out, t = [], t0
    while t + h * DAY <= t_end:
        cl = [close(btc, t - k * DAY) for k in range(49, -1, -1)]
        r = fwd_simple(link, t, h)
        if all(c is not None for c in cl) and r is not None:
            out.append((t, 1.0 if cl[-1] > np.mean(cl) else 0.0, r))
        t += h * DAY
    return out


def a1_returns(windows, weights=None):
    """Per-window net returns for exposure weights (default: the rule's own), maker cost on |Δw| after drift."""
    w_seq = [w for _, w, _ in windows] if weights is None else list(weights)
    out, prev = [], 0.0
    for w, (_, _, r) in zip(w_seq, windows):
        out.append(w * r - MAKER_LEG * abs(w - prev))
        prev = w * (1 + r) / (1 + w * r) if (1 + w * r) > 0 and w > 0 else 0.0
    return np.array(out)


def a1_statistic(windows):
    """Primary: mean per-window (timing - static), static = constant weight e = mean rule exposure."""
    if not windows:
        return None, None
    e = float(np.mean([w for _, w, _ in windows]))
    timing = a1_returns(windows)
    static = a1_returns(windows, [e] * len(windows))
    return timing - static, e


# ---------------------------------------------------------------- A2: X4 low-vol 5 vs hold-LINK
def a2_periods(panel, universe, t0, t_end, k=5, h=28):
    """Every h days from t0: equal-weight the k lowest-vol60 pairs of the frozen universe. Returns per period
    (t, picks, basket_gross, link_return, candidate_returns{pair: r})."""
    out, t = [], t0
    while t + h * DAY <= t_end:
        vols = {p: v for p in universe if p in panel and (v := vol60(panel[p], t)) is not None and v >= 0.005}
        rets = {p: fwd_simple(panel[p], t, h) for p in vols}
        rets = {p: r for p, r in rets.items() if r is not None}
        rl = fwd_simple(panel["LINKUSD"], t, h)
        if len(rets) >= k and rl is not None:
            picks = sorted(rets, key=lambda p: vols[p])[:k]
            out.append((t, picks, float(np.mean([rets[p] for p in picks])), rl, rets))
        t += h * DAY
    return out


def a2_excess(periods, picks_fn=None):
    """Per-period excess vs hold-LINK, net: leaving LINK and returning costs are charged as turnover at the
    maker rate (entry from LINK counts 2 legs on the first period; later turnover between baskets)."""
    out, prev = [], None
    for i, (t, picks, g, rl, rets) in enumerate(periods):
        pk = picks if picks_fn is None else picks_fn(i, rets)
        g = float(np.mean([rets[p] for p in pk]))
        w = {p: 1 / len(pk) for p in pk}
        if prev is None:
            turn_legs = 2.0                      # sell LINK + buy basket
        else:
            turn_legs = sum(abs(w.get(p, 0) - prev.get(p, 0)) for p in set(w) | set(prev))
        out.append(g - MAKER_LEG * turn_legs - rl)
        prev = {p: w[p] * (1 + rets[p]) / (1 + g) for p in pk} if g > -1 else {}
    return np.array(out)


# ---------------------------------------------------------------- B: live candidate stream (mirrored ledger)
def decision_day(ts):
    """Entry at the first UTC midnight close after the decision (conservative; no intraday data needed)."""
    return (int(ts) // DAY + 1) * DAY


def b_rows(ledger_rows, panel, universe, freeze_ts, h=3):
    """For each candidate with decision_ts_epoch > freeze_ts: 3-day excess vs LINK net of the 4-leg tactical
    cost, the X4 filter flag (vol60 <= median of the frozen universe at entry), and the entry day."""
    out = []
    for r in ledger_rows:
        ts = r.get("decision_ts_epoch") or r.get("opened_ts")
        pair = r.get("pair")
        if ts is None or ts <= freeze_ts or pair not in panel:
            continue
        t = decision_day(ts)
        rc, rl = fwd_simple(panel[pair], t, h), fwd_simple(panel["LINKUSD"], t, h)
        v = vol60(panel[pair], t)
        uv = [x for p in universe if p in panel and (x := vol60(panel[p], t)) is not None]
        if rc is None or rl is None or v is None or not uv:
            continue
        out.append({"t": t, "pair": pair, "excess": rc - rl - TACTICAL_RT, "lowvol": v <= float(np.median(uv))})
    return out


def cluster_means(rows, key=None):
    """Mean excess per entry day (one observation per decision day, registry F1/D7)."""
    by = {}
    for r in rows:
        if key is None or key(r):
            by.setdefault(r["t"], []).append(r["excess"])
    return {t: float(np.mean(v)) for t, v in sorted(by.items())}
