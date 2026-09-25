"""Stakes / value-of-information analysis for the remaining experiment horizon.

Question: over the remaining horizon, how many USD can each decision lever move, relative to the
hold-LINK benchmark? This bounds how much any research result can be worth before running it.

Pure arithmetic on stated parameters (no market data needed). Inputs are from STATE.md /
REGISTRY.md as of 2026-09-25; LINK daily sigma is swept because it was not measurable in this
cloud session (exchange APIs blocked by network policy).

Run: python3 research/stakes/stakes.py
"""
import math

ACCOUNT_USD = 58.94          # STATE.md, 2026-09-25 13:05Z
DAYS_LEFT = 20               # to 2026-10-15
TACTICAL_NOTIONAL = 13.0     # typical shadow/counterfactual hypothetical_notional
ROUND_TRIP_MAKER = 1.83      # % REGISTRY A1 (4 legs incl. adverse selection)
HOLD_VS_CASH_CI = (-3.77, 2.23, 8.48)   # % LINK 21d fwd mean CI, DEEP_REVIEW Q5
MDE_RANGE = (2.5, 7.5)       # % minimum detectable effect of existing studies (R9, D5)


def exposure_lever(sigma_daily_pct):
    """1-sigma USD swing of the LINK-vs-USD exposure decision over the horizon."""
    return ACCOUNT_USD * sigma_daily_pct / 100 * math.sqrt(DAYS_LEFT)


def tactical_lever(net_edge_pct, trades):
    """Expected USD from `trades` independent tactical trades with a true net edge."""
    return TACTICAL_NOTIONAL * net_edge_pct / 100 * trades


def main():
    print(f"Account ${ACCOUNT_USD}, {DAYS_LEFT} days left\n")
    print("1. Exposure lever (LINK vs USD), 1-sigma tracking swing vs benchmark:")
    for s in (3.5, 4.5, 6.0):
        print(f"   LINK daily sigma {s:.1f}% -> +/- ${exposure_lever(s):.2f}")
    lo, mid, hi = HOLD_VS_CASH_CI
    print(f"   Expected-value difference of exiting to USD (from 21d CI):"
          f" ${-ACCOUNT_USD*hi/100:.2f} .. ${-ACCOUNT_USD*lo/100:.2f} (point ${-ACCOUNT_USD*mid/100:.2f})")

    print("\n2. Tactical lever: expected USD from a TRUE net edge (already after costs):")
    for e in (0.25, 0.5, 1.0, 2.0):
        row = "  ".join(f"{n:>2} trades ${tactical_lever(e, n):5.2f}" for n in (5, 10, 20))
        print(f"   edge {e:4.2f}%/trade: {row}")
    print(f"   Existing studies cannot detect edges below {MDE_RANGE[0]}-{MDE_RANGE[1]}% (R9/D5);")
    print(f"   a 1% net edge would require a ~{1+ROUND_TRIP_MAKER:.2f}% gross edge per round trip.")

    # How many independent observations would validate a 1% net edge at t=2 before the end?
    # Tactical per-trade sd is roughly the asset's daily sigma * sqrt(3d horizon) ~ 8-10%.
    sd_trade = 9.0
    n_needed = (2 * sd_trade / 1.0) ** 2
    print(f"\n3. Validation cost: detecting a 1% net edge at t=2 needs ~{n_needed:.0f} independent"
          f" trades (per-trade sd ~{sd_trade}%); {DAYS_LEFT} days of 72h trades gives ~{DAYS_LEFT//3}"
          " per concurrent slot.")

    ratio = exposure_lever(4.5) / tactical_lever(1.0, 10)
    print(f"\nExposure lever / tactical lever (sigma 4.5%, 1% edge x 10 trades): {ratio:.0f}x")


if __name__ == "__main__":
    main()
