# Finding X4: low volatility strongly predicts higher cross-sectional *rank* returns out of sample. It beats random alt selection, not hold-LINK or hold-BTC

**Date:** 2026-09-25 ~23:20Z. The filename's 2026-09-26 is an error; it was kept because the
guard treats findings as append-only and blocks renames. · **Author:** Research Agent (cloud) · **Branch:** `research/x4-lowvol`
**Label: REQUIRES VALIDATION.**
- The information result is POSITIVE: the pre-registered H4 is supported in both discovery and
  a chronological holdout.
- The economic content relative to the live holding is weak: there is no significant
  improvement over hold-LINK or hold-BTC.
- What it supports is a **filter** (avoid high-volatility names), not a switch.

## Question
Among liquid crypto assets, do low-volatility assets earn higher subsequent 28-day spot returns
than high-volatility ones (a crypto analogue of the low-vol / betting-against-beta anomaly)?
Is a long-only low-vol basket worth more than hold-LINK, hold-BTC, hold-USD or random selection
after costs?

## Hypothesis (pre-registered)
`research/x4_lowvol/PREREGISTRATION.md` (`4754441`) was committed and pushed before any
volatility–return statistic was computed. Discovery results were committed (`1d1fad3`) before the holdout was
run.
- **Direction:** IC(vol60, fwd 28d) < 0.
- **Family:** 4 tests, Bonferroni α = 0.0125.
- **Support rule:** discovery pass, plus holdout one-sided p < 0.05, plus the controlled partial
  IC having the same sign in both periods.
- **Actionability rule:** H4 supported; top-k beats random-k with a 90% CI excluding 0 for ≥ 2
  values of k; and top-k beats hold-LINK in point estimate.

## Data sources / period / timestamps
X1's survivorship-free panel, unchanged:
- Binance archive USDT-perp funding (used only for universe membership) and spot 1d klines.
- 471 assets, including delisted ones. Fetched 2026-09-25 22:40–23:05Z.
- Coinbase cross-check correlation ≥ 0.989.

Setup:
- **Universe:** the weekly top 50 by 30-day volume, excluding quasi-pegs (vol60 < 0.5%).
- **Decision times:** every 4th Monday.
  - Discovery: 2020-01-06 → 2023-12-04, 51–52 periods.
  - Holdout: 2024-01-01 → 2026-08-10, 35 periods.
- Phases 1–3, shifted by 1–3 weeks, are reported as robustness.

## Methodology
- **vol60:** the sd of 60 daily log returns ending at close(t).
- **beta60:** the beta on BTC over the same days.
- **Tests:** Spearman IC; a partial IC residualised on 28-day momentum and log volume ranks; and
  the quintile raw-return spread.
- **Non-overlapping 28-day windows.** Each period is one observation, with all assets clustered
  within it.
- **Costs:** 0.46% maker per leg on turnover, with 0.83% taker as a sensitivity.
- **CIs:** 3-period block bootstrap, 90%. Random-k uses 500 draws.
- **Reproduce:** `python3 research/x4_lowvol/evaluate.py --stage discovery|holdout`.
- **Tests:** `test_x4.py` (4/4) covers no look-ahead, peg exclusion, and planted-effect recovery
  with a quiet null.

## Results

### Information (phase 0 primary)

| test | discovery | t | p (two-sided) | holdout | t | one-sided p |
|---|---|---|---|---|---|---|
| **P** IC(vol60) | **−0.157** | **−4.28** | 0.0001 ✔ | **−0.254** | **−6.87** | < 0.0001 ✔ |
| S1 IC(beta60) | −0.081 | −2.27 | 0.027 ✘ | −0.077 | −1.38 | 0.089 |
| S2 partial IC(vol60) | −0.151 | −4.59 | < 0.0001 ✔ | −0.245 | −6.73 | < 0.0001 ✔ |
| S3 quintile spread, low − high vol, raw mean per 28d | −1.2% | −0.30 | 0.76 | **+6.5%** | +2.08 | — |

- **MDE on IC:** ~0.10 in both periods.
- **Phases:** the IC is −0.157 to −0.167 across all four phases in discovery and −0.221 to −0.254
  in the holdout.
- **Per year:** 2020 −0.17, 2021 −0.06, 2022 −0.27, 2023 −0.13, 2024 −0.17, 2025 −0.36,
  2026 −0.24. **Negative in every year.** This contrasts with X1's sign flip.
- **H4 is supported.**
- Volatility, not BTC-beta, carries the signal.
- **Momentum and size do not explain it:** the partial IC ≈ the raw IC.

**Rank vs mean, and why it matters for expected USD:**
- **Discovery:** the quintile *mean* spread was ≈ 0. High-vol names had lottery-like right tails,
  and in 2020–21 their arithmetic mean was as high as the low-vol names'.
- **Holdout:** the mean spread was clearly positive, +6.5% per 28 days.
- **Supplementary (not pre-registered, `supplementary_highvol.py`):** the 5 or 10 highest-vol
  names, held long-only:

  | | discovery | holdout |
  |---|---|---|
  | wealth | 0.32× (k = 5), 1.67× (k = 10) | **0.07×** (both k) |
  | mean per 28d | +5.3% / +7.3% | −3.3% / −4.7% |
  | median per 28d | −3.2% / +0.5% | −10.8% / −10.6% |

  - Excess vs random-k has CIs spanning 0 in both periods.
  - Taken together: high-vol names reliably have poor *median* and compounded outcomes. Their
    arithmetic mean was not reliably worse in 2020–21.

### Economics (long-only lowest-vol k, maker costs)

**Wealth multiples:**

| | discovery 2020–23 | holdout 2024–26 | full period |
|---|---|---|---|
| hold-LINK | 8.32 | 0.89 | 7.37 |
| hold-BTC | 5.75 | 1.90 | 10.92 |
| hold-USD | 1.00 | 1.00 | 1.00 |
| equal-weight universe | 3.60 | 0.26 | 0.95 |
| low-vol top-1 (random-1 median) | 9.89 (0.62) | 2.63 (0.08) | 26.2 (0.04) |
| top-3 | 10.53 (1.03) | 2.06 (0.14) | 21.8 (0.18) |
| top-5 | 7.31 (1.44) | 1.24 (0.17) | 9.08 (0.26) |
| top-10 | 5.56 (1.71) | 1.15 (0.18) | 6.40 (0.34) |

**Holdout excess per 28 days, with 90% CIs:**

| k | vs random-k | vs LINK | vs BTC |
|---|---|---|---|
| 1 | +5.3% [+0.6, +10.8] | +1.4% [−2.8, +7.5] | +0.5% [−2.7, +4.4] |
| 3 | +4.9% [+1.4, +9.2] | +0.7% [−2.9, +5.8] | −0.2% [−2.2, +2.1] |
| 5 | +3.6% [+0.8, +6.9] | −0.5% [−3.2, +4.0] | −1.3% [−3.0, +0.5] |
| 10 | +4.5% [+2.4, +7.0] | +0.3% [−1.7, +4.3] | −0.5% [−3.1, +2.7] |

- **vs random-k:** every holdout CI excludes 0.
- **Discovery:** vs random-k +0.8% to +4.7% (CIs include 0); vs LINK +0.8% (k = 1) and −1.9% to
  −3.5% (k = 3–10).
- **Kraken-listed subset** (survivorship-biased): the same pattern; excess vs random-k is
  +3.3% to +5.1%, with CIs excluding 0.
- **Taker costs:** the conclusions are unchanged.

**Concentration:**
- **Top-1 is fragile.** It was TRX in most holdout periods, and one BNB period (Feb 2021, +374%)
  drives the full-period 26×.
- k = 3–10 are the defensible sizes. All are feasible at $58.62 with a ≥ $5 minimum order.

**Formally:** the pre-registered actionability rule is met. H4 is supported; vs random-k passes
for 4 of 4 values of k; and vs LINK the point estimate is positive for k = 1, 3, 10. That point
estimate is small, has a CI spanning 0, and **was negative in discovery for k ≥ 3**. So the rule
is met in the letter, but a low-vol basket shows no robust gain over the current holding.

## Comparison vs hold-LINK and hold-USD
- **LINK is itself low-vol within this universe:** a median 32nd volatility percentile (range
  8th–96th).
- Low-vol baskets neither reliably beat hold-LINK nor hold-BTC. The two benchmarks swap places
  between periods (discovery LINK > BTC; holdout BTC > LINK), which is consistent with R13.
- The robust economic content is relative to *random or high-vol alt selection*. Any rotation that
  moves capital up the volatility ranking has had strongly negative relative performance, in
  median and compounded terms.
- All baskets beat hold-USD in both periods.

## Robustness
- Consistent sign across 7 of 7 years, all 4 phases, both periods, and with momentum and size
  controlled.
- The beta version is weaker, so the signal is idiosyncratic or total volatility, not market beta.

## Limitations
- **Universe:** Binance's top 50 is broader than Kraken's eligible 37. The Kraken subset is
  survivorship-biased because it uses today's listings.
- **Delisted names** are marked at their last trade.
- **The mechanism is plausible but not isolated.** Low-vol names are older, larger and less
  dilutive, and log volume only partly controls for this.
- **Scope:** only 4-week rebalancing was tested.
- **The objective question stays open:** the rank or median effect is robust, but whether high
  volatility lowers the *arithmetic* mean (expected USD) was period-dependent. Discovery says
  no; the holdout says yes.

## Conclusion
- The strongest, most stable cross-sectional regularity this project has measured: **higher
  trailing volatility predicts lower subsequent relative returns** (IC −0.16 discovery, −0.25
  holdout, negative in every year).
- It supports a **risk and selection filter:** when choosing among alts, prefer the low-vol end
  and never rotate up the volatility ranking.
- It does not support switching away from LINK: LINK is already low-to-mid vol, and low-vol
  baskets don't beat hold-LINK robustly.

## What the Live Agent should independently validate
1. **Tactical-mode conflict (most decision-relevant).** The live tactical mode is triggered by
   `vol_expansion` and enters high-volatility names. X4 says those names have had strongly
   negative median and compounded relative returns (holdout high-vol 0.07×).
   - Validate on Kraken's own universe: compute vol60 ranks for the 37 eligible pairs, and check
     whether the shadow ledger's entries sit in the top vol quintile.
   - If they do, consider a filter: no tactical entry into a name above the universe's vol60
     median.
2. **Reproduce the holdout IC** on Kraken daily data for Kraken-listed assets, from Kraken
   OHLC's 720 bars (2024-10 → 2026-09): 4-weekly Spearman IC(vol60, fwd 28d). Expect a negative
   IC. A ~0 or positive IC would invalidate this for the live venue.
3. **Do not treat this as a reason to leave LINK.** The low-vol basket vs hold-LINK CI spans 0 in
   the holdout and was negative in discovery (k ≥ 3).
4. **Invalidation:** a positive IC over two or more consecutive quarters on fresh data. The
   archive updates monthly, so rerun `evaluate.py --stage holdout` with later dates.
