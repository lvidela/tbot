# Pre-registration — X4b: replicate X4's low-vol effect on Kraken's own daily data

**Date:** 2026-09-25 · **Author:** Research Agent (cloud) · **Status:** committed before any
statistic on this dataset is computed.

## Why
X4 found IC(vol60, fwd 28d) < 0 on the Binance archive: −0.254 in the 2024–26 holdout. The live
agent trades on Kraken. This replicates X4 on Kraken's own prices and a Kraken-listed universe.
- **What it tests:** the venue and the universe.
- **What it does not test:** a new time period. The data window, 2024-10 → 2026-09, overlaps X4's
  holdout.

## Data
- **Source:** `research/tsmom/ohlc_long.json`, key `1440`. This is Kraken public daily OHLC for
  20 USD pairs, 720 bars, 2024-10-05 → 2026-09-24, with the partial last bar dropped.
- **Survivorship-biased:** the pairs are ones listed today. This is stated, not corrected.

## Test (single, pre-specified)
- **Decision times:** t on X4's 4-weekly Monday grid (phase 0, anchored 2020-01-06), with
  ≥ 60 prior bars and a 28-day forward window complete by 2026-09-24.
- **Universe:** all 20 assets. The quasi-peg rule (vol60 < 0.5%) is kept.
- **Primary:** the mean per-period Spearman IC(vol60, forward 28d log return).
- **Registered direction:** < 0.
- **Decision rule:**
  - **REPLICATED** if one-sided p < 0.05.
  - **NOT REPLICATED** if the point estimate is ≥ 0.
  - Otherwise INCONCLUSIVE.
  - MDE = 2.8 × SE, always reported.
- **Descriptive, not decisive:**
  - the other 3 phases;
  - the lowest-5-vol vs highest-5-vol equal-weight baskets at 0.46% maker per leg, vs hold-LINK
    and vs random-5 (500 draws);
  - LINK's volatility percentile.
