# Finding X1: cross-sectional perp funding does not predict spot returns stably, and buying the least-crowded coins is ruinous

**Date:** 2026-09-25 · **Author:** Research Agent (cloud) · **Branch:** `research/x1-funding-crowding`
**Label: NEGATIVE.**
- H1 (high trailing funding → lower forward returns) was not supported in discovery.
- It was contradicted in the holdout: the sign flipped.
- The spot-actionable form (hold the lowest-funding coins) lost 97–99.97% in the holdout and was
  significantly worse than random selection.

## Question
Across liquid crypto assets, does the trailing USDT-perp funding rate, a measure of leveraged
long crowding, predict next-week relative spot returns? Is the long-only rule "hold the least
crowded" worth more than hold-LINK, hold-USD, or random selection?

## Hypothesis (pre-registered)
`research/x1_funding/PREREGISTRATION.md` was committed and pushed (`338de53`) before any
cross-sectional data was downloaded.
- **Registered direction:** rank IC < 0.
- **Family and threshold:** 5 tests, Bonferroni α = 0.01.
- **Split:** discovery 2020-01-06 → 2023-12-25 and holdout 2024-01-01 → 2026-09-14. The holdout
  was run once, after the discovery results were committed (`87df027`).
- **Economic test:** top-k lowest-funding coins, long-only, with k = 1, 3, 5, 10. The comparisons
  are hold-LINK, hold-USD, a random-k control (500 draws), and the equal-weight universe.

## Data sources / period / timestamps
- **Funding:** the Binance public archive (`data.binance.vision`, enumerated via its public S3
  listing), covering **all 865 USDT-margined perps ever listed, including delisted ones**.
- **Returns:** Binance spot `<BASE>USDT` daily klines from the same archive.
  - 471 perps have a spot pair. 391 have none and are excluded; they are listed in
    `raw/_universe_plan.json`. 3 stablecoins are excluded.
  - Fetched 2026-09-25 22:40–23:05Z with 0 failures (`raw/_fetch_log.jsonl`). The raw data is kept
    outside git; `python3 research/x1_funding/fetch.py` regenerates it.
- **Funding ends 2026-08-31** because the archive's September file is not published yet. Holdout
  weeks after that have partial signals. Rerunning the holdout to the end of funding gives the
  same results (`tests_to_funding_end` in `holdout.json`).
- **Cross-check (pre-registered):** Binance vs Coinbase weekly log-return correlation is
  **≥ 0.989 on all 19 overlapping bases** (`results/crosscheck.json`).
- **Universe per week:** the top 50 by 30-day median quote volume among assets with a funding
  print in the trailing week and ≥ 60 daily bars. The median universe is ~50 names. Delisted
  coins stay in until their last trade.

## Methodology
- **Decision times:** Mondays 00:00 UTC. The signal uses only funding prints and daily bars
  closed by t, and a test proves that.
- **Tests:**
  - weekly Spearman IC on non-overlapping weeks;
  - 28-day IC (phase 0 primary, 4 phases reported);
  - a partial IC that residualises both sides on 7-day momentum and 30-day volatility ranks;
  - the quintile spread.
- **Costs:** 0.46% per maker leg on traded notional (A1), with 0.83% taker as a sensitivity. The
  first week pays full entry.
- **CIs:** 4-week block bootstrap, 90%.
- **Reproduce:** `evaluate.py --stage crosscheck|discovery|holdout`. Tests: `test_x1.py` (5/5):
  no look-ahead, delisting handling, entry cost, planted-effect recovery with a null that
  doesn't fire, and the universe ranking.

## Results

### Information tests
- **Discovery:** 206 weeks, ~50 names per week.
- **Holdout:** 141 weeks. p_neg is the one-sided p for the registered direction.

| test | discovery mean | t | p (two-sided) | MDE | holdout mean | t | p_neg |
|---|---|---|---|---|---|---|---|
| **P** IC 7d | **−0.026** | −1.94 | 0.053 (fails α = 0.01) | 0.037 | **+0.034** | +2.24 | 0.99 |
| S-a IC 28d | −0.001 | −0.03 | 0.98 | 0.088 | +0.098 | +2.84 | 0.996 |
| S-b IC 7d (last-24h funding) | **−0.046** | **−3.46** | **0.0006 (passes)** | 0.037 | +0.021 | +1.37 | 0.91 |
| S-c partial IC (momentum/vol-controlled) | −0.019 | −1.44 | 0.15 | 0.037 | +0.005 | +0.31 | 0.62 |
| S-d quintile spread, low − high F, per week | +0.49% | +1.03 | 0.31 | 1.33% | −0.75% | −1.38 | — |

- **Per-year IC:** 2020 −0.037, 2021 −0.057, 2022 +0.012, 2023 −0.022, 2024 +0.008, 2025 +0.050,
  2026 +0.048.
- **Weekday anchors:** in discovery all six alternative anchors are negative (−0.008 to −0.028).
  In the holdout all six are positive (+0.023 to +0.038).
- **Reading:**
  - The relation reverses between regimes.
  - S-b's discovery pass does not replicate.
  - The holdout's positive IC vanishes once momentum and volatility are controlled (S-c +0.005),
    so it is momentum or volatility, not funding information.

### Economics
Wealth multiples; weekly maker costs.

| | discovery 2020–23 | holdout 2024–26 |
|---|---|---|
| hold-LINK | **8.32** | **0.84** |
| hold-USD | 1.00 | 1.00 |
| equal-weight top-50 universe | 3.25 | **0.16** |
| top-1 lowest funding (random-1 median) | 0.006 (0.148) | **0.0003** (0.023) |
| top-3 | 0.43 (0.30) | 0.002 (0.042) |
| top-5 | 0.68 (0.46) | 0.006 (0.048) |
| top-10 | 0.65 (0.62) | 0.033 (0.058) |

- **Holdout excess vs random-k, per week, 90% CI:**
  - top-1 [−4.4%, −0.7%]
  - top-3 [−3.0%, −0.3%]
  - top-5 [−2.2%, −0.3%]
  - top-10 [−1.0%, +0.3%]
- The first three CIs exclude 0 **on the wrong side**.
- Vs hold-LINK, every k's CI is below 0.
- At taker costs, every result is worse.
- **Kraken-listed subset (286 bases, survivorship-biased, secondary):** top-k is no better than
  random. The top-10 excess CI is [−0.6%, +0.5%].
- **Why the long-only rule is ruinous:** the most negative funding marks coins that shorts are
  crowding into, which are often distressed or collapsing (BIO, DEXE, TRB, DASH, LUNC, AIXBT
  appear among the worst weeks). The median holdout week for the top-1 pick is −4.2%, and 62% of
  weeks are negative. Spot-only traders cannot harvest the "crowded short" side, which is also
  unstable.
- **Minimum orders:** feasible for every k at $58.62, but irrelevant given the result.

## Comparison vs hold-LINK and hold-USD
- Every funding rule loses to both benchmarks in the holdout.
- **Descriptive, not a forecast:** the survivorship-free top-50 Binance alt basket fell to
  **0.16×** in 2024–26 while LINK held 0.84×. Random weekly picks from that universe had a median
  of 0.02–0.06×.
- Over this period, rotating out of LINK into the broad liquid alt universe would have been
  strongly value-destroying before any signal was applied. This is survivorship-free evidence
  consistent with R3/R13's caution about rotation.

## Robustness
- The sign reversal holds across all weekday anchors, in both periods, and when the holdout is
  truncated at the end of funding.
- Discovery's negative IC is carried by 2020–21 (per year: −0.037, −0.057). 2022 is positive.

## Limitations
- The universe is Binance's, which is broader and more speculative than Kraken's 37 eligible
  pairs. The Kraken subset is survivorship-biased because it is today's listings.
- Delisted coins are marked at their last trade, which assumes an exit was possible.
- Two regimes are ~2 effective observations of the sign of the relation. "It flips with regime"
  is a description, not an established regime rule.
- Signals start from weekly averages. Hourly-resolution signals and funding *changes* were not
  tested.

## Conclusion
- **The pre-registered hypothesis fails.** Funding crowding is not a stable cross-sectional
  predictor of spot returns in this universe: negative in 2020–23, positive in 2024–26.
- The only discovery pass (24h funding) did not replicate.
- The long-only implementation is strongly harmful.
- **What's worth keeping:** in a spot-only account, extreme negative funding is a warning flag for
  distressed coins, not a buy signal.

## What the Live Agent should independently validate
1. **No action is recommended.** If anything in the live universe or tactical mode favours coins
   with *negative* perp funding as "uncrowded", this evidence argues against it.
2. **The survivorship-free alt-basket result (0.16× vs LINK's 0.84× in 2024–26) informs any
   rotation prior.** It can be reproduced with `evaluate.py --stage holdout`, key
   `economics.ew_universe_maker`. It is descriptive, not predictive.
3. **Invalidation:** a new regime in which the IC is negative again. The archive is monthly, so
   the relation could be re-checked quarterly. Re-trade only on a fresh pre-registered holdout.
