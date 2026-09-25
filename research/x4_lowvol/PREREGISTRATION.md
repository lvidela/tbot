# Pre-registration — X4: low-volatility / low-beta cross-section (monthly)

**Date:** 2026-09-25 · **Author:** Research Agent (cloud) · **Branch:** `research/x4-lowvol`
**Status:** committed before any volatility–return statistic is computed.
- The data is X1's survivorship-free Binance panel, already downloaded.
- What X1 exposed about it: the equal-weight universe and the lowest-*funding* picks performed
  badly in 2024–26. Nothing was computed conditional on volatility or beta.

## Hypothesis and mechanism
**H4:** within the liquid crypto universe, assets with low trailing realised volatility earn
higher subsequent 28-day spot returns than high-volatility assets.
- **Registered direction:** rank IC(vol, forward return) < 0.

**Mechanism (the low-vol / betting-against-beta anomaly):**
- Leverage-constrained and lottery-seeking buyers overpay for high-volatility, high-beta tokens.
- Crypto-specific additions: high-vol tokens are disproportionately recent listings with ongoing
  supply unlocks and dilution, plus distressed names.
- This predicts that high-vol names bleed over time.

**Relation to prior work:**
- R3/R9 sorted on past *returns*, and X1 on funding.
- R13 compared LINK with BTC/ETH as single pairs, with no power.
- H4 uses a different characteristic across ~50 assets per date. That is more power on the
  "what to hold" question than R13 had.

## Data and universe (identical to X1's, reused)
- **Data:** Binance archive perps and spot, including delisted ones, as fetched by
  `research/x1_funding/fetch.py`.
- **Universe at t:** the top 50 by 30-day median quote volume among assets with a funding print in
  (t−7d, t] and ≥ 60 daily bars.
- **Added exclusion (fixed now):** assets with 60-day daily-return sd < 0.5%. These are
  quasi-pegs or wrapped assets.

## Definitions
- **t:** every 4th Monday, anchored on 2020-01-06 (phase 0, primary). Phases 1–3 are shifted by
  1–3 weeks and reported as robustness.
- **Forward return:** spot log return close(t) → close(t+28d). Delisted assets run to their last
  close.
- **vol60:** the sd of the last 60 daily log returns ending at close(t).
- **beta60:** the OLS beta of the asset's daily log returns on BTCUSDT's, over the same 60 days.

## Tests
Family of 4, Bonferroni α = 0.0125, two-sided, in discovery:

| id | test |
|---|---|
| **P** | mean Spearman IC(vol60, fwd 28d) over non-overlapping 4-week periods |
| S1 | mean Spearman IC(beta60, fwd 28d) |
| S2 | partial IC of vol60, with both sides rank-residualised on 28-day momentum and log volume rank |
| S3 | mean per-period raw return spread: lowest-vol quintile minus highest-vol quintile |

- **Sample split:** discovery covers t in 2020-01-06 → 2023-12-25, and the holdout t from
  2024-01-01 (a phase-0 date) through the last t whose 28-day forward window completes by
  2026-09-24. The holdout runs
  once, after the discovery results are committed.
- **H4 is SUPPORTED only if all hold:**
  - P passes Bonferroni in discovery with IC < 0;
  - the holdout P has one-sided p < 0.05 in the same direction;
  - S2 has the same sign in both periods.
- **Otherwise:** NEGATIVE if the discovery point estimate has the wrong sign, INCONCLUSIVE if the
  sign is right but the test fails. The MDE (2.8 × SE) is always reported.

## Economic test (always reported; interpreted only if H4 is supported)
**Strategy:** long-only, the k lowest-vol60 assets (k = 1, 3, 5, 10), equal weight, rebalanced
every 4 weeks.

**Costs:** 0.46% per leg on traded notional, with the first period paying full entry. Taker
0.83% is a sensitivity.

**Benchmarks:**
- hold-LINK;
- hold-USD;
- **hold-BTC**, because a low-vol basket may simply be "mostly BTC" and R13 already covers BTC;
- random-k (500 draws, the same schedule and costs);
- the equal-weight universe.

**Actionable only if all hold:**
- H4 is supported;
- in the holdout, top-k net beats random-k with a 90% block-bootstrap CI excluding 0, for at
  least 2 values of k;
- top-k beats hold-LINK in point estimate.

**Secondary, labelled survivorship-biased:** the Kraken-listed subset. A positive result still
goes to the Live Agent as REQUIRES VALIDATION.

## Known risks, stated in advance
- **Small n:** ~50 discovery periods and ~33 holdout periods. The MDE on IC will be ~0.08–0.10.
  A null will likely be INCONCLUSIVE rather than NEGATIVE.
- **A low-vol basket ≈ BTC/ETH/BNB:** the result may reduce to R13. The hold-BTC benchmark and
  S2 exist to show this.
- **Regime dependence** is the lesson of X1. Per-year ICs will be reported.
