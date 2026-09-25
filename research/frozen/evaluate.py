"""Frozen forward-holdout evaluator (audit P1 / C2 / C6).

  python3 research/frozen/evaluate.py FROZEN-1 --reason "scheduled review 2026-12-26"

Rules, enforced here:
- Refuses to run if the sha256 of spec.json, entrants.py or this file differs from FREEZE.json.
- Uses ONLY outcome bars that open at or after the first UTC midnight following freeze_ts. Signal
  lookbacks may use earlier bars.
- Appends every call to research/frozen/ACCESS.jsonl before computing anything. Refuses once the query
  budget is spent, or before the first review date (except --selftest on synthetic data).
- Prints ONLY the pre-registered statistics: n, mean, one-sided p, Holm p, MDE, verdict.
"""
import datetime as dt
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ACCESS = os.path.join(HERE, "ACCESS.jsonl")
DAY = 86400


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def load(exp):
    d = os.path.join(HERE, exp)
    spec = json.load(open(os.path.join(d, "spec.json")))
    freeze = json.load(open(os.path.join(d, "FREEZE.json")))
    for name, path in (("spec.json", os.path.join(d, "spec.json")), ("entrants.py", os.path.join(d, "entrants.py")),
                       ("evaluate.py", os.path.abspath(__file__))):
        if sha256(path) != freeze["sha256"][name]:
            raise SystemExit(f"HASH MISMATCH on {name}: experiment {exp} is VOID for this run")
    spec_mod = importlib.util.spec_from_file_location(f"{exp}_entrants", os.path.join(d, "entrants.py"))
    ent = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(ent)
    return spec, freeze, ent


def log_access(entry):
    with open(ACCESS, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def accesses(exp):
    if not os.path.exists(ACCESS):
        return []
    return [a for a in (json.loads(x) for x in open(ACCESS) if x.strip()) if a.get("experiment") == exp and not a.get("selftest")]


def fetch_kraken(pairs):
    import requests
    panel = {}
    for p in pairs:
        r = requests.get("https://api.kraken.com/0/public/OHLC", params={"pair": p, "interval": 1440}, timeout=30).json()
        if r.get("error"):
            continue
        key = next(k for k in r["result"] if k != "last")
        rows = r["result"][key][:-1]                      # drop the in-progress bar
        panel[p] = {int(x[0]): float(x[4]) for x in rows}
    return panel


def mask_outcomes(panel, first_bar, now_bar):
    """Keep all bars (signal lookback needs them) but evaluation windows are restricted by t0 = first_bar."""
    return {p: {t: c for t, c in s.items() if t < now_bar} for p, s in panel.items()}


def one_sided(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 3:
        return {"n": n}
    m, se = float(x.mean()), float(x.std(ddof=1) / np.sqrt(n))
    t = m / se if se > 0 else float("nan")
    return {"n": n, "mean": m, "se": se, "p_t": float(stats.t.sf(t, n - 1)), "mde": 2.8 * se,
            "ci95_upper": m + 1.96 * se}


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out, running = [None] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        out[i] = running
    return out


def run(spec, freeze, ent, panel, ledger_rows, now_ts, rng_seed=0):
    rng = np.random.default_rng(rng_seed)
    t0 = (int(freeze["freeze_ts"]) // DAY + 1) * DAY
    uni = spec["universe_kraken_pairs"]
    res = {}
    # A1
    win = ent.a1_s2_windows(panel, t0, now_ts)
    diff, e = ent.a1_statistic(win)
    r = one_sided(diff) if diff is not None else {"n": 0}
    res["A1_S2_h5_timing_minus_static"] = {**r, "p": r.get("p_t"), "exposure": e}
    # A2
    per = ent.a2_periods(panel, uni, t0, now_ts)
    ex = ent.a2_excess(per)
    r = one_sided(ex)
    if r["n"] >= 3:
        null = [ent.a2_excess(per, lambda i, rets: list(rng.choice(sorted(rets), 5, replace=False))).mean()
                for _ in range(spec["null_draws"])]
        r["p_random5"] = float(np.mean(np.array(null) >= r["mean"]))
        r["p"] = max(r["p_t"], r["p_random5"])
    res["A2_X4_lowvol5_excess_vs_LINK"] = r
    # B1 / B2
    rows = ent.b_rows(ledger_rows, panel, uni, freeze["freeze_ts"])
    for name, key in (("B1_tactical_candidates_all", None), ("B2_tactical_candidates_X4_lowvol", lambda x: x["lowvol"])):
        cm = ent.cluster_means(rows, key)
        r = one_sided(list(cm.values()))
        if r["n"] >= 3:
            sizes = {t: sum(1 for x in rows if x["t"] == t and (key is None or key(x))) for t in cm}
            null = []
            for _ in range(spec["null_draws"]):
                vals = []
                for t, k in sizes.items():
                    cands = [p for p in uni if p in panel and ent.fwd_simple(panel[p], t, 3) is not None]
                    pk = rng.choice(cands, min(k, len(cands)), replace=False)
                    rl = ent.fwd_simple(panel["LINKUSD"], t, 3)
                    vals.append(float(np.mean([ent.fwd_simple(panel[p], t, 3) - rl - ent.TACTICAL_RT for p in pk])))
                null.append(np.mean(vals))
            r["p_random_entry"] = float(np.mean(np.array(null) >= r["mean"]))
            r["p"] = max(r["p_t"], r["p_random_entry"])
        res[name] = r
    names = [k for k, v in res.items() if v.get("p") is not None and v.get("n", 0) >= spec["min_n"]]
    for k, hp in zip(names, holm([res[k]["p"] for k in names])):
        res[k]["p_holm"] = hp
    for k, v in res.items():
        if v.get("n", 0) < spec["min_n"]:
            v["verdict"] = "INSUFFICIENT_N"
        elif v.get("p_holm", 1) < 0.05 and v["mean"] >= v["mde"]:
            v["verdict"] = "SUCCESS"
        elif v["ci95_upper"] < 0 and v["mde"] <= spec["retire_mde_max"]:
            v["verdict"] = "RETIRE"
        else:
            v["verdict"] = "CONTINUE"
    return res


def main():
    exp = sys.argv[1]
    selftest = "--selftest" in sys.argv
    reason = sys.argv[sys.argv.index("--reason") + 1] if "--reason" in sys.argv else ""
    spec, freeze, ent = load(exp)
    now = dt.datetime.now(dt.timezone.utc)
    prior = accesses(exp)
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    except Exception:
        commit = None
    entry = {"ts": now.isoformat(), "experiment": exp, "reason": reason, "commit": commit, "selftest": selftest,
             "query_number": len(prior) + 1, "budget": spec["query_budget"]}
    if not selftest:
        if len(prior) >= spec["query_budget"]:
            log_access({**entry, "refused": "budget exhausted"})
            raise SystemExit("query budget exhausted")
        if now.date().isoformat() < spec["review_dates"][0]:
            log_access({**entry, "refused": "before first review date"})
            raise SystemExit(f"refused: first review date is {spec['review_dates'][0]}")
    log_access(entry)
    if selftest:
        raise SystemExit("selftest runs only via test_frozen.py")
    panel = fetch_kraken(spec["universe_kraken_pairs"] + ["XBTUSD", "LINKUSD"])
    now_bar = int(now.timestamp()) // DAY * DAY
    panel = mask_outcomes(panel, None, now_bar)
    ledger = []
    for f in spec["ledger_files"]:
        p = os.path.join(HERE, "..", "..", f)
        if os.path.exists(p):
            d = json.load(open(p))
            ledger += d if isinstance(d, list) else next((v for v in d.values() if isinstance(v, list)), [])
    res = run(spec, freeze, ent, panel, ledger, now_bar)
    for k, v in res.items():
        print(k, {a: (round(b, 5) if isinstance(b, float) else b) for a, b in v.items()
                  if a in ("n", "mean", "p", "p_holm", "mde", "verdict", "exposure")})


if __name__ == "__main__":
    main()
