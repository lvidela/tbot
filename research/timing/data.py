"""Load cached raw data into daily pandas Series and cross-check exchanges.

Daily bars are labelled by their UTC open date; the value is that day's close (00:00 UTC next day).
"""
import json
import os

import numpy as np
import pandas as pd

from fetch import RAW


def load_raw(name):
    path = os.path.join(RAW, f"{name}.json")
    if not os.path.exists(path):
        return None, None
    with open(path) as f:
        d = json.load(f)
    return d["meta"], d["rows"]


def closes(name):
    meta, rows = load_raw(name)
    if rows is None:
        return None
    idx = pd.to_datetime([r[0] for r in rows], unit="s", utc=True).normalize()
    s = pd.Series([r[4] for r in rows], index=idx, name=name).astype(float)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s.asfreq("D")  # gaps become NaN, surfaced by crosscheck/coverage


def funding_daily(name):
    """Mean of the day's funding prints (per 8h rate), by UTC date."""
    meta, rows = load_raw(name)
    if rows is None:
        return None
    idx = pd.to_datetime([r[0] for r in rows], unit="s", utc=True)
    s = pd.Series([r[1] for r in rows], index=idx).astype(float)
    return s.groupby(s.index.normalize()).mean().asfreq("D")


def crosscheck(a, b, tol=0.02):
    """Compare two daily close series on their common dates.

    Returns summary dict and the DataFrame of flagged days (|log ratio| > tol). A USD vs USDT
    comparison also contains the USDT basis, which is reported separately (median log ratio).
    """
    df = pd.concat({"a": a, "b": b}, axis=1).dropna()
    lr = np.log(df["a"] / df["b"])
    flagged = df[lr.abs() > tol].assign(log_ratio=lr[lr.abs() > tol])
    ra, rb = np.log(df["a"]).diff(), np.log(df["b"]).diff()
    return {
        "n_common": int(len(df)),
        "first": str(df.index.min().date()) if len(df) else None,
        "last": str(df.index.max().date()) if len(df) else None,
        "median_log_ratio_bps": float(lr.median() * 1e4) if len(df) else None,
        "p99_abs_log_ratio_bps": float(lr.abs().quantile(0.99) * 1e4) if len(df) else None,
        "n_flagged": int(len(flagged)),
        "daily_return_corr": float(ra.corr(rb)) if len(df) > 2 else None,
    }, flagged
