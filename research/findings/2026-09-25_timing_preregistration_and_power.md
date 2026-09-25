# Finding: LINK/USD market-timing test (T1) is pre-registered and built, but it cannot resolve the live decision

**Date:** 2026-09-25 · **Author:** Research Agent (cloud session) ·
**Label: INCONCLUSIVE (design and power result; the empirical test has not been run, no market data was reachable)**

## Question
Can a small, pre-registered set of market-level signals forecast LINK's forward return vs USD
over 5–20 days well enough to beat hold-LINK after a 0.92% switch cost? And before running it:
could such a test, on the best data that exists, detect an effect large enough to change the
live decision?

## Hypothesis
Registered in `research/timing/PREREGISTRATION.md`, commit `16cbda7`, before any data. Six
signals (BTC SMA200, BTC SMA50, LINK SMA50, LINK drawdown < −30% from its 90d max, LINK 20d vol
> 1.5× its 1y median, Binance LINK funding 7d mean > its 1y 90th percentile) × horizons
{5, 10, 20} days = 18 tests. The direction of each is fixed a priori.

Amendments A1–A5 were all made before any data was seen: replication rule, how tilts combine,
unconditional mean, S6 perturbation bound, SMA perturbations. A4 was found by the synthetic
end-to-end smoke test.

## Data sources / period / timestamps
**None obtained.** At 2026-09-25T15:44Z and again at 15:55Z, every public market-data host
returned **proxy 403 (environment network policy)**:
- `api.kraken.com`, `api.exchange.coinbase.com`, `api.binance.com`, `fapi.binance.com`,
  `data.binance.vision`, `www.okx.com`, `api.bybit.com`, `www.deribit.com`,
  `min-api.cryptocompare.com`.
- The log is in `research/data/raw/_fetch_log.jsonl`.
- I did not route around the denial.

Planned sources and period are in the pre-registration: Coinbase primary, Binance and Kraken
cross-check, mid-2019 → 2026-09-24, Binance/Bybit funding from 2020.

## Methodology (what was done here)
1. **Complete reproducible pipeline:** `research/timing/{fetch,data,signals,evaluate,run}.py`.
   - Data: unauthenticated fetch with provenance, and a cross-exchange divergence check.
   - Test design: non-overlapping, phase-averaged windows with a conservative SE (no credit for
     phase averaging), and a chronological holdout with the in-sample table written to disk first.
   - Controls: sub-periods, ETH/SOL replication, 4 perturbations per signal, 1-day execution lag,
     taker cost, and a Bonferroni(18) plus circular-shift family-wise permutation.
   - Outputs: MDE for every cell, the pre-registered labelling rule, and a shrinkage decision
     analysis at the latest date.
2. **Tests:** `research/timing/test_timing.py`, 11/11 pass. They cover:
   - no look-ahead in signals;
   - window alignment and cost accounting;
   - null false-positive rate ≤ nominal (150 random-walk replications);
   - planted-effect detection;
   - an end-to-end run on synthetic raw files in the exact fetcher format.
3. **Power study** (`research/timing/power.py`, 250 replications per cell, `results/power.json`):
   - The real `evaluate()` is run on synthetic LINK-like returns: Student-t(4) innovations,
     stochastic volatility, daily sd 4.5%.
   - Signals are Markov regimes, P(ON) = 0.55, mean ON-duration 10 / 40 / 100 days.
   - Planted drift gaps are 0–400%/yr. Each is reported as the **implied conditional h-day
     spread**, i.e. what the signal state at t can actually forecast.
4. **Value of information** (`research/timing/evsi.py`, `results/evsi.json`): the expected USD
   value, on the $58.94 account, of running T1 before the one-shot "stay in LINK / exit to USD"
   decision. It uses normal preposteriors and sweeps the priors.

## Costs and account assumptions
- Maker leg 0.46% (0.40% + 5.4 bps adverse selection); taker 0.83%.
- An out-and-back switch is 2 legs (0.92%). Exit-and-stay to the end is 1 leg, since the account
  is valued in USD.
- Account $58.94. LINK ordermin 0.55 LINK (~$7.7), so a full switch is always feasible.

## Results

**Effect size that would change the live decision.** Exiting pays only if
E[R₂₀ | current state] < −0.46%. With the state OFF, that needs a conditional spread
d > (μ + 0.46%) / 0.55, where μ is the unconditional 20-day drift:

| μ | required d |
|---|---|
| 0 | 0.8% |
| +1% | 2.7% |
| +2.2% (in-repo estimate) | 4.9% |

**So the decision-relevant range is d ≈ 1–5% per 20 days.**

**What the test can detect (full sample ≈ 2,440 days after warm-up).**
- SE of the 20-day spread ≈ 3.8% (S6 ≈ 4.6%; holdout ≈ 5.9%).
- Analytic MDE at 80% power:
  - h = 20: 10.3% unadjusted, **14.0% Bonferroni**.
  - h = 5: 2.6% / 3.5% per 5 days, equivalent to ~10–14% per 20 days.

Simulated power, as the probability of passing Bonferroni at any horizon (criterion a). Each
cell shows the implied 20-day spread first, then the power:

| drift gap between regimes | ON 10d (fast: vol/crash-like) | ON 40d (SMA50-like) | ON 100d (SMA200-like) | holdout, ON 40d |
|---|---|---|---|---|
| 50%/yr | 0.6% → 0.00 | 1.7% → 0.00 | 2.2% → 0.01 | 1.7% → 0.01 |
| 100%/yr | 1.2% → 0.01 | 3.4% → 0.03 | 4.5% → 0.05 | 3.4% → 0.00 |
| 150%/yr | 1.8% → 0.04 | 5.0% → 0.16 | 6.7% → 0.22 | 5.0% → 0.05 |
| 200%/yr | 2.4% → 0.11 | 6.7% → 0.36 | 8.9% → 0.37 | 6.7% → 0.07 |
| 300%/yr | 3.7% → 0.44 | 10.1% → 0.82 | 13.4% → 0.84 | 10.1% → 0.30 |
| 400%/yr | 4.9% → 0.74 | 13.4% → 0.98 | 17.9% → 0.97 | 13.4% → 0.60 |

- **Persistent (trend-type) signals:** within the decision-relevant 1–5% range, power is
  **≤ 16% on the full sample and ≤ 5% in the holdout**. ~80% power arrives only at implied
  20-day spreads of 10–13%.
- **Fast-decaying signals (~10-day regimes):** the 5-day horizon does better, with power of
  **44–74% for implied 20-day spreads of 3.7–4.9%**, the top of the relevant range. That needs a
  300–400%/yr drift gap between regimes. Power is ≤ 11% below ~2.5%, and 7–26% in the holdout.
  So T1 is not powerless everywhere. It can catch a large, fast-mean-reverting state effect,
  but not a moderate one, and not any trend-type effect.
- **Winner's curse:** when an h = 20 cell passes Bonferroni, its mean estimated spread is 12–22%,
  whatever the true value (5–13%). A significant 20-day hit would overstate the effect
  about 2–3×.
- **Cross-asset pooling barely helps.** Averaging over k = 3–4 assets at ρ = 0.6–0.85 cuts the
  SE by only 5–16%.

**Value of information** (normal approximation, priors swept over μ₀ ∈ {0, 1, 2}%/20d,
prior sd of μ ∈ {2, 3, 5}%, τ ∈ {1.5, 3, 6}%):
- Running T1 is worth **$0.02–$1.15** on this account.
- The **signal part is worth $0.00–$0.53**. It is ≤ $0.13 unless one assumes τ = 6%, i.e. a prior
  that regime spreads of ±6%/20d are typical.
- Most of the value comes from re-estimating LINK's **unconditional** drift, not from the signals.

## Statistical evidence
Nothing empirical, by design and by necessity. The power and EVSI numbers are properties of the
test design under stated assumptions, not claims about the market.

## Robustness of the design result
- The conclusion holds across regime persistence (10 / 40 / 100 d), for fat tails, and with
  stochastic volatility.
- It is driven by one fundamental: estimating a drift difference needs calendar time, not more
  frequent sampling. Seven years of 20-day windows is ~120 observations with sd ≈ 20%.
- The exception is fast-decaying regimes, where short horizons carry most of the forecastable
  effect. See the ON 10d column.
- Using a less conservative phase-averaged SE (e.g. block bootstrap) would raise power somewhat
  for short-lived signals (10-day regimes). It cannot move the 20-day MDE from ~14% into the
  1–5% range.
- If LINK's true daily sd is 3.7% (its recent 60d value) instead of 4.5%, the SE falls by about
  18%. The conclusion does not change.

## Limitations
- No real data. The null false-positive rate of my conservative SE is below nominal for
  short-lived signals, so power here is, if anything, slightly understated for those. Even so, it
  cannot reach the decision-relevant range: see Robustness.
- The Markov-regime model is a simplification of real SMA or funding signals.
- The EVSI priors are assumptions, and they are swept.
- The EVSI covers only the single remaining decision. It does not value what T1 would teach for
  future experiments.

## Conclusion
- **Even on ~7 years of data, the pre-registered timing test mostly cannot distinguish the
  effect sizes that would change the live LINK-vs-USD decision (1–5% per 20 days) from zero.**
  - For trend-type signals, its Bonferroni MDE is ~14% per 20 days and its power in the
    relevant range is ≤ 16%.
  - The one exception is a large, fast-decaying state effect (a ~10-day regime with a
    300–400%/yr drift gap). The 5-day horizon would catch that with ~45–75% power.
- A null result would therefore be uninformative. Under the pre-registered rule it can only come
  out INCONCLUSIVE, since NEGATIVE needs an MDE ≤ 3%.
- A significant hit would most likely be an inflated draw.
- The expected dollar value of the answer before 2026-10-15 is tens of cents. It comes mostly
  from the unconditional drift, which earlier in-repo work already found unresolvable (CI
  straddles zero).
- This extends F1: the exposure lever is large, but **no available data can tell us which way to
  pull it**.
- Absent new information, the lowest-cost action (HOLD, $0) is the rational default. It is not
  evidence that LINK will outperform USD.
- The pipeline is ready. If researchers allow the exchange hosts, it runs in minutes and should
  still be run, because it is cheap and pre-registered. Its output must be read through the
  pre-registered shrinkage analysis (section 6), not the significance test.

## Recommended next experiment
1. **(Researchers)** Allow `api.exchange.coinbase.com`, `api.binance.com`, `fapi.binance.com`
   and `api.bybit.com` for this environment, then run:
   `python3 research/timing/fetch.py && python3 research/timing/run.py`
2. **Do not spend further effort on LINK-vs-USD timing signals before 2026-10-15.** By
   construction, their value of information on this account is under ~$0.5.
3. The same power limit applies to "which single asset to hold" (LINK vs ETH vs SOL). A 20-day
   relative-return difference has an sd of roughly 10–15%, so the MDE is several percent
   against cost differences of ~0.9%. Pursue it only with a structural rather than statistical
   argument.
4. The only lever that is both large and decision-changing without forecasting is risk. For
   example, a LINK/USD split changes the final-value distribution without needing an edge. Under
   the stated risk-neutral objective ("maximize final USD value") a split is never optimal in
   expectation. It is a researcher-level question whether variance matters, not a research
   question.

## What the Live Agent should independently validate
1. Compute the current S1–S5 states from Kraken's own 720-day daily OHLC. Its authenticated
   environment can reach public Kraken. The warm-up of ≤ 365 days fits in 720 bars.
2. If any signal is OFF, do not act on it alone. Per this finding, its conditional-mean evidence
   cannot exceed the MDE, and the pre-registered shrinkage weight is ~0.38 at τ = 3%.
3. Re-measure LINK's realised daily sd (30/90 d) and confirm it lies in 3.5–6%, the range the
   power result assumes.
4. Confirm that the exit-and-stay cost is one maker leg (~0.46%) and that the terminal valuation
   needs no buy-back leg.
