"""V1: value-of-information screen of candidate research questions (see PREREGISTRATION.md).

V1a: EVPI (upper bound for any study) and EVSI (best study feasible now) in USD of final account
     value, for candidates C1-C9, at horizons H20 (to 2026-10-15) and H365 (open-ended bound).
V1b: minimum detectable effect of the forward ledgers vs accumulated days.

Scenarios (low / central / high) are fixed below before the first run. "low" and "high" mean
low / high *value of information*, not low / high parameter values.

No network. The only data read is research/tsmom/ohlc_long.json (Kraken public daily OHLC),
used for the V1b nuisance parameters.

Run: python3 research/voi/voi_screen.py
"""
import json
import math
import os

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
OHLC = os.path.join(HERE, "..", "tsmom", "ohlc_long.json")
OUT = os.path.join(HERE, "results", "voi.json")

A = 58.62            # account USD, STATE.md 2026-09-25 13:55Z
C1 = 0.0046          # maker leg incl. adverse selection (A1)
RT4 = 0.0183         # 4-leg tactical round trip (A1)
NOTIONAL = 13.0      # tactical position (F1)
HORIZONS = {"H20": 20, "H365": 365}
SCEN = ("low", "central", "high")
NEGLIGIBLE, MEANINGFUL = 0.05, 0.25


# ---------------------------------------------------------------- closed forms
def gain(mu, v, k):
    """E[max(m - k*c1, 0)] - max(mu - k*c1, 0) for m ~ N(mu, v^2): value per dollar of
    choosing after seeing m. (Standard normal-preposterior result; see timing/evsi.py.)"""
    a = mu - k * C1
    if v <= 0:
        return 0.0
    z = a / v
    return a * stats.norm.cdf(z) + v * stats.norm.pdf(z) - max(a, 0.0)


def prepost_sd(prior_sd, se):
    """sd of the posterior mean, before the data are seen."""
    if se is None or not math.isfinite(se):
        return 0.0
    post_var = 1 / (1 / prior_sd ** 2 + 1 / se ** 2)
    return math.sqrt(max(prior_sd ** 2 - post_var, 0.0))


def switch_value(mu_ann, sd_ann, se_ann, k, days):
    """EVPI / EVSI in USD for a one-off switch whose annual expected benefit is
    N(mu_ann, sd_ann^2). Parameter uncertainty scales linearly with horizon."""
    f = days / 365
    evpi = A * gain(mu_ann * f, sd_ann * f, k)
    evsi = A * gain(mu_ann * f, prepost_sd(sd_ann, se_ann) * f, k)
    return evpi, evsi


# ---------------------------------------------------------------- candidates
def c1_link_vs_usd(s, days):
    """Exit LINK to USD (1 leg). Benefit m = -(LINK expected return). Two components:
    (i) unconditional drift, prior mean mu_ann, sd sd_ann (T1 already absorbed);
    (ii) conditional timing tilt per 20-day window, sd tau, re-decided every 20 days.
    Feasible now: ~1 new day since T1, so SE of the annual drift from new data ~ daily sd*365
    (useless), and no new signal data."""
    mu_ann = {"low": 0.30, "central": 0.15, "high": 0.00}[s]
    sd_ann = {"low": 0.20, "central": 0.35, "high": 0.50}[s]
    tau20 = {"low": 0.005, "central": 0.01, "high": 0.02}[s]
    se_new = 0.04 * 365 / math.sqrt(1)
    evpi_d, evsi_d = switch_value(-mu_ann, sd_ann, se_new, 1, days)
    windows = max(days / 20, 1.0)
    mu20 = -mu_ann * 20 / 365
    evpi_t = A * windows * gain(mu20, tau20, 1)
    return evpi_d + evpi_t, evsi_d, "only ~1 new day since T1"


def c2_other_asset(s, days):
    """Switch LINK -> BTC/ETH (2 legs). Unknown annual expected-return difference, prior mean 0.
    Feasible now: no unused history (R13 used all of it). Also reported: EVSI of a
    hypothetical second, independent history as long as the existing one (SE 29%/yr) -- that
    data does not exist."""
    sd = {"low": 0.10, "central": 0.20, "high": 0.35}[s]
    evpi, evsi = switch_value(0.0, sd, None, 2, days)
    _, evsi_hyp = switch_value(0.0, sd, 0.29, 2, days)
    return evpi, evsi, f"no unused history; hypothetical extra history would be worth ${evsi_hyp:.2f}"


def c3_tactical_signal(s, days):
    """New tactical signal search. With prior prob pi a signal has true net edge e per trade,
    else it has zero gross edge (net -RT4). A backtest with SE = MDE/2.8 accepts if
    estimate > 1.96*SE (one test -- flatters it). Accepted signals are traded n times over
    the horizon (one 72h trade per 3 days, capped at 10 for H20 per F1).
    EVSI = pi*power*e*N*n - (1-pi)*alpha*RT4*N*n.  EVPI = pi*e*N*n."""
    pi = {"low": 0.02, "central": 0.05, "high": 0.15}[s]
    e = {"low": 0.005, "central": 0.01, "high": 0.02}[s]
    mde = {"low": 0.075, "central": 0.04, "high": 0.025}[s]
    n = min(days / 3, 10) if days <= 20 else days / 3
    se = mde / 2.8
    power = 1 - stats.norm.cdf(1.96 - e / se)
    alpha = 1 - stats.norm.cdf(1.96 + RT4 / se)   # null true net = -RT4
    evpi = pi * e * NOTIONAL * n
    evsi = pi * power * e * NOTIONAL * n - (1 - pi) * alpha * RT4 * NOTIONAL * n
    return evpi, evsi, f"power {power:.2f} at e={e:.1%}, MDE {mde:.1%}"


def c4_volatile_fills(s, days):
    """Maker fill quality in volatile regimes. Matters only if a tactical trade happens.
    EVPI <= P(trade) * n * N * E|misestimate of round-trip cost|. Not feasible in cloud
    (needs live fills); the live agent records it at zero research cost."""
    p = {"low": 0.1, "central": 0.25, "high": 0.5}[s]
    miss = {"low": 0.002, "central": 0.004, "high": 0.008}[s]
    n = min(days / 3, 10) if days <= 20 else days / 3
    return p * n * NOTIONAL * miss, 0.0, "live-only data"


def c5_switch_execution(s, days):
    """Execution timing of a one-off LINK<->X switch. EVPI = P(switch) * saving/leg * 2 * A.
    A public order-book study would recover at most half of it."""
    p = {"low": 0.05, "central": 0.10, "high": 0.30}[s] * (1 if days <= 20 else 3)
    p = min(p, 0.9)
    save = {"low": 0.0002, "central": 0.0005, "high": 0.0010}[s]
    evpi = p * save * 2 * A
    return evpi, 0.5 * evpi, "order-book sampling; also blocked by network policy here"


def c6_tail_event(s, days):
    """LINK-specific non-price tail event (delisting, exploit, oracle failure).
    Rate lam/yr, loss L of LINK value, fraction f avoidable by monitoring (prices gap).
    EVPI (foreknowledge) = lam*H*L*A ; monitoring value = lam*H*L*f*A. Not a statistical study."""
    lam = {"low": 0.01, "central": 0.03, "high": 0.06}[s]
    loss = {"low": 0.5, "central": 0.6, "high": 0.8}[s]
    f = {"low": 0.05, "central": 0.15, "high": 0.30}[s]
    h = days / 365
    return lam * h * loss * A, lam * h * loss * f * A, "monitoring task (live agent), not research"


def c7_partial(s, days):
    """Linear objective (expected USD) -> corner solutions; value is inside C1/C2."""
    return 0.0, 0.0, "zero by linearity of the objective"


def c8_derivatives(s, days):
    """Not actionable: Hard Rule 2 (spot only). Value to the live account is zero unless a
    researcher changes the rule."""
    return 0.0, 0.0, "not actionable without a researcher rule change"


CANDIDATES = {
    "C1 LINK vs USD (drift/timing)": c1_link_vs_usd,
    "C2 hold another asset": c2_other_asset,
    "C3 new tactical signal": c3_tactical_signal,
    "C4 volatile-regime fills": c4_volatile_fills,
    "C5 switch execution timing": c5_switch_execution,
    "C6 LINK tail-event monitoring": c6_tail_event,
    "C7 partial exposure": c7_partial,
    "C8 derivatives/hedging": c8_derivatives,
}


def label(v):
    return "NEGLIGIBLE" if v < NEGLIGIBLE else ("MEANINGFUL" if v >= MEANINGFUL else "MARGINAL")


# ---------------------------------------------------------------- V1b
def ledger_params(path=OHLC, h=3):
    """sigma_x: sd of h-day log return of an alt minus LINK; rho: mean pairwise correlation of
    those excess returns across alts. Non-overlapping windows, median over the h phases.
    Last (partial) bar dropped."""
    d = json.load(open(path))
    names = sorted(d)
    closes = {a: np.array([r[4] for r in d[a]["1440"][:-1]], float) for a in names}
    lengths = {len(v) for v in closes.values()}
    assert len(lengths) == 1, "series not aligned"
    lp = {a: np.log(v) for a, v in closes.items()}
    link_sd = float(np.std(np.diff(lp["LINKUSD"]), ddof=1))
    others = [a for a in names if a != "LINKUSD"]
    sig, rho = [], []
    for ph in range(h):
        idx = np.arange(ph, len(lp["LINKUSD"]), h)
        rl = np.diff(lp["LINKUSD"][idx])
        X = np.array([np.diff(lp[a][idx]) - rl for a in others])   # assets x windows
        sig.append(float(np.std(X, ddof=1)))
        c = np.corrcoef(X)
        rho.append(float(c[~np.eye(len(others), dtype=bool)].mean()))
    return {"sigma_x": float(np.median(sig)), "rho": float(np.median(rho)),
            "link_daily_sd": link_sd, "n_assets": len(others), "horizon_days": h,
            "bars": lengths.pop(), "per_phase_sigma": sig, "per_phase_rho": rho}


def mde(days, sigma_x, rho, m, h=3):
    n = days / h
    if n < 1:
        return float("inf")
    var = sigma_x ** 2 * (rho + (1 - rho) / m)
    return 2.80 * math.sqrt(var) / math.sqrt(n)


def days_to(target, sigma_x, rho, m, h=3):
    var = sigma_x ** 2 * (rho + (1 - rho) / m)
    return h * (2.80 * math.sqrt(var) / target) ** 2


def c9_ledgers(s, days, p):
    """Forward ledgers: accrue free in the live system. Value = C3-style gain if the ledger
    detects a true edge by mid-horizon and it is traded for the remaining half."""
    pi = {"low": 0.02, "central": 0.05, "high": 0.15}[s]
    e = {"low": 0.005, "central": 0.01, "high": 0.02}[s]
    m = {"low": 1, "central": 3, "high": 10}[s]
    half = days / 2
    se = mde(half, p["sigma_x"], p["rho"], m) / 2.8
    power = 1 - stats.norm.cdf(1.96 - e / se) if math.isfinite(se) else 0.0
    n = min(half / 3, 5) if days <= 20 else half / 3
    return pi * e * NOTIONAL * n, pi * power * e * NOTIONAL * n, f"power {power:.2f} by day {half:.0f}"


def main():
    p = ledger_params()
    res = {"params": {"A": A, "c1": C1, "rt4": RT4, "notional": NOTIONAL}, "ledger": p,
           "candidates": {}, "v1b": {}}
    fns = dict(CANDIDATES)
    fns["C9 forward ledgers"] = lambda s, d: c9_ledgers(s, d, p)
    print(f"{'candidate':34s} {'hz':5s} " + "  ".join(f"{x:>17s}" for x in SCEN) + "   label(central)")
    for name, fn in fns.items():
        res["candidates"][name] = {}
        for hz, days in HORIZONS.items():
            row = {s: dict(zip(("evpi", "evsi", "note"), fn(s, days))) for s in SCEN}
            row["label"] = label(row["central"]["evsi"])
            row["evpi_label"] = label(row["central"]["evpi"])
            res["candidates"][name][hz] = row
            cells = "  ".join(f"${row[s]['evpi']:6.2f}/${row[s]['evsi']:6.2f}" for s in SCEN)
            print(f"{name:34s} {hz:5s} {cells}   {row['label']}")
    print("(cells: EVPI / EVSI in USD)\n")

    print(f"V1b ledger params: sigma_x(3d) {p['sigma_x']:.4f}, rho {p['rho']:.3f}, "
          f"LINK daily sd {p['link_daily_sd']:.4f} ({p['bars']} Kraken bars)")
    for m in (1, 3, 10):
        row = {"mde_at": {d: mde(d, p["sigma_x"], p["rho"], m) for d in (20, 60, 180, 365)},
               "days_to_mde_1.83%": days_to(0.0183, p["sigma_x"], p["rho"], m),
               "days_to_mde_2.83%": days_to(0.0283, p["sigma_x"], p["rho"], m)}
        res["v1b"][f"m={m}"] = row
        print(f"  m={m:2d}: MDE " + ", ".join(f"{d}d {v:.1%}" for d, v in row["mde_at"].items())
              + f" | days to MDE<=1.83%: {row['days_to_mde_1.83%']:.0f}, <=2.83%: {row['days_to_mde_2.83%']:.0f}")
    # SUPPLEMENTARY, added after the first run and NOT pre-registered: the registered targets
    # (1.83%, 2.83%) test against zero GROSS edge. Acting needs the NET edge separated from
    # zero, i.e. MDE <= the net edge itself.
    res["v1b_supplementary_not_preregistered"] = {
        f"m={m}": {f"days_to_mde_{t:.1%}": days_to(t, p["sigma_x"], p["rho"], m) for t in (0.005, 0.01)}
        for m in (1, 3, 10)}
    print("  supplementary (not pre-registered), days until MDE <= net edge:")
    for k, row in res["v1b_supplementary_not_preregistered"].items():
        print(f"    {k}: " + ", ".join(f"{a[12:]} {b:.0f}d" for a, b in row.items()))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1)
    return res


if __name__ == "__main__":
    main()
