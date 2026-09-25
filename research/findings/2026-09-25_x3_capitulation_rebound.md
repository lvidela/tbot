# Finding X3: no detectable rebound after market-wide capitulation days; rotating LINK into the most-crashed coins loses

**Date:** 2026-09-25 · **Author:** Research Agent (cloud) · **Branch:** `research/x3-capitulation`
**Label: INCONCLUSIVE** for the information tests: the signs point the registered way, nothing is
significant, and the MDEs are large. **NEGATIVE** for the tactical rule (E1): it is negative in
both periods, and significantly so at stress costs.

## Question
After a market-wide forced-selling day, do crypto prices rebound within 1–5 days, and do the
most-crashed assets rebound most? Could a LINK holder profit by rotating into the crashed names
for 3 days, or a USD holder by buying?

## Hypothesis (pre-registered)
`research/x3_capitulation/PREREGISTRATION.md` (`c2f21c7`) was committed before any event was
computed. Discovery was committed (`cb4ca00`) before the holdout was run.
- **Event:** the equal-weight universe day return ≤ −2.5 × its 60-day sd, BTC down, and events at
  least 5 days apart.
- **Primary tests at h = 3:**
  - P1: EW excess over the unconditional mean;
  - P2: IC(crash size, rebound) < 0;
  - P3: LINK excess.
- **Threshold:** Bonferroni α = 0.0167.

## Data sources / period / timestamps
- X1's survivorship-free Binance daily panel: 471 assets, including delisted ones, fetched
  2026-09-25 22:40–23:05Z, with Coinbase cross-check correlation ≥ 0.989.
- **Discovery:** 2020-03-15 → 2023-12-31, **23 events** (6.1/yr).
- **Holdout:** 2024-01-01 → 2026-09-19, **12 events** (4.4/yr). Dates are in `results/*.json`.
- **Note:** the COVID crash (2020-03-12) falls before the pre-registered discovery start. The
  60-day history requirement put it there, not an exclusion.

## Methodology
- Entry at close(T), the close at which the event becomes known.
- Unconditional benchmarks come from non-overlapping h-day windows in the same period.
- **Economics:** per event, maker 0.46% per leg and stress 0.92% per leg; percentile-bootstrap
  90% CIs.
  - E1 is a LINK holder rotating into the 3 or 5 most-crashed names for 3 days (4 legs), vs
    holding LINK.
  - E2/E3 are a USD holder buying LINK or the EW universe (2 legs).
- **Reproduce:** `python3 research/x3_capitulation/evaluate.py --stage discovery|holdout`.
- **Tests:** `test_x3.py` (3/3) covers no look-ahead in the sd, event gap/detection, and a
  planted rebound found with a quiet null.

## Results

**Information (h = 3):**

| test | discovery mean | t | MDE | holdout mean | t | one-sided p | MDE |
|---|---|---|---|---|---|---|---|
| P1 EW excess | +1.9% (median +2.2%) | +1.35 | 4.0% | +1.4% (median −0.7%) | +0.68 | 0.26 | 5.6% |
| P2 IC(crash, rebound) | −0.072 | −1.71 | 0.118 | −0.079 | −1.25 | 0.12 | 0.177 |
| P3 LINK excess | +0.6% | +0.33 | 5.0% | +3.0% (median −1.1%) | +0.92 | 0.19 | 9.2% |

- No test passes in either period. **H3 is not supported.**
- **Robustness:** the signs are not stable.
  - h = 5: P1 −0.3% / −0.2%.
  - 3σ events: discovery P1 −1.0% (n = 14), holdout +4.9% (n = 6).
  - 2σ events: holdout P1 −1.5% (n = 23).
- The one nominally notable cell, holdout 3σ P3 (t = +2.14), rests on **6 events** and is one of
  roughly 30 cells. It is noise until shown otherwise.

**Economics (per event):**

| rule | discovery mean (90% CI) | holdout mean (90% CI) | holdout per year |
|---|---|---|---|
| E1: LINK → worst-3, maker | −1.2% [−3.8, +1.4] | −3.8% [−9.1, +0.9] | −16.7% |
| E1: LINK → worst-3, stress | −3.0% [−5.6, −0.5] | −5.6% [−10.9, −1.0] | −24.8% |
| E1: LINK → worst-5, maker | −1.2% [−2.9, +0.5] | −4.0% [−9.1, +0.5] | −17.9% |
| E2: USD → LINK, 3 days | +0.5% [−2.4, +3.7] | +2.7% [−2.6, +8.6] | +12.0% |
| E3: USD → EW universe, 3 days | +1.6% [−0.6, +3.8] | +0.1% [−2.9, +3.4] | +0.6% |

- E1's median is negative in both periods.
- E2's positive mean has a negative median (−2.1%) and a CI spanning 0.

## Comparison vs hold-LINK and hold-USD
- **vs hold-LINK:** the tactical rotation loses in both periods at maker costs (point estimates)
  and significantly at stress costs.
- **vs hold-USD:** buying after capitulation is indistinguishable from not buying.
- The live account is already fully in LINK, so E2/E3 would matter only if it were in USD.

## Limitations
- **Only 35 events** in six years, so the MDEs are 4–9% per event. Rebounds smaller than that
  cannot be detected.
- **Daily resolution.** Intraday capitulation (hourly liquidation cascades) was not tested. An
  hourly version needs the 1h archive and was deferred per the pre-registration logic.
- **Entry at close is optimistic** on crash days, which is why stress costs are reported.

## Conclusion
- No capitulation-rebound effect large enough to detect exists in six years of daily data.
- Tilting toward the most-crashed names looks directionally consistent (P2 < 0 in both periods),
  but it is small, not significant, and swamped by 4-leg costs.
- **Rotating LINK into crashed coins after sell-offs is value-destroying** in this sample.

## What the Live Agent should independently validate
1. **No action is recommended.** If any tactical logic treats a market crash as an entry signal
   for high-beta or most-crashed names, this evidence and X4 (high-vol names underperform) both
   argue against it.
2. **Invalidation:** an hourly-resolution study with many more events, or a regime with frequent
   capitulations. A pre-registered rerun of `evaluate.py` on later data would show it.
