# Pre-registration — X3: rebound after market-wide capitulation days

**Date:** 2026-09-25 · **Author:** Research Agent (cloud) · **Branch:** `research/x3-capitulation`
**Status:** committed before any event is identified or any post-event return is computed.
The data is X1's survivorship-free Binance daily panel, which was already downloaded. No
event-conditional statistic has been computed on it.

## Hypothesis and mechanism
**H3:** after a market-wide capitulation day, crypto prices rebound over the following days. The
rebound is concentrated in the assets that fell most.

**Mechanism:**
- Capitulation days are dominated by forced selling: perp liquidation cascades and margin calls.
- Liquidity providers who absorb that selling demand a discount, which mean-reverts once the
  forced flow ends.
- **Why this is new here:**
  - R4 tested *unconditional* autocorrelation.
  - R9 tested unconditional cross-sectional reversal.
  - T1's S4 (LINK crash) was a LINK-only 20-day timing state.
  - None conditions on a **market-wide** forced-selling event at a 1–5 day horizon.
- **Why it could matter at this account size:** the moves are large (several %), so a plausible
  edge could clear 4 maker legs (1.84%).

## Data (fixed now)
- X1's panel: Binance archive spot 1d klines for 471 assets, including delisted ones.
- **Universe on day d:** X1's universe as of the most recent Monday ≤ d, i.e. the top 50 by
  30-day volume with a trailing funding print.
- Cross-checked for the 19 overlapping bases (weekly corr ≥ 0.989, X1).

## Definitions (no look-ahead)
- **Day T:** a UTC midnight. The day return r_T(a) = log close(T) − log close(T−1d), where close(T)
  is the close of the bar opened at T−1d.
- **Market index M_T:** the equal-weight mean of simple day returns over the universe.
- **Capitulation event at T,** when all hold:
  - M_T ≤ −2.5 × sd(M over the 60 days ending at T−1d);
  - BTC's day return < 0;
  - at least 5 days have passed since the previous event. Only the first event in a cluster
    counts, so events are non-overlapping.
- **Entry:** at close(T). Using daily data, this is the close at which the event becomes known.
  Realistic entry slippage is priced separately (see Economics).
- **Forward return:** log close(T+h) − log close(T), with h = 3 days primary and 1 and 5 days as
  robustness.

## Tests
Primary family: 3 tests at h = 3, Bonferroni α = 0.05/3 = 0.0167, two-sided.

| id | test | registered direction |
|---|---|---|
| **P1** | mean over events of [EW-universe forward return − the unconditional mean h-day EW return in the same period (all non-overlapping h-day windows)] | > 0 |
| **P2** | mean over events of Spearman IC(event-day return, forward return) across the universe | < 0 (the most crashed rebound most) |
| **P3** | mean over events of [LINK forward return − LINK's unconditional mean h-day return in the same period] | > 0 |

- **Robustness (reported, not in the family):**
  - h = 1 and h = 5;
  - an event threshold of 2.0σ and 3.0σ;
  - excluding 2020-03-12 → 2020-03-13, the COVID crash.
- **Sample split:** discovery covers events with T from 2020-03-15 (after 60 days of index
  history) to 2023-12-31. The holdout covers 2024-01-01 → 2026-09-19. The holdout runs once,
  after the discovery results are committed.
- **H3 is SUPPORTED** if P1 or P2 passes Bonferroni in discovery in the registered direction and
  the same test has one-sided p < 0.05 in the holdout.
- **Otherwise:** NEGATIVE if the sign is wrong, INCONCLUSIVE if not. An MDE is reported for every
  test.
- **Small-n warning, stated now:** expect roughly 15–40 events in total. MDEs will be several
  percent, so only large rebounds are detectable. Those are the only ones that could matter
  economically.

## Economics (always reported)
Three event strategies, each held h = 3 days, one position per event:
- **(E1) LINK holder, tactical:** sell LINK at close(T), buy the k = 3 / 5 most-crashed universe
  names equal weight, hold 3 days, and rotate back to LINK. That is 4 legs.
  - Excess vs hold-LINK over the same 3 days, per event.
- **(E2) USD holder:** buy LINK at close(T), sell at T+3d. That is 2 legs.
  - Return vs hold-USD, per event.
- **(E3) USD holder:** buy the EW universe at close(T) and hold 3 days. That is 2 legs.

**Costs and CIs:**
- Maker 0.46% per leg. A stress case of 0.92% per leg covers capitulation-day spreads and
  slippage.
- CIs are the percentile bootstrap over events, 90%.
- Reported per year of activity (events per year × mean excess per event), because an event rule
  only matters if events are frequent enough.

**Actionable only if all hold:**
- H3 is supported;
- E1's holdout mean excess vs hold-LINK is > 0 with a 90% CI excluding 0 at maker costs, and it
  stays > 0 at stress costs.

This would still go to the Live Agent as REQUIRES VALIDATION.

## Known risks
- **Few events:** high variance.
- **Close-to-close entry is optimistic** on a capitulation day, which is why the stress cost
  exists.
- **Delisted assets:** included, marked at their last trade.
- **Overlap with X1/X4 data use:** this is a different conditioning event, but the same panel.
