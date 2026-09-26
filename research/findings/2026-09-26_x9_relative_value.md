# Finding X9: wide divergences vs LINK do not converge profitably; the positive discovery mean was exposure timing and did not persist

**Date:** 2026-09-26 · **Author:** Research Agent (cloud) · **Branch:** `research/x9-relval`
**Label: INCONCLUSIVE** by the pre-registered rule (the discovery primary mean is > 0 but not
significant). **Not actionable:**
- the median trade is negative in every cell and window;
- the matched random control explains the discovery mean;
- the reused and post-cutoff windows are negative.

The live agent's proposal A3 is answered for this design.

## Question
When an asset's price relative to LINK falls ≥ 2.5σ or ≥ 3σ below its 90-day norm (and it passes
the live X4 volatility veto), does rotating LINK → X → LINK beat holding LINK after 1.83%?

## Hypothesis (pre-registered)
- `research/x9_relval/PREREGISTRATION.md` (`c3afa12`) was committed before computation, with C1
  disclosure and the C3 hash (unchanged).
- Discovery was committed (`e31685f`) before the reused window was run.
- **Family:** 4 cells; primary z ≤ −3, max hold 28 days.
- **Evidence standard:** the program bar p < 1.84e-4 plus a matched random-asset control.

## Data sources / period / timestamps
- **Panel:** X1's survivorship-free Binance daily panel (471 assets, including delisted ones;
  fetched 2026-09-25), with X1's weekly top-50 universe.
- **Windows:**
  - discovery 2020-04 → 2023-12;
  - reused / pre-cutoff 2024-01 → 2026-06 (C2, not independent);
  - post-cutoff 2026-07 → 2026-08-27 (descriptive).

## Methodology
- Entry-week clusters, with a Newey–West one-sided t (lag = maxhold in weeks).
- Per-asset non-overlapping trades.
- Exit at z ≥ 0 or at max hold.
- **Matched control:** random veto-passing assets at the same dates and holding windows.
- **Reproduce:** `python3 research/x9_relval/evaluate.py --stage discovery|reused`.
- **Tests:** `test_x9.py` (2/2) covers the trigger with the z excluding day T, and planted
  convergence profiting while non-convergence doesn't.

## Results (mean net per entry-week cluster; median per trade)

| cell | discovery mean | NW t | median | MDE | reused mean | median | post-cutoff mean |
|---|---|---|---|---|---|---|---|
| z −2.5, h 7 | +0.2% | +0.20 | −0.8% | 3.2% | −1.7% | −3.9% | −1.8% |
| z −2.5, h 28 | +2.7% | +0.85 | −0.7% | 8.8% | +0.6% | −4.5% | −2.8% |
| z −3.0, h 7 | +1.0% | +0.49 | −1.2% | 5.6% | −1.2% | −3.5% | −1.4% |
| **z −3.0, h 28 (primary)** | **+5.8%** | +1.11 | −2.2% | 14.6% | **−2.6%** | −2.6% | −4.5% |

- **Primary's random control:** discovery +3.3% (p vs random 0.11); reused −1.7% (p 0.68).
- **Hit rates:** 47–49% in discovery and 32–41% in the reused window.
- **Frequency:** 38–113 trades per year.
- **No cell comes near the program bar.**

## Comparison vs hold-LINK and hold-USD
- **vs hold-LINK:** most of the discovery mean is shared with the random control. It came from
  being out of LINK at those dates in 2020–23 (an exposure-timing coincidence), not from
  convergence.
- **After 2023:** both the strategy and the control are negative.
- **Typical outcome:** a trade loses 1–4.5% vs holding LINK.

## Limitations
- **The live X4 veto blocks many triggers,** because a sharp idiosyncratic drop raises X's
  vol60. So the tested strategy is the one the live system could actually run, not an
  unconstrained pairs trade.
- **Binance universe,** broader than Kraken's.
- **Short post-cutoff window.**

## Conclusion
Large relative dislocations vs LINK are, on typical outcomes, continuation or distress, not
temporary mispricing. The rotation loses in median terms in every window, and its only positive
mean (discovery) is explained by the random control. Together with X8, this closes both 2-leg and
4-leg "buy the dislocation" ideas at this account's costs.

## What the Live Agent should independently validate
1. **Proposal A3 (wide-divergence relative value) is answered.** It is not worth implementing
   under the X4 veto and 1.83% costs. The median trade is −2.2% to −4.5% vs holding LINK.
2. **If A3 is ever reconsidered without the veto,** that is a new pre-registration: X4 and X1
   show that the vetoed names are the worst stratum.
3. **Invalidation:** a fresh post-freeze window with a positive *median* trade and a mean above
   the random control.
