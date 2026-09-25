"""Program-level trial ledger (audit P2 / control C4).

research/TRIALS.jsonl is APPEND-ONLY: one row per formal test (or one aggregated row per
older study, marked backfilled + aggregated, with n_tests). This tool never rewrites it.

  python3 research/trials.py                 program count K and Bonferroni / Holm thresholds
  python3 research/trials.py --check P       does a p-value clear the program-level bar now?
  python3 research/trials.py --backfill      one-time: append the 2026-09-25 back-fill (refuses if rows exist)
"""
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "TRIALS.jsonl")
ALPHA = 0.05


def rows(path=LEDGER):
    if not os.path.exists(path):
        return []
    return [json.loads(line) for line in open(path) if line.strip()]


def count(rs):
    return sum(int(r.get("n_tests", 1)) for r in rs)


def append(new, path=LEDGER):
    with open(path, "a") as f:
        for r in new:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def threshold(k, alpha=ALPHA):
    return alpha / max(k, 1)


def backfill_rows():
    """Aggregated rows for studies before the ledger existed (audit E4 tally), then per-test rows for
    the cloud studies whose p-values are in committed results files."""
    now = "2026-09-25"
    agg = [("R1/R2", "event triggers vol_expansion / volume_spike", 4, "live", False),
           ("R3", "cross-sectional momentum IC 12 + grid 36", 48, "live", False),
           ("R4", "LINK mean reversion autocorrelation", 3, "live", False),
           ("R6/Q1", "confluence subsets 31x3", 93, "live", False),
           ("R7/Q2", "confluence slope in success probability", 3, "live", False),
           ("R9", "reversal / momentum 36 cells", 36, "live", False),
           ("R10", "trailing-stop asymmetry", 6, "live", False),
           ("IdeaB", "majors lead/lag 16 combinations", 16, "live", False),
           ("R11", "micro-arbitrage mechanisms", 4, "live", False),
           ("R12", "weekly TSMOM 9 rules", 9, "live", False),
           ("R13", "LINK vs BTC/ETH drift", 2, "live", False),
           ("T1", "LINK/USD timing 6 signals x 3 horizons", 18, "cloud", True)]
    out = [{"id": f"{s}-agg", "study": s, "date": now, "hypothesis": h, "n_tests": n, "author": a,
            "pre_registered": pre, "backfilled": True, "aggregated": True, "p": None,
            "holdout_window": "2024-01-01..2026-09" if s in ("T1", "R12", "R13") else None,
            "prior_exposure": "unknown (backfilled)"} for s, h, n, a, pre in agg]

    def res(path):
        return json.load(open(os.path.join(HERE, path)))

    per = []
    x1 = res("x1_funding/results/discovery.json")["tests"]
    for k in ("P_ic_7d", "S-a_ic_28d", "S-b_ic_7d_last24h", "S-c_partial_ic_7d", "S-d_quintile_spread_low_minus_high"):
        per.append(("X1", k, x1[k]["p_two_sided"], "2020-01..2023-12", "2024-01..2026-09",
                    "none on this panel; T1 used 2024-26 holdout (LINK only)"))
    x4 = res("x4_lowvol/results/discovery.json")["tests"]
    for k in ("P_ic_vol", "S1_ic_beta", "S2_partial_ic_vol", "S3_quintile_spread_lowvol_minus_highvol"):
        per.append(("X4", k, x4[k]["p_two_sided"], "2020-01..2023-12", "2024-01..2026-08 (REUSED, pre-cutoff)",
                    "X1 holdout tables incl. vol-controlled partial IC, EW basket 0.16x (AU1)"))
    x4b = json.load(open(os.path.join(HERE, "x4b_kraken/results.json")))["primary"]
    per.append(("X4b", "P_ic_vol_kraken", x4b["p_one_sided_neg"], "2024-10..2026-09 (REUSED)", None,
                "X4 discovery and holdout results"))
    x3 = res("x3_capitulation/results/discovery.json")["primary_h3"]
    for k in ("P1_ew_excess", "P2_ic_crash_vs_fwd", "P3_link_excess"):
        per.append(("X3", k, x3[k]["p_two_sided"], "2020-03..2023-12", "2024-01..2026-09 (REUSED)",
                    "X1, X4 holdout tables on same panel"))
    x5 = res("x5_dvol/results/discovery.json")["primary"]
    for k in ("P_link_on_vrp", "S1_btc_on_vrp", "S2_ew_on_vrp", "S3_link_on_dvol"):
        per.append(("X5", k, x5[k]["p_two_sided"], "2021-10..2023-12", "2024-01..2026-08 (REUSED)",
                    "T1, X1, X3, X4 results over 2024-26"))
    x6 = res("x6_listing_age/results/discovery.json")["tests"]
    for k in ("P_partial_ic_age", "S1_ic_age", "S2_young_minus_rest"):
        per.append(("X6", k, x6[k]["p_two_sided"], "2020-01..2023-12", "2024-01..2026-08 (REUSED, pre-cutoff)",
                    "X4 discovery + holdout on same grid (AU1)"))
    for s, k, p, disc, hold, prior in per:
        out.append({"id": f"{s}-{k}", "study": s, "date": now, "hypothesis": k, "n_tests": 1, "author": "cloud",
                    "pre_registered": True, "backfilled": True, "aggregated": False, "stage": "discovery",
                    "p": p, "data_window": disc, "holdout_window": hold, "prior_exposure": prior,
                    "model_knowledge_cutoff": "2026-06 (Research Agent)"})
    return out


def main():
    rs = rows()
    if "--backfill" in sys.argv:
        if rs:
            raise SystemExit("ledger already has rows; backfill refused (append-only)")
        append(backfill_rows())
        rs = rows()
    k = count(rs)
    print(f"program formal tests K = {k}; Bonferroni alpha/K = {threshold(k):.2e} (alpha={ALPHA})")
    if "--check" in sys.argv:
        p = float(sys.argv[sys.argv.index("--check") + 1])
        print(f"p = {p:.2e} -> {'CLEARS' if p < threshold(k) else 'does NOT clear'} the program-level bar")
    ps = sorted((r["p"], r["id"]) for r in rs if r.get("p") is not None)
    print("per-test rows clearing the program-level Bonferroni bar:",
          [i for p, i in ps if p < threshold(k)] or "none")


if __name__ == "__main__":
    main()
