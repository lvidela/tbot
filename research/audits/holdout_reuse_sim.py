"""Audit measurement A3 -- how much protection does the two-stage (discovery -> holdout) gate
give when the holdout is reused and hypothesis choice can see holdout-period outcomes?

Pure simulation under a GLOBAL NULL (no characteristic has any true effect in any period), so
every pass is a false positive. Mirrors the gate used by X1/X4 (research/x4_lowvol/
PREREGISTRATION.md): discovery two-sided p < 0.0125 (Bonferroni over 4) in the registered
direction, then holdout one-sided p < 0.05 in the same direction.

Scenarios (K candidate hypotheses available to the agent at registration time):
  honest          registers a candidate chosen without looking at either period
  holdout_peek    sees a noisy view of every candidate's HOLDOUT statistic (e.g. a previous
                  study's holdout tables on the same 2024-26 window) and registers the one that
                  looks strongest, in the direction it points
  both_peek       sees a noisy view of both periods (e.g. an LLM whose training data covers the
                  whole sample, or a researcher who has browsed the data before registering)
peek_noise is the sd of the view's error relative to the statistic's own sd (0 = sees it exactly).

Usage: python3 research/audits/holdout_reuse_sim.py   (seeded, deterministic, ~20s)
"""
import json, os, time
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "holdout_reuse_sim.json")
Z_DISC = 2.4977      # one-sided equivalent of two-sided 0.0125 with the sign required
Z_HOLD = 1.6449      # one-sided 0.05
SIMS = 200_000


def run(rng, K, mode, peek_noise):
    zd = rng.standard_normal((SIMS, K))
    zh = rng.standard_normal((SIMS, K))
    if mode == "honest":
        k = np.zeros(SIMS, dtype=int)
        sign = np.where(rng.random(SIMS) < 0.5, 1.0, -1.0)
    else:
        view = zh.copy() if mode == "holdout_peek" else (zd + zh) / np.sqrt(2)
        view = view + peek_noise * rng.standard_normal((SIMS, K))
        k = np.abs(view).argmax(1)
        sign = np.sign(view[np.arange(SIMS), k])
    d = sign * zd[np.arange(SIMS), k]
    h = sign * zh[np.arange(SIMS), k]
    pass_d, pass_h = d > Z_DISC, h > Z_HOLD
    return dict(p_discovery_pass=float(pass_d.mean()), p_holdout_pass=float(pass_h.mean()),
                p_false_positive=float((pass_d & pass_h).mean()))


def main():
    rng = np.random.default_rng(20260925)
    out = dict(generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), sims=SIMS,
               gate="discovery one-sided z>2.498 AND holdout one-sided z>1.645, same sign",
               results=[])
    for K in (5, 20):
        out["results"].append(dict(K=K, mode="honest", peek_noise=None, **run(rng, K, "honest", 0)))
        for mode in ("holdout_peek", "both_peek"):
            for noise in (0.0, 0.5, 1.0, 2.0):
                out["results"].append(dict(K=K, mode=mode, peek_noise=noise,
                                           **run(rng, K, mode, noise)))
    # program-level: probability of >=1 false POSITIVE over N studies
    for r in out["results"]:
        r["p_any_false_positive_10_studies"] = 1 - (1 - r["p_false_positive"]) ** 10
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=2)
    print(f"{'K':>3} {'mode':<13}{'noise':>6}{'P(disc)':>10}{'P(hold)':>10}{'P(FP)':>10}{'P(>=1 FP /10)':>15}")
    for r in out["results"]:
        print(f"{r['K']:>3} {r['mode']:<13}{str(r['peek_noise']):>6}{r['p_discovery_pass']:>10.4f}"
              f"{r['p_holdout_pass']:>10.4f}{r['p_false_positive']:>10.5f}"
              f"{r['p_any_false_positive_10_studies']:>15.4f}")


if __name__ == "__main__":
    main()
