# Pre-registration — X1: cross-sectional funding crowding

**Date:** 2026-09-25 · **Author:** Research Agent (cloud) · **Branch:** `research/x1-funding-crowding`
**Status:** committed before any cross-sectional funding or return data is downloaded. The only
funding series seen before this is LINK's own (T1 signal S6).

## Hypothesis and mechanism
**H1:** among liquid crypto assets, those whose USDT-perpetual funding rate was high over the
trailing week have *lower* subsequent spot returns than those whose funding was low.

**Mechanism:**
- Positive funding is the price leveraged longs pay to hold exposure, so high funding marks
  crowded, leverage-financed demand.
- The prediction is that crowding inflates price temporarily and unwinds through deleveraging,
  liquidations or carry fatigue.
- **Registered direction:** rank IC < 0.

**Why it is new here:**
- R3/R9 (momentum/reversal) used past *returns*. Funding is a positioning measure, correlated
  with past returns but not identical to them. Test S-c isolates the difference.
- T1 S6 used LINK's own funding as a LINK-vs-USD timing signal, not cross-sectionally.

**Spot-only relevance:** a long-only rule (hold the least-crowded assets, or avoid LINK when it is
among the most crowded) is spot-actionable. A long-short version is not actionable under Hard
Rule 2 and is reported only as a measure of information.

## Data (fixed now)
- **Funding:** `data.binance.vision` archive, `futures/um/monthly/fundingRate/<SYM>/`, for every
  USDT-margined perp listed in the archive bucket. This **includes delisted symbols**, so the
  universe is survivorship-free with respect to Binance's listing history.
- **Returns:** Binance **spot** `<BASE>USDT` 1d klines from the same archive, also including
  delisted pairs. Symbol mapping:
  - a perp `1000X`/`1000000X` maps to spot `X`;
  - a perp with no spot USDT pair is excluded, and the exclusions are listed.
- **Enumeration:** the archive's public S3 listing (`s3-ap-northeast-1.amazonaws.com/data.binance.vision`).
  It is the same public bucket as `data.binance.vision`, not the geo-blocked API (A6).
- **Excluded:** stablecoins and fiat-pegged bases (USDC, FDUSD, TUSD, BUSD, DAI, USDP, EUR,
  PAXG and similar gold/fiat pegs).
- **Cross-check:** for bases in F5's 19-asset set, Binance spot returns are compared against
  Coinbase over the same weeks. The correlation of weekly returns must be ≥ 0.98, or the
  finding reports it as a data problem.
- **Provenance:** every file is stored with its URL and `fetched_at`.
- **Size:** the raw per-symbol data is kept outside git, and only derived panels are committed if
  they are ≤ 5 MB. `fetch.py` regenerates everything.

## Universe at each rebalance time t (no look-ahead)
- The perp has ≥ 1 funding print in (t−7d, t].
- The spot pair has ≥ 60 daily bars before t.
- Of those, take the **top 50** by median daily quote volume over the 30 bars before t.
- **Delisting:** if the spot pair stops trading before t+h, the forward return runs to its last
  available close. The asset is never dropped for delisting.

## Definitions
- **t:** Mondays 00:00 UTC. The bar that opened the day before closes at t.
- **Signal F(t):** the mean of funding prints with time in (t−7d, t].
- **Forward return:** spot log return over close(t) → close(t+h).

## Tests
Family of 5, Bonferroni α = 0.05/5 = 0.01, two-sided, in discovery:

| id | test | h |
|---|---|---|
| **P (primary)** | mean weekly Spearman IC(F, fwd return), non-overlapping Monday weeks | 7d |
| S-a | same, non-overlapping 4-week windows (every 4th Monday; the 4 phases are reported, phase 0 is primary) | 28d |
| S-b | signal = mean of the last 3 prints (24h) | 7d |
| S-c | partial IC: F and forward return each rank-residualised on trailing 7d return and 30d realised vol, per week | 7d |
| S-d | mean weekly return spread, lowest-F quintile minus highest-F quintile | 7d |

- **Sample split:** discovery covers t from 2020-01-06 to 2023-12-25. The holdout covers
  2024-01-01 to 2026-09-14. The holdout is evaluated once, after the discovery results are
  written to disk.
- **H1 is SUPPORTED only if all of the following hold:**
  - P is significant at the Bonferroni level in discovery, with IC < 0;
  - the holdout has the same sign with one-sided p < 0.05;
  - S-c has the same sign in both periods, so the effect is not just momentum or volatility.
- **Otherwise:** NEGATIVE if the discovery point estimate has the wrong sign or is below the MDE;
  INCONCLUSIVE if it has the right sign but is not significant. An MDE is always reported
  (2.8 × SE).
- **Other phase anchors** (Tuesday–Sunday) are reported as robustness, not as extra tests.

## Economic test (only interpreted if H1 is supported, but always reported)
**Strategy:** long-only, the **k** lowest-F assets (k = 1, 3, 5, 10), equal weight, rebalanced
each Monday.

**Costs:**
- 0.46% per leg on traded notional (A1 maker, including adverse selection). The first week is
  charged the full entry cost.
- Sensitivity at taker cost: 0.83% per leg.

**Benchmarks** (the weekly mean excess of each is reported, with a week-block bootstrap 90% CI):
1. hold-LINK;
2. hold-USD;
3. **the random-k control:** a k-asset equal-weight selection drawn uniformly from the same
   week's universe, with the same rebalance schedule and cost rule, averaged over 500 draws.
   This is the selection analogue of the static-exposure control: it has the same exposure and
   turnover type, and no information.
4. the equal-weight top-50 universe.

**Account feasibility:**
- At A = $58.62, flag any k where A/k is below the relevant Kraken minimum order.
- Secondary result, labelled survivorship-biased: restricted to bases that currently have a
  Kraken USD pair (Kraken public `AssetPairs`).

**Actionable only if all hold:**
- H1 is supported;
- in the **holdout**, top-k net of maker costs beats random-k *and* hold-LINK, with the 90% CI
  of excess-vs-random-k excluding 0;
- this holds for at least 2 of the 4 values of k.

A positive result would still go to the live agent as REQUIRES VALIDATION, not as an
instruction.

## Known risks, stated in advance
- **Data mining:** 5 tests and 4 values of k, with one family-wise correction on the tests. The
  values of k are economic sizing, not extra hypotheses.
- **Crowded funding coincides with rallies:** without S-c, H1 could be momentum or reversal
  relabelled.
- **The Binance universe is not Kraken's:** the live venue lists fewer assets.
- **Regime concentration:** the 2021 and 2022 cycles may carry the result. Per-year ICs will be
  reported.
