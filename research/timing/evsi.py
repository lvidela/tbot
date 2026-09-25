"""Expected value of sample information (EVSI) of running T1, in USD on the live account.

Decision (one-shot, ~20 days left): stay in LINK, or exit to USD and stay (one maker leg, c).
Unknown: m = E[LINK 20d return | current signal state] = mu + tilt.
  mu   : unconditional 20d drift,  prior N(mu0, s_mu^2)
  tilt : deviation of the current state, prior N(0, (tau * k)^2) with k = max(P_ON, 1 - P_ON)
         (the tilt is spread * (1 - P_ON) or spread * P_ON; k is the larger, so this is generous)
Data from T1 (normal approx.): mu estimated with SE_mu, spread with SE_d (tilt SE = k * SE_d).

Without data you exit iff mu0 < -c. With data you exit iff posterior mean < -c. For a normal
preposterior with sd v, EVSI = ACCOUNT * E[max(-c - m, 0)] - value of the prior-optimal action,
which is the standard closed form below. SE values are taken from power.py (median simulated
h=20 SE on the full sample, daily sd 4.5%, ~2440 days).

Run: python3 research/timing/evsi.py
"""
import json
import math
import os

from scipy import stats

ACCOUNT = 58.94
C = 0.0046                 # one maker leg incl. adverse selection
SE_D = 0.038               # power.py, full sample h=20
SE_MU = 0.045 * math.sqrt(20) / math.sqrt(2440 / 20)   # iid approx, ~1.8%
K = 0.55


def _gain(mean, v):
    """E[max(-c - m, 0)] - max(-c - mean, 0) for m ~ N(mean, v^2): value of being able to
    choose after observing m instead of before."""
    a = -C - mean
    if v <= 0:
        return 0.0
    z = a / v
    return a * stats.norm.cdf(z) + v * stats.norm.pdf(z) - max(a, 0.0)


def prepost_sd(prior_sd, se):
    """sd of the posterior mean before seeing data = sqrt(prior var - posterior var)."""
    post_var = 1 / (1 / prior_sd ** 2 + 1 / se ** 2)
    return math.sqrt(max(prior_sd ** 2 - post_var, 0.0))


def main():
    rows = []
    for mu0 in (0.0, 0.01, 0.02):
        for s_mu in (0.02, 0.03, 0.05):
            for tau in (0.015, 0.03, 0.06):
                v_mu = prepost_sd(s_mu, SE_MU)
                v_tilt = prepost_sd(tau * K, SE_D * K)
                rows.append({
                    "mu0": mu0, "s_mu": s_mu, "tau": tau,
                    "evsi_total_usd": ACCOUNT * _gain(mu0, math.hypot(v_mu, v_tilt)),
                    "evsi_signals_only_usd": ACCOUNT * _gain(mu0, v_tilt),
                    "evsi_drift_only_usd": ACCOUNT * _gain(mu0, v_mu),
                })
    for r in rows:
        print(f"mu0={r['mu0']:+.2f} s_mu={r['s_mu']:.2f} tau={r['tau']:.3f}  EVSI total ${r['evsi_total_usd']:.2f}"
              f"  signals-only ${r['evsi_signals_only_usd']:.2f}  drift-only ${r['evsi_drift_only_usd']:.2f}")
    sig = [r["evsi_signals_only_usd"] for r in rows]
    tot = [r["evsi_total_usd"] for r in rows]
    print(f"\nsignals-only EVSI range ${min(sig):.2f}-${max(sig):.2f}; total ${min(tot):.2f}-${max(tot):.2f}"
          f"  (SE_mu {SE_MU:.4f}, SE_d {SE_D})")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "evsi.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump({"account": ACCOUNT, "cost_leg": C, "se_d": SE_D, "se_mu": SE_MU, "rows": rows}, f, indent=1)


if __name__ == "__main__":
    main()
