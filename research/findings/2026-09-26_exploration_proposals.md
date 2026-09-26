# Proposals for the live exploration sleeve (≤ 10%, ~$10): where real execution resolves what public data cannot

**Date:** 2026-09-26 · **Author:** Research Agent (cloud) · **For:** the live agent (the final evaluator)
**Label: REQUIRES VALIDATION.** These are proposals, not instructions. The core HOLD-LINK and the
exploitation gate are untouched.
**Trigger:** researcher update. 41 USDT was added, so the ~$10 exploration sleeve can now meet
Kraken's minimum orders.

## The screening principle
Capital is not evidence. A live experiment is worth running only if **its question cannot be
answered from public forward data at zero cost.** On that test:

| open question | resolvable without trading? | live needed? |
|---|---|---|
| Does any signal predict returns? (FROZEN-1, FROZEN-2, the tail-reversal bet) | **Yes:** public forward prices, frozen specs, paper outcomes | **No.** Live adds only execution realism. |
| Our own post-only fill probability and markout **in volatile markets** | **Only partly.** P3 gives strict/touch *bounds* but cannot know queue position, and it has seen **no volatile-regime sample in ~10 h** | **Yes** |
| Fee rounding, partial fills and minimum-size behaviour at $3–8 clips | No | **Yes** (as a by-product of E1) |

So there is **one** live experiment worth running now: E1, execution calibration. It is a paid
measurement, not an alpha bet. Its expected net is negative and says so.

## E1 — Live maker-execution calibration (RECOMMENDED)

**Hypothesis:**
- (H-a) Our own post-only orders at the touch fill within 5 min at a rate inside P3's virtual
  [strict, touch] bounds for the same pair and regime, and their 5-min markout lies inside P3's
  CI. If so, P3's free virtual sampler is **calibrated** and can replace live testing.
- (H-b) In the **volatile** regime (|1d return| / σ30 ≥ 1.5, the `execution_stats` definition),
  the fill probability is below the 50% prior in `edge.py`, or the markout is worse than the
  calm −5 bps.

**Universe:** low-volatility majors only (consistent with the X4 veto), all USDT-quoted to use
the new USDT without a conversion leg:

| pair | ordermin | ≈ notional | spread |
|---|---|---|---|
| LINKUSDT | 0.55 | $7.9 | 3.3 bps |
| XBTUSDT | 0.00005 | $4.2 | 0.01 bps |
| ETHUSDT | 0.001 | $2.7 | 0.04 bps |
| XRPUSDT | 1.65 | $2.6 | 0.8 bps |

LINK matters most, because it is the core asset for any future core switch.

**Protocol (fixed before any order):**
1. **Schedule:** Poisson times, mean one attempt per pair per day, plus one immediate attempt
   (max 1/day/pair) whenever the pair's regime flips to *volatile*. The volatile stratum is the
   point of the experiment.
2. **Buy leg:** post-only BUY at the best bid, minimum size. If unfilled at 30 min, cancel. Never
   cross (`edge.should_cross_spread` stays as is).
3. **Sell leg:** on fill, post-only SELL at the best ask. If unfilled after 15 min, re-post at the
   new best ask, repeating up to 24 h. Still never cross; this is inventory risk, bounded below.
4. **Record per order:** submit time, fill time, fill fraction, realised fee, mid at submit/fill
   and at +1/5/30 min after the fill, regime and vol ratio. That means post-fill **markout**
   (audit P7), not only the existing `adverse_bps`.
5. **Logging:** alongside each live order, log P3's virtual prediction for the same pair and
   moment, so the comparison is paired.

**Horizon:** minutes per round trip; 4–6 weeks in total, or until the resolution targets are
met.

**Expected gross and net edge (honest):**
- **Gross per round trip** ≈ the quoted spread captured minus the markout on both legs. P3 calm
  data for LINK has markout −4 to −6 bps per leg (CIs ±15 bps), and majors (Q1) −1 to −1.5 bps.
  So gross ≈ −10 to 0 bps.
- **Fees:** 2 × 0.40% = 80 bps.
- **Net ≈ −0.8% to −0.9% per round trip** ≈ **−$0.02 to −$0.07 per trip** at $2.6–7.9. About 60
  trips ≈ **−$2 to −$4 expected.** This is the price of the information.

**Maximum loss:**
- **Hard stop:** a cumulative realised cost (fees + P&L) of **−$5.00** ends the experiment.
- **Per trip:** inventory ≤ one minimum clip (≤ $7.9). A stranded sell leg in a −10% day costs
  ≤ $0.80.
- **Sleeve:** never more than 10% of the portfolio, and never more than one open inventory per
  pair.

**Resolution criteria:**
- **(H-a) calibrated** if the live 5-min fill rate's 95% CI overlaps P3's [lower, upper] bracket
  for the same pair and regime, **and** the live markout's CI overlaps P3's.
  - **Needs:** ≥ 30 filled calm round trips pooled across pairs, and ≥ 10 LINK.
  - **If calibrated:** stop live calibration and use P3 thereafter.
  - **If not:** P3's bias is measured, and virtual results get corrected by it.
- **(H-b) resolved** at ≥ 10 volatile-regime attempts. Report the fill probability with a
  Clopper–Pearson CI and the markout with a bootstrap CI.
  - **Where it's used:** `edge.py`'s volatile fill prior (0.50) and `execution_stats` are
    replaced by the measured values, never tuned to make a trade pass.
- **Stop:** the budget is exhausted, or 6 weeks pass. Report whatever n was reached, with MDEs.

**Why live execution is necessary:**
- Public trades show *that* someone traded at our price, not whether **our** queued order would
  have been ahead. The strict/touch gap is the ignorance band, and in fast markets it is the whole
  question.
- Only own orders measure real fee rounding and partial fills at $3–8.
- P3 has not observed a single volatile-regime order yet, and may not before its 2026-10-10
  deadline.

## E2 — The live agent's armed LINK tail-reversal bet: research opinion
- **Hypothesis:** after a daily move ≥ 2.5σ, the next day reverses. Universe: LINK.
  Horizon: 1 day.
- **Expected net:** the in-sample estimate (+1.94%, n = 17) did **not** replicate on disjoint
  earlier history (X10): Binance +1.3% (p = 0.26), Coinbase −1.5%, and h = 2/3 negative on both.
  The best estimate is **≈ 0 ± 2% per trade**.
- **Execution:** post-only, 2 legs, at the minimum clip.
- **Maximum loss:** at the minimum clip ($7.9), the live agent's stop (2 × 4.54% daily σ) caps a
  trade at ≈ $0.72.
- **Resolution:** not resolvable in practice. There are ~5–9 triggers per year; the MDE at n = 5
  is ~11%, and 30 triggers take years.
- **Why live:** **for the signal, it isn't.** Paper outcomes on public prices answer that for
  free. Live adds only volatile-day execution evidence, which E1's volatile stratum collects
  anyway.
- **Recommendation:** keep it armed only at the minimum clip, as a volatile-regime E1 sample.
  Always log the paper outcome. Do not size it by conviction.

## Not proposed, and why
- **Any high-vol or memecoin exploration position:** X4/X4b show a negative rank and median.
  FROZEN-2 is already measuring the arithmetic-mean question forward, at zero cost.
- **Short-horizon LINK timing:** X8 and the live agent's own arithmetic show it is dead at 0.92%.
- **Relative value:** X9 (median trade negative in every window).
- **Micro-arbitrage and spread capture:** R11 (5–46× short of the fee floor).
- **Scaling any of these with the new capital:** capital does not change a sign.

## Minor operational notes for the live agent
- The 41 USDT can fund E1 directly through USDT pairs. Converting to USD (USDTUSD, 0.1 bps
  spread, 0.40% maker fee) would cost ~$0.16 for no benefit.
- For the benchmark: the passive benchmark is 4.1944857200 LINK, and the 41 USDT deposit is new
  capital. Valuing it at face in both the portfolio and a "benchmark + deposit" series keeps the
  comparison honest. This is a researcher/live-agent accounting decision; I'm only flagging it.
