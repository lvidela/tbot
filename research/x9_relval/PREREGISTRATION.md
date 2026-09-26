# Pre-registration — X9: wide-divergence relative value vs LINK (live-agent proposal A3)

**Date:** 2026-09-26 · **Author:** Research Agent (cloud) · **Branch:** `research/x9-relval`
**Origin:** the live agent's proposal A3 (`research/findings/2026-09-26_broadened_alpha_program.md`):
"conditional on a divergence of ≥ Xσ, is convergence larger than 1.83% net?".
**Status:** committed before any divergence statistic is computed on real data.

## C1 prior-exposure disclosure
- **This panel:** X1's survivorship-free Binance daily panel. I have seen X1, X3, X4 and X6
  results on it, including that the EW alt basket was 0.16× in 2024–26 and that high-vol names do
  badly.
- **LINK hourly (X8):** no reversal after up-spikes.
- **Not seen:** I have not computed any X/LINK price-ratio statistic.
- **Knowledge cutoff:** 2026-06.
- **Evidential weight:** discovery-stage only at the program bar. The 2024-01 → 2026-06 window is
  a reused, pre-cutoff holdout and not independent confirmation (C2). Confirmation would need a
  FROZEN-2 forward entrant.

## C3 code hash
`evaluate.py` sha256 `2f16988a8e0370c41f52f9016080a45fe50b2677efd9086ec9e40817511bbcb5`.

## Hypothesis and mechanism
**H9:** when an asset's price relative to LINK falls unusually far below its recent norm, it
subsequently converges back. The convergence exceeds the 4-leg cost of rotating
LINK → X → LINK (1.83%).

**Mechanism:** a temporary, idiosyncratic dislocation (forced selling in X, or a LINK-specific
pump), followed by relative-price mean reversion.

**Spot-only form:** hold LINK; on a trigger, rotate into X; exit back to LINK on convergence or at
max hold.

## Definitions (no look-ahead)
- **Universe at day T:** X1's weekly top-50 as of the most recent Monday, excluding LINK.
- **z_T(X):** the z-score of log(close_X / close_LINK) at close(T), against the mean and sd of the
  **90 preceding** daily values. T itself is excluded.
- **Trigger:** z ≤ zthr **and** the live X4 volatility veto passes. The veto requires X's vol60
  percentile rank minus LINK's to be ≤ 15 points, among the universe plus LINK at T, as in
  `scripts/volfilter.py`.
- **Per-asset non-overlap:** no new trade in X while a trade in X is open.
- **Exit:** the first day d > T with z_d(X) ≥ 0, else T + maxhold. Prices at the exit use the last
  available close, so delisting is handled.
- **Net excess vs hold-LINK:** (X_exit/X_T)/(LINK_exit/LINK_T) − 1 − 1.83%.

## Tests
Family of 4: zthr ∈ {−2.5, −3.0} × maxhold ∈ {7, 28} days. **Primary:** zthr −3.0, maxhold 28.

- **Unit:** the mean net excess per *entry-week cluster* (all trades entered in the same Monday
  week are averaged). This handles simultaneous triggers from a common LINK move.
- **Inference:** a one-sided Newey–West t with lag = ceil(maxhold/7) weeks, for overlapping
  holdings.
- **Evidence standard:** a cell counts as a discovery pass only if **p < 0.05/(268 + 4) = 1.84e-4**
  (the program bar, C4) **and** the primary cell's matched random-asset control has p < 0.05.
  - **Matched control:** same entry dates and holding windows, with a random veto-passing
    universe member instead of the triggered asset, 300 draws.
  - The control separates "X is cheap vs LINK" from "rotating out of LINK at those dates".
- **Windows:**
  - discovery 2020-04-06 → 2023-12-31;
  - reused / pre-cutoff 2024-01-01 → 2026-06-30, run once after discovery is committed;
  - post-cutoff 2026-07-01 → 2026-08-27, descriptive only (limited by the panel's funding end).
- **Outcomes:**
  - a pass → freeze a FROZEN-2 forward entrant;
  - no pass → NEGATIVE if the primary mean is ≤ 0, else INCONCLUSIVE, with the MDE.

## Also reported
Trades per year, hit rate, median trade, and mean holding days.

## Known risks
- **The veto interacts with the trigger.** A sharp idiosyncratic drop raises X's vol60, so the
  veto may block many triggers (this was seen in unit tests). That is the live rule, so it is
  kept.
- **Binance universe vs Kraken's 37 pairs.** Delisted assets are marked at their last close.
- **Survivorship-free but broad:** distressed names that crashed vs LINK often do *not* converge.
  That is part of the question.
