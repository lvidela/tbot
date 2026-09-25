# Pre-registration — V1: value-of-information screen of candidate research questions

**Date:** 2026-09-25 · **Author:** Research Agent (cloud session) · **Status:** committed before
any computation in `research/voi/`.

## Why this, and why no market test

- Every public data host is refused by this environment's network policy (proxy 403,
  2026-09-25 ~19:58Z: Kraken, Coinbase, Binance API, data.binance.vision, OKX, Bybit, Deribit).
  `research/data/raw/` is empty in this checkout, so T1 cannot be regenerated here, and no new
  two-exchange multi-year test is possible in this session.
- More importantly, the task is to pick the next question by expected information value for final
  net USD. F1–F3, R12 and R13 suggest few questions remain worth anything at a ~$59 account.
  This study asks that directly, before spending effort on any of them.

## Questions

**V1a.** For each candidate question C1–C9 below, what is the expected value of sample
information (EVSI) of the best study that is feasible now, in USD of final account value? What is
the expected value of perfect information (EVPI), which upper-bounds every possible study?

**V1b** (asked for by REGISTRY "Horizon amendment"). How does the minimum detectable effect of
the forward shadow/counterfactual ledgers shrink as independent decision times accumulate?
When can the ledgers first detect an effect equal to the tactical cost hurdle?

## Horizons (the two sources disagree, so both are reported)

- **H20:** 20 days to 2026-10-15. This is the end date in CLAUDE.md §1 and in the researcher's
  research-agent brief of 2026-09-25.
- **H365:** 365 days. `STATE.md` and REGISTRY's horizon amendment record an open-ended experiment.
  One year is used as a sensitivity bound, not as a claim about the end date.

## Fixed parameters (from repo records, not tuned)

| parameter | value | source |
|---|---|---|
| account A | $58.62 | STATE.md 2026-09-25 13:55Z |
| maker leg c₁ | 0.46% (0.40% fee + 5.4 bps adverse selection) | REGISTRY A1 |
| 4-leg tactical round trip | 1.83% | REGISTRY A1 |
| tactical notional | $13 | F1 / shadow ledger |
| LINK daily sd | 3.3% / 4.0% / 5.4% (low / central / high) | F3: last 90 d / 30 d / full |

Every other input is a stated scenario (low / central / high), fixed in `voi_screen.py` before it
is first run. Nothing is estimated from outcome data except the V1b nuisance parameters below.

## Method (V1a)

Each candidate is written as a binary decision: keep the status quo, or take action X. X has
unknown net benefit per dollar m ~ N(μ₀, s²) over the horizon, and X costs k legs.
- **EVPI** = A · E[max(m − k·c₁, 0)] − A · max(μ₀ − k·c₁, 0).
- **EVSI** uses the same closed form, but with the preposterior sd v = √(s² − s²_post) of the
  best feasible study, whose standard error is SE. This is the form `research/timing/evsi.py` uses.
- Where a candidate is not a single switch (tactical signals, tail monitoring), a stated
  expected-gain model is used instead, written out in the code docstring for that candidate.

Candidates:

| id | question | feasible study now |
|---|---|---|
| C1 | LINK vs USD: re-estimate the drift or re-run timing | only ~1 new day since T1; history is exhausted |
| C2 | hold a different asset (BTC/ETH) instead of LINK | no unused history (drift SE depends on span, not sampling frequency) |
| C3 | search for a new tactical signal | backtest at MDE 2.5–7.5% (R9/D5), prior from 13 rejections |
| C4 | maker fill and adverse selection in volatile regimes | live-only data; not feasible in cloud |
| C5 | execution timing (hour-of-day spread) of a one-off switch | public order-book sampling |
| C6 | LINK-specific non-price tail event (delisting, exploit) | monitoring, not statistics |
| C7 | partial exposure or diversification | none needed: see rule below |
| C8 | derivatives or hedging | not actionable under Hard Rule 2 |
| C9 | forward ledgers as tactical-edge evidence | accrues in the live system; V1b gives its timing |

**C7 rule:** under the stated objective (expected final USD), the payoff is linear in the weight.
So the optimum is a corner, and a partial position has zero EVPI beyond the C1/C2 corners.
This reopens only if the objective changes to median or utility, which is a researcher decision.

**Classification (per candidate, central scenario, horizon H20; H365 is reported beside it):**

- **NEGLIGIBLE:** EVSI < $0.05, i.e. "under a few cents". Do not research.
- **MARGINAL:** $0.05 ≤ EVSI < $0.25.
- **MEANINGFUL:** EVSI ≥ $0.25. This is a candidate for the next pre-registered study.

If no candidate is MEANINGFUL at H20, the finding says so plainly. It then names the best
candidate under H365, labelled conditional on the open-ended horizon.

## Method (V1b)

- Unit: one **decision time**, i.e. all ledger records opened within the same scan. The outcome
  is that cluster's mean 72h excess return vs LINK. Records at one time are one observation
  (F1, D7).
- Clusters count as independent only if they are ≥72h apart, so n(T) = T/3 after T days. This
  is conservative: overlapping clusters are not counted (D7).
- Var(cluster mean) = σ²_x · (ρ + (1 − ρ)/m), where m = picks per decision time
  (scenarios 1 / 3 / 10).
- MDE(T) = 2.80 · √Var / √n(T): two-sided α = 0.05 with 80% power, and a single test, so there
  is no correction. That flatters the ledgers.
- σ_x (sd of 3-day log return of an alt minus LINK) and ρ (average pairwise correlation of those
  excess returns across alts on the same day) are estimated from Kraken public daily OHLC
  (`research/tsmom/ohlc_long.json`, key `1440`, 2024-10-05 → 2026-09-25). This uses
  non-overlapping 3-day windows, the 19 non-LINK assets, and the median over the 3 phases.
- These are nuisance parameters, not a hypothesis test, so a single exchange is acceptable. The
  two-exchange rule applies to tests of effects. Cross-check: LINK's daily sd from this file is
  compared against F3's Coinbase figures (3.3–5.4%).
- **Reported:** days until MDE ≤ 1.83% (net-zero edge) and MDE ≤ 2.83% (+1% net). The answer is
  set against H20 and against H365.

## What would change the conclusion

- A MEANINGFUL candidate under H20 → it becomes the next pre-registered study.
- An EVPI under H20 below $0.05 for a candidate → no study of it can be worth running before
  2026-10-15, whatever its design.
