"""Execute pre-registration T1 on cached data. Refuses to run without the primary series.

Order is fixed by the pre-registration: coverage + cross-check -> in-sample table (written to
disk first) -> holdout -> sub-periods -> ETH/SOL replication -> perturbations -> execution lag
and taker cost -> family-wise permutation -> labels -> decision analysis.

Run: python3 research/timing/fetch.py && python3 research/timing/run.py [--perm 2000]
Outputs: research/timing/results/*.json and results/REPORT.md
"""
import datetime as dt
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data as D  # noqa: E402
import evaluate as E  # noqa: E402
import signals as S  # noqa: E402

OUT = os.environ.get("T1_OUT_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
HORIZONS = (5, 10, 20)
SIGS = ("S1", "S2", "S3", "S4", "S5", "S6")
HOLDOUT_START = pd.Timestamp("2024-01-01", tz="UTC")
END = pd.Timestamp("2026-09-24", tz="UTC")
SUBPERIODS = {"2019-21": ("2019-01-01", "2021-12-31"), "2022-23": ("2022-01-01", "2023-12-31"),
              "2024-26": ("2024-01-01", "2026-09-24")}
TAUS = (0.015, 0.03, 0.06)


def _dump(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(obj, f, indent=1, default=lambda o: float(o) if isinstance(o, np.floating) else str(o))


def _mask(index, lo, hi):
    return np.asarray((index >= pd.Timestamp(lo, tz="UTC")) & (index <= pd.Timestamp(hi, tz="UTC")))


def load():
    series = {}
    for a in ("LINK", "BTC", "ETH", "SOL"):
        for src in ("coinbase", "binance", "kraken"):
            s = D.closes(f"{src}_{a}_1d")
            if s is not None:
                series[(src, a)] = s
    fund = D.funding_daily("binance_LINK_funding")
    fund_okx = D.funding_daily("okx_LINK_funding")
    return series, fund, fund_okx


def table(close, sigdf, mask=None, lag=0, cost=E.MAKER_LEG):
    rows = {}
    for sg in SIGS:
        if sigdf[sg].notna().sum() < 200:
            continue
        for h in HORIZONS:
            r = E.evaluate(close.values, sigdf[sg].values, h, lag=lag, cost_leg=cost, dates_mask=mask)
            if r:
                rows[f"{sg}_h{h}"] = r
    return rows


def main():
    n_perm = int(sys.argv[sys.argv.index("--perm") + 1]) if "--perm" in sys.argv else 2000
    series, fund, fund_okx = load()
    if ("coinbase", "LINK") not in series or ("coinbase", "BTC") not in series:
        sys.exit("Primary series missing (research/data/raw/coinbase_{LINK,BTC}_1d.json). "
                 "Run fetch.py from an environment whose network policy allows the exchange hosts.")
    report = {"run_at": dt.datetime.now(dt.timezone.utc).isoformat(), "provenance": {}}
    for (src, a) in series:
        report["provenance"][f"{src}_{a}"] = D.load_raw(f"{src}_{a}_1d")[0]

    # 1. cross-check
    cc = {}
    for a in ("LINK", "BTC", "ETH", "SOL"):
        for other in ("binance", "kraken"):
            if ("coinbase", a) in series and (other, a) in series:
                summ, flagged = D.crosscheck(series[("coinbase", a)], series[(other, a)])
                summ["flagged_days"] = [str(i.date()) for i in flagged.index[:50]]
                cc[f"coinbase_vs_{other}_{a}"] = summ
    if fund is not None and fund_okx is not None:
        j = pd.concat({"binance": fund, "okx": fund_okx}, axis=1).dropna()
        cc["funding_binance_vs_okx"] = {"n_common": len(j), "corr": float(j.corr().iloc[0, 1]),
                                       "median_abs_diff": float((j.iloc[:, 0] - j.iloc[:, 1]).abs().median())}
    _dump("crosscheck.json", cc)

    link = series[("coinbase", "LINK")].loc[:END]
    btc = series[("coinbase", "BTC")]
    sig = S.compute(link, btc, fund)
    idx = link.index

    # 2. in-sample first, written before the holdout is computed
    ins = table(link, sig, mask=np.asarray(idx < HOLDOUT_START))
    _dump("in_sample.json", ins)
    # 3. full sample + holdout
    full = table(link, sig)
    hold = table(link, sig, mask=np.asarray(idx >= HOLDOUT_START))
    _dump("full.json", full)
    _dump("holdout.json", hold)
    # 4. sub-periods
    subs = {k: table(link, sig, mask=_mask(idx, *v)) for k, v in SUBPERIODS.items()}
    _dump("subperiods.json", subs)
    # 5. replication on ETH / SOL (amendment A1 in PREREGISTRATION.md)
    rep = {}
    for a in ("ETH", "SOL"):
        if ("coinbase", a) not in series:
            continue
        px = series[("coinbase", a)].loc[:END]
        sa = S.compute(px, btc, None)
        rep[a] = table(px, sa)
    _dump("replication.json", rep)
    # 6. perturbations
    pert = {}
    for sg in SIGS:
        pert[sg] = []
        for pp in S.perturbations(sg):
            sd = S.compute(link, btc, fund, {sg: pp})
            pert[sg].append({"params": pp, **{f"h{h}": (E.evaluate(link.values, sd[sg].values, h) or {}).get("t")
                                              for h in HORIZONS}})
    _dump("perturbations.json", pert)
    # 7. execution lag and taker cost
    _dump("lag1.json", table(link, sig, lag=1))
    _dump("taker.json", table(link, sig, cost=E.TAKER_LEG))
    # 8. family-wise permutation
    sigmap = {sg: sig[sg].values for sg in SIGS if sig[sg].notna().sum() >= 200}
    perm = E.family_permutation(link.values, sigmap, HORIZONS, n_perm=n_perm)
    _dump("permutation.json", perm)

    # 9. labels per the pre-registered rule (section 5)
    labels = {}
    for sg in SIGS:
        keys = [f"{sg}_h{h}" for h in HORIZONS if f"{sg}_h{h}" in full]
        if not keys:
            labels[sg] = "NOT RUN (no data)"
            continue
        passed = [k for k in keys if full[k]["t"] >= full[k]["t_bonf"]]
        a = bool(passed)
        b = perm["p_family"] < 0.05
        best = max(keys, key=lambda k: full[k]["t"])
        c = best in hold and hold[best]["spread"] > 0 and hold[best]["excess_vs_hold_link"] > 0
        d = sum(1 for s in subs.values() if best in s and s[best]["spread"] > 0) >= 2
        if sg == "S6":
            e = None  # waived, amendment A1
        else:
            e = any(best in rep.get(x, {}) and rep[x][best]["spread"] > 0 for x in ("ETH", "SOL"))
        hk = f"h{best.split('_h')[1]}"
        f = sum(1 for x in pert[sg] if (x.get(hk) or 0) > 0) >= 3
        crit = {"a": bool(a), "b": bool(b), "c": bool(c), "d": bool(d), "e": None if e is None else bool(e), "f": bool(f)}
        if a and b and c and d and e is not False and f:
            lab = "POSITIVE"
        elif a or b:
            lab = "REQUIRES VALIDATION"
        elif all(full[k]["mde_bonf"] <= 0.03 for k in keys if k.endswith("_h20")):
            lab = "NEGATIVE"
        else:
            lab = "INCONCLUSIVE"
        labels[sg] = {"label": lab, "criteria": crit, "best": best}
    _dump("labels.json", labels)

    # 10. decision analysis at the last date (section 6), h = 20
    last = sig.dropna(how="all").index[-1]
    fwd20 = (link.shift(-20) / link - 1).dropna()
    nonov = fwd20.iloc[::20]
    uncond = float(nonov.mean())
    dec = {"as_of": str(last.date()), "uncond_20d_mean": uncond,
           "uncond_20d_se": float(nonov.std(ddof=1) / np.sqrt(len(nonov))), "n_uncond": len(nonov),
           "states": {}, "by_tau": {}}
    for sg in SIGS:
        k = f"{sg}_h20"
        if k not in full or np.isnan(sig.loc[last, sg]):
            continue
        dec["states"][sg] = int(sig.loc[last, sg])
    for tau in TAUS:
        tilt = 0.0
        for sg, st in dec["states"].items():
            r = full[f"{sg}_h20"]
            shr, w = E.shrink(r["spread"], r["se"], tau)
            p_on = r["n_on"] / (r["n_on"] + r["n_off"])
            # deviation of the current state's mean from the unconditional mean
            tilt_sg = shr * (1 - p_on) if st == 1 else -shr * p_on
            dec.setdefault("per_signal", {}).setdefault(str(tau), {})[sg] = tilt_sg
            tilt = tilt_sg if abs(tilt_sg) > abs(tilt) else tilt  # signals are correlated: use the
            # single largest shrunk tilt, not the sum (summing would count one market state 6x)
        fc = uncond + tilt
        dec["by_tau"][str(tau)] = {"forecast_20d": fc, "exit_to_usd": bool(fc < -E.MAKER_LEG)}
    _dump("decision.json", dec)
    print(json.dumps({"labels": labels, "permutation": perm, "decision": dec}, indent=1, default=str))


if __name__ == "__main__":
    main()
