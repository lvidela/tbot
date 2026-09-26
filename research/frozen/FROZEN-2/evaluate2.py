"""FROZEN-2 evaluator (FROZEN: sha256 in FREEZE.json).

  python3 research/frozen/FROZEN-2/evaluate2.py --reason "scheduled review 2027-03-26"

Refuses on a hash mismatch (spec.json, entrants.py, evaluate2.py, universe.json), before the first review
date, or once the query budget is spent. Logs every call to research/frozen/ACCESS.jsonl before computing.
Uses closes.jsonl (append-only archive) plus a fresh Kraken public fetch; outcome periods start at the first
Monday after freeze_ts. Prints only the pre-registered statistics.
"""
import datetime as dt
import hashlib
import importlib.util
import json
import os
import sys

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ACCESS = os.path.join(HERE, "..", "ACCESS.jsonl")
EXP = "FROZEN-2"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load():
    spec = json.load(open(os.path.join(HERE, "spec.json")))
    fz = json.load(open(os.path.join(HERE, "FREEZE.json")))
    for n in ("spec.json", "entrants.py", "evaluate2.py", "universe.json"):
        if sha(os.path.join(HERE, n)) != fz["sha256"][n]:
            raise SystemExit(f"HASH MISMATCH on {n}: {EXP} is VOID for this run")
    s = importlib.util.spec_from_file_location("f2e", os.path.join(HERE, "entrants.py"))
    ent = importlib.util.module_from_spec(s)
    s.loader.exec_module(ent)
    return spec, fz, ent


def closes_from_archive():
    out = {}
    p = os.path.join(HERE, "closes.jsonl")
    if os.path.exists(p):
        for line in open(p):
            if line.strip():
                r = json.loads(line)
                if r.get("t") is not None:
                    out.setdefault(r["pair"], {})[int(r["t"])] = float(r["close"])
    return out


def fresh(pairs):
    import requests
    out = {}
    for p in pairs:
        try:
            r = requests.get("https://api.kraken.com/0/public/OHLC", params={"pair": p, "interval": 1440}, timeout=30).json()
            if not r.get("error"):
                key = next(k for k in r["result"] if k != "last")
                out[p] = {int(x[0]): float(x[4]) for x in r["result"][key][:-1]}
        except Exception:
            pass
    return out


def summary(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 3:
        return {"n": n}
    m, se = float(x.mean()), float(x.std(ddof=1) / np.sqrt(n))
    t = m / se if se > 0 else float("nan")
    return {"n": n, "mean": m, "median": float(np.median(x)), "se": se, "mde": 2.8 * se,
            "p_one_sided_pos": float(stats.t.sf(t, n - 1)), "p_one_sided_neg": float(stats.t.cdf(t, n - 1)),
            "ci95": [m - 1.96 * se, m + 1.96 * se]}


def verdict(s, min_n):
    if s.get("n", 0) < min_n:
        return "INSUFFICIENT_N"
    if s["p_one_sided_pos"] < 0.05 and s["mean"] >= s["mde"]:
        return "POSITIVE_EV"
    if s["ci95"][1] < 0:
        return "NEGATIVE_EV"
    return "UNRESOLVED"


def run(spec, fz, ent, closes, now_ts):
    t0 = ent.first_monday_after(fz["freeze_ts"])
    per = ent.periods(closes, spec["universe_pairs"], t0, now_ts)
    res = {}
    for k in ("q5_net", "q1_net", "spread_q5_q1", "q5_median_asset_minus_link"):
        s = summary([p[k] for p in per])
        if k in ("q5_net", "q1_net"):
            s["verdict"] = verdict(s, spec["min_n"])
        res[k] = s
    return res


def main():
    reason = sys.argv[sys.argv.index("--reason") + 1] if "--reason" in sys.argv else ""
    spec, fz, ent = load()
    now = dt.datetime.now(dt.timezone.utc)
    prior = [a for a in (json.loads(x) for x in open(ACCESS) if x.strip())
             if a.get("experiment") == EXP and not a.get("selftest")] if os.path.exists(ACCESS) else []
    entry = {"ts": now.isoformat(), "experiment": EXP, "reason": reason, "query_number": len(prior) + 1,
             "budget": spec["query_budget"]}
    with open(ACCESS, "a") as f:
        if len(prior) >= spec["query_budget"]:
            f.write(json.dumps({**entry, "refused": "budget exhausted"}) + "\n")
            raise SystemExit("query budget exhausted")
        if now.date().isoformat() < spec["review_dates"][0]:
            f.write(json.dumps({**entry, "refused": "before first review date"}) + "\n")
            raise SystemExit(f"refused: first review date is {spec['review_dates'][0]}")
        f.write(json.dumps(entry) + "\n")
    closes = closes_from_archive()
    for p, s in fresh(spec["universe_pairs"]).items():
        closes.setdefault(p, {}).update(s)
    res = run(spec, fz, ent, closes, int(now.timestamp()) // 86400 * 86400)
    for k, v in res.items():
        print(k, {a: (round(b, 5) if isinstance(b, float) else b) for a, b in v.items() if a != "ci95"})


if __name__ == "__main__":
    main()
