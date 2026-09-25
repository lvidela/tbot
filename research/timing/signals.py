"""Pre-registered signals S1-S6 (research/timing/PREREGISTRATION.md section 2).

Each function returns a float Series aligned to the input index: 1.0 = ON (hold LINK),
0.0 = OFF (hold USD), NaN = not yet computable (warm-up). Every value at date t uses data up
to and including t only; tests/test_timing.py pins the no-look-ahead property.
"""
import numpy as np
import pandas as pd

DEFAULTS = {
    "S1": {"n": 200},
    "S2": {"n": 50},
    "S3": {"n": 50},
    "S4": {"n": 90, "dd": -0.30},
    "S5": {"n": 20, "ref": 365, "mult": 1.5},
    "S6": {"n": 7, "ref": 365, "q": 0.90},
}
NEUTRAL = {"S4": {"dd": 0.0}, "S5": {"mult": 1.0}, "S6": {"q": 0.5}}


def _onoff(cond, valid):
    return cond.astype(float).where(valid)


def sma_trend(close, n):
    sma = close.rolling(n, min_periods=n).mean()
    return _onoff(close > sma, sma.notna() & close.notna())


def no_crash(close, n, dd):
    peak = close.rolling(n, min_periods=n).max()
    draw = close / peak - 1
    return _onoff(draw > dd, draw.notna())


def calm_vol(close, n, ref, mult):
    lr = np.log(close).diff()
    vol = lr.rolling(n, min_periods=n).std()
    med = vol.rolling(ref, min_periods=ref).median()
    return _onoff(vol <= mult * med, med.notna() & vol.notna())


def funding_not_crowded(funding, n, ref, q):
    f = funding.rolling(n, min_periods=n).mean()
    thr = f.rolling(ref, min_periods=ref).quantile(q)
    return _onoff(f <= thr, thr.notna() & f.notna())


def compute(link, btc, funding=None, params=None):
    """Return DataFrame of S1..S6 on link's index. `params` overrides DEFAULTS per signal."""
    p = {k: {**v, **((params or {}).get(k, {}))} for k, v in DEFAULTS.items()}
    btc = btc.reindex(link.index)
    out = {
        "S1": sma_trend(btc, p["S1"]["n"]),
        "S2": sma_trend(btc, p["S2"]["n"]),
        "S3": sma_trend(link, p["S3"]["n"]),
        "S4": no_crash(link, p["S4"]["n"], p["S4"]["dd"]),
        "S5": calm_vol(link, p["S5"]["n"], p["S5"]["ref"], p["S5"]["mult"]),
    }
    if funding is not None:
        out["S6"] = funding_not_crowded(funding.reindex(link.index), p["S6"]["n"],
                                        p["S6"]["ref"], p["S6"]["q"])
    else:
        out["S6"] = pd.Series(np.nan, index=link.index)
    return pd.DataFrame(out)


def perturbations(sig):
    """The four pre-registered perturbations for one signal: lookback x0.7/x1.3 and the
    threshold moved +/- 1/3 of its distance from neutral (S1-S3 have no threshold, so their
    lookback of the SMA is perturbed and the '1/3' pair uses x0.85/x1.15)."""
    d = DEFAULTS[sig]
    out = [{"n": max(2, round(d["n"] * 0.7))}, {"n": round(d["n"] * 1.3)}]
    if sig in NEUTRAL:
        (k, neutral), = NEUTRAL[sig].items()
        gap = d[k] - neutral
        outward = d[k] + gap / 3
        if sig == "S6":  # a quantile cannot exceed 1: move 1/3 of the way to 1 (amendment A4)
            outward = d[k] + (1 - d[k]) / 3
        out += [{k: d[k] - gap / 3}, {k: outward}]
    else:
        out += [{"n": round(d["n"] * 0.85)}, {"n": round(d["n"] * 1.15)}]
    return out
