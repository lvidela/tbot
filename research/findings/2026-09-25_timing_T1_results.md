# Finding: T1 results. No market-level signal forecasts LINK vs USD over 5–20 days; stay in LINK

**Date:** 2026-09-25 · **Author:** Research Agent (cloud session) ·
**Label: INCONCLUSIVE (all 6 signals, under the pre-registered rule). The decision analysis supports HOLD LINK.**

## Question
Can a pre-registered set of market-level signals forecast LINK's forward return vs USD over
5–20 days well enough to beat hold-LINK after costs? This is the empirical run of the design in
F2 (`2026-09-25_timing_preregistration_and_power.md`).

## Hypothesis
`research/timing/PREREGISTRATION.md`:
- Pushed to the remote as `3960fe4` (original) and `cbbec6d` (amendments A1–A5), both before any
  data was downloaded. They are byte-identical to local commits `16cbda7` and `cefdc74`.
- A6 (data-source substitution) is local commit `e65de1c`, made before the first download.
- Nothing was amended after data was seen.

## Data sources / period / timestamps
Downloaded 2026-09-25 between ~17:20Z and ~17:45Z. Each file records its URL and `fetched_at`
under `meta`; see also `research/data/raw/_fetch_log.jsonl`.

| series | source | range | rows |
|---|---|---|---|
| LINK, BTC, ETH, SOL daily (primary) | Coinbase Exchange public candles | LINK 2019-06-27, BTC/ETH 2019-01-01, SOL 2021-06-17 → 2026-09-25 | 2648 / 2825 / 2825 / 1927 |
| same (cross-check) | `data.binance.vision` spot 1d archive (the API returns 451, geo-blocked) | 2019 → 2026-09-24 | 2809 / 2824 / 2824 / 2236 |
| same (cross-check) | Kraken public OHLC (last 720 bars) | 2024-10-05 → 2026-09-25 | 721 each |
| LINK funding (S6) | `data.binance.vision` USDⓈ-M fundingRate archive | 2020-01-17 → 2026-08-31 | 7256 prints |
| LINK funding (cross-check) | OKX funding-rate-history (Bybit returned 403, geo-blocked) | recent months | 287 prints |

- The analysis stops at 2026-09-24, so today's partial bar is excluded.
- There are no missing days in any primary series.

**Cross-check (Coinbase vs Binance/Kraken):**
- Agreement: the median signed log ratio is 0.0–1.6 bps and daily-return correlation is ≥ 0.999.
- 12 days exceed the 2% flag. Every one sits in a known USD/USDT dislocation or thin-listing
  episode:
  - LINK's first Coinbase days, 2019-06-28 and 06-29;
  - the Tether/Bitfinex USDT de-peg, 2019-04-26 → 05-11;
  - the COVID crash, 2020-03-12.
- These reflect the USDT basis, not errors in the primary USD data. Coinbase vs Kraken: 0 flags
  and p99 ≤ 19 bps.
- Funding: Binance vs OKX over 71 common days has correlation 0.79 and a median absolute
  difference of 1.6e-5 per 8h (0.0016%), against daily funding levels of order 1e-4.

## Methodology
As pre-registered: `python3 research/timing/run.py --perm 2000`. All outputs are in
`research/timing/results/`.
- Non-overlapping windows, averaged over all phases, with a conservative SE.
- Maker cost 0.46%/leg (taker 0.83%) is charged on every state change. The account starts in LINK.
- In-sample (to 2023-12-31) was written to disk before the holdout (2024-01-01 → 2026-09-24).
- Controls: Bonferroni over 18 tests, and a family-wise circular-shift permutation (2,000 draws,
  shifts ≥ 90 d).
- Robustness: 3 sub-periods, ETH/SOL replication, 4 perturbations per signal, a 1-day execution
  lag, and taker cost.

**Sample size:** 2,640 LINK days → per phase about 520 / 260 / 130 non-overlapping windows at
h = 5 / 10 / 20 for S1–S3. There are fewer after warm-up for S4–S6: S6 has ~2,050 days, with only
6–26 OFF windows per phase.

**Account assumptions:**
- $58.94 account.
- LINK ordermin is 0.55 LINK, so a full switch is feasible.
- Exit-and-stay costs 1 leg; an out-and-back switch costs 2 (0.92%).

## Results (full sample, h-day spread = mean R | ON − mean R | OFF)

| signal | best h | spread | 95% CI | t | Bonferroni MDE | mean excess vs hold-LINK per window (maker) | holdout t | label |
|---|---|---|---|---|---|---|---|---|
| S1 BTC>SMA200 | 10 | +1.6% | [−2.6, +5.7] | 0.76 | 8.1% | −0.48% | −0.21 | INCONCLUSIVE |
| S2 BTC>SMA50 | 5 | +1.8% | [−0.2, +3.8] | **1.77** | 3.9% | −0.08% | 0.16 | INCONCLUSIVE |
| S3 LINK>SMA50 | 5 | +0.9% | [−1.1, +2.9] | 0.89 | 3.9% | −0.34% | 0.63 | INCONCLUSIVE |
| S4 no crash | 20 | −0.1% | [−8.6, +8.4] | −0.02 | 16.8% | −1.58% | 0.48 | INCONCLUSIVE |
| S5 calm vol | 10 | +0.3% | [−6.5, +7.2] | 0.10 | 13.7% | −0.19% | 0.71 | INCONCLUSIVE |
| S6 funding not crowded | 20 | −1.1% | [−11.9, +9.7] | −0.22 | 22.5% | −0.28% | 0.36 | INCONCLUSIVE |

The full 18-cell table is in `results/full.json`. Statistics:
- **Bonferroni critical |t| ≈ 3.0. No cell passes.** The largest |t| is 1.77 (S2, h = 5).
  Unadjusted p = 0.078.
- **Family-wise permutation p = 0.47.** The observed max |t| of 1.77 equals the null median
  (1.74); the null 95th percentile is 2.49. The best signal looks exactly like the best of 18
  random alignments.
- **All 18 cells have negative mean excess vs hold-LINK at maker cost** (−0.08% to −1.79% per
  window) and at taker cost. On average, timing LINK with these signals lost money after costs.
- **Holdout (2024–26):** no cell has |t| > 1.23.
  - Criterion (c), a registered-direction spread plus positive net excess, is met by S3 h = 10,
    S5 h = 5/10/20 and S6 h = 20. Their net excess is only +0.03% to +0.36% per window, with
    |t| ≤ 1.23 and few OFF windows.
  - None of them passes (a) or (b) in the full sample.
- **Direction:** S4, S5 and S6 mostly point *opposite* to the registered direction. After
  crashes, high volatility and crowded funding, LINK did slightly better, not worse. None of
  this is significant.

**The one pattern worth recording, not acting on: S2 (BTC above its 50-day SMA).**
- Its spread is positive in all 3 sub-periods (t = 1.44 / 1.18 / 0.16).
- The same BTC signal applied to ETH gives t = 2.56 and to SOL t = 2.09 at h = 5. Those are not
  independent evidence, because the returns are ~0.8 correlated and the signal is identical.
- It holds under all 4 perturbations (t = 1.30–2.10).
- By compounded wealth (median over phases) it ended at 17.9× vs 5.3× for hold-LINK over the
  full sample. That came almost entirely from sitting out 2019–2022 crashes.
- **In the holdout it lost: 0.71× vs 0.86×**, spread t = 0.16, with ~73 switches per phase over
  the full sample.
- Its arithmetic mean excess per window is −0.08%, i.e. zero. The wealth gap comes from lower
  variance drag during crashes, not from a higher expected return per window.
- It fails Bonferroni, the permutation test, and holdout criterion (c).

**Decision analysis (pre-registered §6, as of the 2026-09-24 close):**
- Current states: **S1–S5 are all ON (hold LINK)**. S6 is unknown, because the funding archive
  ends 2026-08-31 (A6).
- Unconditional LINK 20-day mean is **+3.7% (SE 2.0%, n = 132 non-overlapping windows, t = 1.83)**.
- The shrunk 20-day forecast is +3.9% / +4.3% / +5.0% for τ = 1.5% / 3% / 6%. That is far above
  the −0.46% exit threshold. **Exit to USD: no, under every τ.**
- The unconditional mean dominates the forecast. It is a 2019–2026 average that includes the
  2020–21 bull run, and it should not be read as a forecast of +3.7% over the next 20 days.
  - Removing the extreme 2020 period would not move the forecast below −0.46% unless LINK's
    true drift were negative.
  - Even so, the conditional tilt from the signals is only +0.1 to +1.3 pp.

## Comparison vs hold-LINK and hold-USD
- **Every timing rule underperformed hold-LINK in arithmetic mean per window after costs.**
- Against hold-USD, strategy net means were positive in-sample, because LINK rose over the
  sample. Most of that is LINK's drift, not timing.
- Holdout 2024–26:
  - Hold-LINK wealth: 0.83–0.86×. LINK lost money over the holdout, so hold-USD beat hold-LINK there.
  - Timing rules: 0.71–1.36×. The best was S3 at h = 20 (1.36×), a single-period outcome with
    holdout t = 0.61 that is not significant.

## Robustness
Nothing passes, so there is nothing whose robustness needs testing. Beyond that:
- **Execution lag:** a 1-day lag lowers S2's t from 1.77 to 1.71.
- **Taker cost:** makes every cell's excess more negative.
- **Power assumptions:** LINK's realised daily sd is 5.44% (full), 3.32% (last 90 d) and 3.97%
  (last 30 d). The actual h = 20 SE was 4.4%, against 3.8% assumed in F2, so the real test was a
  little *less* powerful than F2 predicted. The Bonferroni MDE at h = 20 was 16.6–17.1% for
  S1–S4 (F2 predicted ~14%). F2's prediction held.

## Limitations
- The minimum detectable effect is 3.9–8% at h = 5–10 and ~17% at h = 20. Per F2, that is far
  above the 1–5%/20d that would matter. **This is a failure to detect, not evidence of no
  effect** (registry D5).
- S6 is based on 6–26 OFF windows per phase, and it lacks the last 3–4 weeks of funding data.
- Binance's archive and OKX stood in for the geo-blocked Binance API and Bybit (A6). The data is
  the same, apart from Bybit being unavailable for cross-checking.
- The in-sample period includes an exceptional bull run (2020–21) and crash (2022). Sub-period
  t-statistics are small everywhere.

## Conclusion
- None of the six market-level signals forecasts LINK's 5–20-day return vs USD distinguishably
  from chance, whether tested individually, as a family (p = 0.47), or out of sample.
- Timing with them cost money on average after fees.
- The pre-registered decision analysis says **stay in LINK**: every current signal is ON, and the
  forecast is positive under all priors.
- This agrees with the live agent's current HOLD. It does **not** show that LINK will outperform
  USD before 2026-10-15; the unconditional drift itself has t = 1.83.
- Taken with F1 and F2, the exposure lever is large, the available data cannot aim it, and
  switching costs money. HOLD is the choice that does not pay for an unproven forecast.

## Recommended next experiment
1. **Stop LINK-vs-USD signal research for this experiment.** Its value of information is under
   ~$0.5 (F2), and the empirical run found nothing.
2. **If a future experiment wants to revisit timing:** pre-register S2 (BTC > SMA50) alone, at
   h = 5, with a fresh forward holdout and the Bonferroni burden reduced to 1 test. It is the only
   cell with consistent sign across sub-periods, assets and perturbations.
   - Expect its true effect, if any, to be well below the in-sample +1.8%/5d (winner's curse, F2).
   - Its 2024–26 holdout was flat to negative.
   - It needs ~70 switches per 7 years (≈ 0.9% each), so any real edge must beat roughly 9%/yr
     in costs.
3. Re-run `run.py` after 2026-10-01, when the September funding archive is published, to fill in
   S6's current state. By F2, that is worth cents.

## What the Live Agent should independently validate
1. **Current signal states from its own Kraken 720-day OHLC:**
   - S1: XBTUSD close > 200d SMA
   - S2: XBTUSD close > 50d SMA
   - S3: LINKUSD close > 50d SMA
   - S4: LINK drawdown from its 90-day max > −30%
   - S5: 20d vol ≤ 1.5× its 365d median

   This run found all five ON as of 2026-09-24. A flip to OFF is **not** by itself a reason to
   exit: no OFF state had a detectable effect.
2. That LINKUSD on Kraken matches Coinbase closely (this run: p99 difference 19 bps), so these
   results apply to the Kraken account.
3. That an exit-and-stay costs one maker leg (~0.46%), so any future exit case must forecast a
   20-day LINK return below −0.46%. Nothing tested here gets there.
