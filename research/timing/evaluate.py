"""Evaluation core for pre-registration T1 (section 4). Pure numpy/scipy, no I/O.

Conventions
- close: 1-D float array of daily closes; sig: same length, 1.0 ON / 0.0 OFF / NaN warm-up.
- Decision dates are non-overlapping (every h days); every phase offset 0..h-1 is evaluated and
  averaged (registry rule D7). Phases are highly correlated, so the averaged SE is NOT divided
  by sqrt(h): it is the mean of the per-phase SEs, i.e. no credit is taken for phase averaging.
- The account starts in LINK (state ON before the first decision), as the live account does.
"""
import math

import numpy as np
from scipy import stats

MAKER_LEG = 0.0046   # 0.40% fee + 5.4 bps adverse selection, rounded up (A1)
TAKER_LEG = 0.0083
N_FAMILY = 18
Z80 = stats.norm.ppf(0.80)


def windows(close, sig, h, phase, lag=0, dates_mask=None):
    """Non-overlapping windows for one phase. Returns (R, s, idx)."""
    close = np.asarray(close, float)
    sig = np.asarray(sig, float)
    n = len(close)
    valid = np.where(~np.isnan(sig))[0]
    if len(valid) == 0:
        return np.array([]), np.array([]), np.array([], int)
    t = np.arange(valid[0] + phase, n - h - lag, h)
    t = t[~np.isnan(sig[t])]
    c0, c1 = close[t + lag], close[t + lag + h]
    ok = ~(np.isnan(c0) | np.isnan(c1))
    if dates_mask is not None:
        ok &= np.asarray(dates_mask)[t]
    t = t[ok]
    return close[t + lag + h] / close[t + lag] - 1, sig[t], t


def strategy(R, s, cost_leg, start_state=1.0):
    """Per-window net strategy return and excess vs hold-LINK (both simple returns)."""
    prev = np.concatenate([[start_state], s[:-1]])
    cost = cost_leg * np.abs(s - prev)
    net = s * R - cost
    return net, net - R, cost


def welch(R, s):
    on, off = R[s == 1], R[s == 0]
    if len(on) < 2 or len(off) < 2:
        return math.nan, math.nan, math.nan
    va, vb = on.var(ddof=1) / len(on), off.var(ddof=1) / len(off)
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(on) - 1) + vb ** 2 / (len(off) - 1)) if se > 0 else math.nan
    return on.mean() - off.mean(), se, df


def _mean_se(x):
    return (x.mean(), x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else (math.nan, math.nan)


def evaluate(close, sig, h, lag=0, cost_leg=MAKER_LEG, dates_mask=None, n_family=N_FAMILY):
    """All section-4 statistics for one (signal, horizon), phase-averaged."""
    per = []
    for p in range(h):
        R, s, _ = windows(close, sig, h, p, lag, dates_mask)
        if len(R) < 6:
            continue
        d, se, df = welch(R, s)
        net, exc, cost = strategy(R, s, cost_leg)
        em, ese = _mean_se(exc)
        per.append(dict(d=d, se=se, df=df, t=d / se if se else math.nan, n=len(R),
                        n_on=int((s == 1).sum()), n_off=int((s == 0).sum()),
                        exc=em, exc_se=ese, net=net.mean(), hold=R.mean(),
                        switches=int((cost > 0).sum()),
                        wealth=float(np.prod(1 + net)), wealth_hold=float(np.prod(1 + R))))
    if not per:
        return None
    A = {k: np.array([x[k] for x in per], float) for k in per[0]}
    d, se, df = np.nanmean(A["d"]), np.nanmean(A["se"]), np.nanmean(A["df"])
    if not np.isfinite(df) or df < 2:
        df = 2.0
    tc = stats.t.ppf(0.975, df)
    tb = stats.t.ppf(1 - 0.025 / n_family, df)
    exc, exc_se = np.nanmean(A["exc"]), np.nanmean(A["exc_se"])
    return {
        "h": h, "phases": len(per), "n_windows": float(A["n"].mean()),
        "n_on": float(A["n_on"].mean()), "n_off": float(A["n_off"].mean()),
        "spread": d, "se": se, "t": d / se if se else math.nan,
        "t_min": float(np.nanmin(A["t"])), "t_max": float(np.nanmax(A["t"])),
        "ci95": (d - tc * se, d + tc * se),
        "mde": (tc + Z80) * se, "mde_bonf": (tb + Z80) * se, "t_bonf": tb,
        "p_two_sided": float(2 * stats.t.sf(abs(d / se), df)) if se else math.nan,
        "excess_vs_hold_link": exc, "excess_se": exc_se,
        "excess_t": exc / exc_se if exc_se else math.nan,
        "net_vs_hold_usd": float(np.nanmean(A["net"])), "hold_link_mean": float(np.nanmean(A["hold"])),
        "switches_per_phase": float(A["switches"].mean()),
        "wealth_strategy": float(np.nanmedian(A["wealth"])),
        "wealth_hold_link": float(np.nanmedian(A["wealth_hold"])),
    }


def circular_shift(sig, k):
    """Roll the valid part of `sig` by k, keeping the warm-up NaNs in place."""
    sig = np.asarray(sig, float).copy()
    v = np.where(~np.isnan(sig))[0]
    if len(v):
        sig[v[0]:v[-1] + 1] = np.roll(sig[v[0]:v[-1] + 1], k)
    return sig


def family_permutation(close, sigs, horizons, n_perm=2000, min_shift=90, seed=0, observed=None,
                       phase_stride=1):
    """Family-wise p for max |t| over all (signal, horizon) tests via circular shifts.

    `sigs` is a dict name -> array. Each draw shifts every signal by its own random offset
    (>= min_shift days from zero, in either direction). phase_stride > 1 evaluates a subset of
    phases per draw for speed (the observed statistic must then use the same stride).
    """
    rng = np.random.default_rng(seed)

    def max_abs_t(sig_map):
        m = 0.0
        for name, sg in sig_map.items():
            for h in horizons:
                ts = []
                for p in range(0, h, phase_stride):
                    R, s, _ = windows(close, sg, h, p)
                    if len(R) < 6:
                        continue
                    d, se, _ = welch(R, s)
                    if se and np.isfinite(se):
                        ts.append((d, se))
                if ts:
                    d = np.mean([x[0] for x in ts]); se = np.mean([x[1] for x in ts])
                    m = max(m, abs(d / se))
        return m

    obs = max_abs_t(sigs) if observed is None else observed
    null = []
    for _ in range(n_perm):
        shifted = {}
        for name, sg in sigs.items():
            nv = int((~np.isnan(np.asarray(sg, float))).sum())
            if nv <= 2 * min_shift:
                shifted[name] = sg
                continue
            k = int(rng.integers(min_shift, nv - min_shift))
            shifted[name] = circular_shift(sg, k)
        null.append(max_abs_t(shifted))
    null = np.array(null)
    return {"observed_max_abs_t": obs, "p_family": float((1 + (null >= obs).sum()) / (1 + len(null))),
            "null_median": float(np.median(null)), "null_p95": float(np.quantile(null, 0.95))}


def shrink(spread, se, tau):
    """Normal-normal posterior mean of the spread under prior N(0, tau^2)."""
    w = tau ** 2 / (tau ** 2 + se ** 2)
    return spread * w, w


def mde_analytic(sd_h, n_on, n_off, alpha=0.05, power=0.80):
    se = sd_h * math.sqrt(1 / n_on + 1 / n_off)
    return (stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)) * se
