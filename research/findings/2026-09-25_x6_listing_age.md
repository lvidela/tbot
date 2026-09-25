# Finding X6: younger listings rank lower beyond volatility, but the effect is in ranks and medians, not mean returns; not actionable as a filter

**Date:** 2026-09-25 · **Author:** Research Agent (cloud) · **Branch:** `research/x6-listing-age`
**Label: POSITIVE for information.** H6 is supported: the partial IC is significant in discovery
and the holdout. **NEGATIVE as a universe filter:** excluding young assets did not raise the
equal-weight portfolio's return (pre-registered actionability test failed).

## Question
Do recently listed assets underperform older ones over 28 days, beyond what their higher
volatility (X4) already explains? Would excluding assets younger than 180 days from a universe
improve returns?

## Hypothesis (pre-registered)
`research/x6_listing_age/PREREGISTRATION.md` (`c44cfbc`) was committed before computation.
Discovery was committed (`2df2c75`) before the holdout was run.
- **Primary:** partial IC(log age, fwd 28d) > 0, controlling for vol60, mom28 and log volume.
- **Family:** 3 tests, Bonferroni α = 0.0167.

## Data sources / period / timestamps
- **Data:** X1's survivorship-free Binance panel, with X4's universe and grid.
- **Age:** days since the first Binance spot bar.
- **Periods:** discovery 2020-01 → 2023-12 (51 periods); holdout 2024-01 → 2026-08 (35 periods).
- On average there are 4–5 "young" (< 180 days) assets per period.
- The age–vol rank correlation is −0.50 in discovery and −0.59 in the holdout.

## Methodology
- Non-overlapping 28-day windows, with rank residualisation for the partial IC.
- **Economics:**
  - EW(age ≥ 180d) vs EW(all), 4-weekly at 0.46% per leg;
  - young basket (≤ 5 names) vs a random basket of the same size;
  - 3-period block-bootstrap 90% CIs.
- **Reproduce:** `python3 research/x6_listing_age/evaluate.py --stage discovery|holdout`.
- **Tests:** `test_x6.py` (2/2) covers age from the first bar and planted-effect recovery with a
  quiet null. The null has equal volatility across assets, so a detected effect cannot be
  volatility.

## Results

| test | discovery | t | p (two-sided) | holdout | t | one-sided p |
|---|---|---|---|---|---|---|
| **P** partial IC(age \| vol, mom, size) | **+0.074** | +2.68 | 0.0099 ✔ | **+0.112** | +3.45 | 0.0008 ✔ |
| S1 raw IC(age) | +0.143 | +4.61 | < 0.0001 ✔ | +0.260 | +6.68 | < 0.0001 |
| S2 young − rest, mean per 28d | −0.1% | −0.02 | 0.98 | −0.1% | −0.02 | 0.49 |

- **MDEs:** P 0.077 / 0.091; S2 12.7% / 16.5%.
- **Phases 1–3:** +0.057 to +0.066 in discovery and +0.106 to +0.134 in the holdout.
- **Per year:** 2020 +0.01, 2021 +0.06, 2022 +0.08, 2023 +0.13, 2024 +0.13, 2025 +0.17,
  2026 −0.02.

**Economics (wealth multiples):**

| | discovery | holdout |
|---|---|---|
| EW(age ≥ 180d) | 3.32 | 0.27 |
| EW(all) | 3.60 | 0.26 |
| **old − all, per 28d** (90% CI) | −0.4% [−1.5, +0.4] | +0.1% [−0.9, +0.9] |
| young basket | 0.38 | 0.27 |
| young − random, gross per 28d (90% CI) | −0.2% [−5.8, +6.2] | +2.5% [−5.8, +13.4] |
| hold-LINK | 8.32 | 0.89 |

**Reading:**
- Younger assets land in the lower half of the cross-section of returns more often, beyond
  volatility, and that holds in both periods.
- Their *mean* return is the same as the rest's. A few young names have large right-tail winners
  that offset the typical loss.
- For an expected-USD objective, excluding them buys nothing, so the actionability test fails.

## Comparison vs hold-LINK and hold-USD
- The filter does not change the universe's poor absolute performance: 0.27× in the holdout vs
  hold-LINK's 0.89× and hold-USD's 1.00×.
- Nothing here bears on leaving LINK.

## Limitations
- The Binance listing date is not the token launch date.
- There are few young assets per period, so S2's MDE is large (13–17% per 28 days).
- Delisted names are marked at their last trade.
- 2026 is partial, and its partial IC is ≈ 0.

## Conclusion
- **Listing age carries rank information beyond volatility:** a second robust cross-sectional
  characteristic after X4.
- As with X4, the effect sits in the typical (median or rank) outcome. The arithmetic mean
  difference is not detectable, because young coins have lottery-like right tails.
- **Recurring pattern:** X4 discovery and X6 both show strong rank ICs with ≈ 0 mean spreads.
  - A filter based on either improves median outcomes, not reliably expected USD.
  - Which objective applies (expected vs median) is a researcher decision. F4 already flagged
    it as a trigger for re-screening.

## What the Live Agent should independently validate
1. **No filter recommended for an expected-USD objective.** If the researchers regard median
   outcomes or drawdown as relevant, an age ≥ 180d plus low-vol filter on tactical entries is
   supported by two independent rank effects (X4, X6).
2. **Check the live universe's composition:** how many of the 37 eligible pairs are younger than
   180 days on Kraken, and whether tactical or shadow entries concentrate in them.
3. **Invalidation:** the partial IC ≤ 0 over a fresh 12-period window.
