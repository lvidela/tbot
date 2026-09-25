# Pre-registration — X6: listing age and post-listing drift

**Date:** 2026-09-25 · **Author:** Research Agent (cloud) · **Branch:** `research/x6-listing-age`
**Status:** committed before any age–return statistic is computed.
- The data is X1's survivorship-free Binance panel, already downloaded.
- X4 established that high trailing volatility predicts low relative returns. Young listings are
  high-vol, so any age effect must be shown *beyond* volatility.

## Hypothesis and mechanism
**H6:** among liquid assets, recently listed ones underperform older ones over the next 28 days,
**after controlling for volatility**.
- **Registered direction:** partial IC(log age, fwd 28d) > 0.

**Mechanism:**
- Launch hype decays after listing.
- Low initial float is followed by scheduled token unlocks, which dilute holders.
- Market makers' and early investors' inventory distribution adds selling pressure.
- None of this is a volatility property per se, which is why the partial IC controls for
  volatility.

## Data and universe
- **Data:** X1's panel and X4's universe (top 50 by 30-day volume, funding print, ≥ 60 bars,
  vol60 ≥ 0.5%).
- **Age at t:** days between the asset's first Binance spot daily bar and t, from X1's
  survivorship-free archive.
  - **Limitation:** this is the Binance listing date, which can be later than the token's first
    trade elsewhere. It measures the age of the asset's liquid life on a major venue.
  - Assets whose Binance history begins at the archive's start (2017-08 / 2017-11) are older
    than measured. The rank transforms make that harmless for the oldest names.

## Tests
Family of 3, Bonferroni α = 0.0167, two-sided, in discovery. The periods are X4's 4-weekly grid,
phase 0.

| id | test | registered direction |
|---|---|---|
| **P** | partial Spearman IC(log age, fwd 28d), both sides rank-residualised on vol60, mom28 and log 30-day volume | > 0 |
| S1 | raw Spearman IC(log age, fwd 28d) | > 0 |
| S2 | per-period mean forward simple return of "young" assets (age < 180 days) minus the rest; only periods with ≥ 3 young assets | < 0 |

- **Sample split:** discovery covers t from 2020-01-06 to 2023-12-04, and the holdout covers
  2024-01-01 → 2026-08-10, the same grid as X4. The holdout runs once, after discovery is
  committed.
- **H6 is SUPPORTED** if P passes Bonferroni in discovery in the registered direction and the
  holdout P has one-sided p < 0.05.
- **Otherwise:** NEGATIVE if P has the wrong sign in discovery, INCONCLUSIVE if not. MDEs are
  always reported.

## Economics (always reported)
**Filter test:**
- **EW(age ≥ 180d):** the equal-weight universe excluding young assets.
- **EW(all):** the full equal-weight universe.
- Both rebalanced 4-weekly at 0.46% per leg. Report the per-period difference with a 3-period
  block-bootstrap 90% CI.

**Also:**
- the young basket vs random-k with the same k (the young count per period is capped at 5);
- hold-LINK and hold-USD.

**Actionable (as a universe filter for the live agent) only if all hold:**
- H6 is supported;
- EW(old) − EW(all) > 0 in the holdout with a 90% CI excluding 0.

## Known risks
- **Age correlates with volatility and size.** The partial IC addresses this, but imperfectly.
- **Young assets per period may be few,** especially in 2020, so S2 may have low n.
- **2024–26 had many new listings** (a memecoin/AI wave). That could make the holdout a special
  regime.
