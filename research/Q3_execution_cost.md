# Q3 — Can execution cost be structurally reduced, and is the 4-leg model correct?

**Date:** 2026-09-24
**Script:** `/home/lisandro/backtests/execution_cost_model.py`
**Full numeric output:** `/home/lisandro/backtests/execution_cost_model_output.txt`
**Data:** `/home/lisandro/data/cache/` (37 pairs; 1d 240–721 bars, 4h 721 bars, 1h 721 bars),
`/home/lisandro/data/universe.json` depth snapshot, `/home/lisandro/data/execution_log.json` (n=2 fills).
**No Kraken API calls. No orders placed.**

---

## MEASURED vs MODELLED — read this first

| Quantity | Status | Value |
|---|---|---|
| Maker fee rate | **MEASURED**, n=2 | 0.4000%/leg exactly |
| Taker all-in per leg | **MEASURED** (REGISTRY A1) | 0.831%/leg |
| Adverse selection, CALM | **MEASURED**, n=2 | 5.4 bps/leg (4.7, 6.1) |
| Adverse selection, VOLATILE | **MODELLED** (n=0 real fills) | 8.5 bps/leg |
| Maker fill probability, CALM | **MEASURED**, n=2 | 2/2 — exact binomial 95% CI **[0.16, 1.00]** |
| Maker fill probability, VOLATILE | **MODELLED**, n=0 | 0.65, range 0.40–0.85 |
| Book depth / est. slippage | **MEASURED** snapshot | see §4 |
| E&#124;move&#124; by holding period | **MEASURED** from 1d bars | see §2 |
| Touch probability from bars | **MEASURED** bar statistic (≠ a fill) | see §3 |
| Queue-clearing times | **MODELLED**, falsified by our one real check | see §3 |
| All leg-count arithmetic | **MODELLED** (it is arithmetic) | see §1 |

We have **two** real fills in the entire system. Both were LINKUSD rebalances, both in
CALM conditions, both with no directional signal — the easiest possible execution case.
Every statement below about volatile-regime execution is a model.

---

## 1. LEG COUNTING — **4 legs is wrong. The marginal cost is 2 legs.**

### 1.1 The error

The current model charges every tactical trade `sell LINK → buy ALT → sell ALT → buy LINK`
= 4 legs. Two things are wrong with that.

**(a) The LINK exit is a one-time campaign cost, not a per-trade cost.** Once we are out of
LINK, the marginal cost of taking *one more* tactical opportunity is exactly the alt round
trip: buy ALT, sell ALT = **2 legs**. Charging the LINK exit to every trade double-counts it.

**(b) The terminal `buy LINK` leg does not exist.** The experiment is valued in USD on
2026-10-15. There is no requirement ever to be back in LINK. We may simply end in USD.

Honest campaign arithmetic for N tactical trades:

```
total legs = 1 (LINK → USD, once) + 2N (alt in/out) + 0 (no forced return)
amortised legs per trade = 2 + 1/N
```

### 1.2 Amortised cost by policy (maker, calm-adverse 0.454%/leg)

| N trades | P1 round-trip-to-core (4 legs) | P2 park-in-USD (2+2/N) | **P2\* end-in-USD (2+1/N)** |
|---|---|---|---|
| 1 | 1.816% | 1.816% | 1.362% |
| 2 | 1.816% | 1.362% | 1.135% |
| 3 | 1.816% | 1.211% | 1.059% |
| 5 | 1.816% | 1.090% | 0.999% |
| 12 | 1.816% | 0.984% | 0.946% |
| ∞ | 1.816% | 0.909% | **0.908%** |

With ~3 weeks left, even a modest arrival rate of R = 2 opportunities/week gives N ≈ 6 and
an amortised cost near **1.0%**, not 1.83%.

### 1.3 The alternatives, evaluated

- **(a) Exit tactical to USD and stay there.** Best of the four. Next entry is 1 leg, not 2.
  Legs per trade → 2 + 1/N.
- **(b) Rotate directly between tactical assets.** **Identical leg count to (a)** — our
  universe is USD-quoted only, so ALT1→ALT2 is still `sell ALT1/USD` + `buy ALT2/USD` = 2
  legs. It would only help if a direct ALT1/ALT2 cross pair existed, and none does in the
  eligible set. Rotation's real (dis)advantage is exposure, not cost: it keeps us
  continuously in a risk asset even when no signal is live.
- **(c) One-way re-allocation, no return.** 2 legs, cheapest, but it is a **change of core
  holding**, not a trade. It should be evaluated as "is ALT a better core than LINK for the
  remaining horizon", which is a different question with a different (much higher) bar.
- **(d) P1, return to core each time.** Only optimal if LINK has a positive expected drift
  large enough to justify paying 2 extra legs to recapture it during the waiting period.

### 1.4 The carry cost of sitting in USD — **measured, and it is not distinguishable from zero**

| Window | LINK daily drift | t | Weekly |
|---|---|---|---|
| Full cache (721d) | +0.128%/d | +0.75 | +0.90% ± 3.16% |
| Last 180d | +0.298%/d | +1.30 | +2.09% ± 4.25% |
| Last 90d | +0.714%/d | +2.00 | +5.00% ± 6.60% |
| Last 30d | +0.613%/d | +0.85 | +4.29% ± 13.41% |

Break-even condition for returning to core after every trade:
`μ_LINK_weekly / R > 2 legs = 0.908%`.

Nothing here is a reliable forecast — the 90d t=2.00 is a single window with a ±6.6%
weekly standard error and does not survive any multiple-testing correction. **Under a
zero-drift prior, parking in USD between tactical trades is EV-neutral and removes 2 of
the 4 legs.** It raises tracking error against the hold-LINK benchmark; it does not cost
expected value. Since the objective is final USD, not benchmark tracking, this is the
right trade.

### 1.5 The rule this implies

Replace one 4-leg charge with a **two-level decision**:

- **L1 (campaign, decided once):** is tactical mode worth 0.454% plus the benchmark
  tracking risk of not holding LINK while waiting?
- **L2 (per trade):** does this opportunity clear 3 × 0.970% = **2.91%**?

---

## 2. HOLD-PERIOD AMORTISATION — **yes, extending the hold makes the gate reachable**

### 2.1 E|move| by holding period — MEASURED, non-overlapping windows

Focus set = the 12 most volatile eligible alts (30d σ 6.35%–12.60%/day): NIL, ARB, VVV,
ZEC, FARTCOIN, NEAR, SPX, ENA, UNI, INJ, BCH, PUMP.

| h (days) | n | E&#124;r_h&#124; | se | median | √t prediction | cost/E&#124;r&#124; @4 legs | cost/E&#124;r&#124; @2 legs |
|---|---|---|---|---|---|---|---|
| 1 | 4368 | 4.52% | 0.08 | 3.13% | 4.52% | 0.40 | 0.20 |
| 2 | 2184 | 6.61% | 0.16 | 4.49% | 6.39% | 0.27 | 0.14 |
| 3 | 1452 | 8.14% | 0.24 | 5.91% | 7.83% | 0.22 | 0.11 |
| 5 | 864 | 10.49% | 0.42 | 7.28% | 10.10% | 0.17 | 0.09 |
| 7 | 624 | 12.65% | 0.60 | 8.76% | 11.96% | 0.14 | 0.07 |
| 14 | 312 | 20.44% | 1.47 | 14.49% | 16.91% | 0.09 | 0.04 |
| 21 | 204 | 24.78% | 1.91 | 18.61% | 20.71% | 0.07 | 0.04 |

Fitted exponent **b = 0.561** (pure √t would be 0.500). |move| grows slightly *faster*
than √t — mild trending, no range-bounding. Cost per unit of realised move falls from 0.40
(4 legs, 1-day hold) to **0.04** (2 legs, 14-day hold), a **10× structural improvement**
from holding period and leg counting alone.

### 2.2 Required holding period to clear the gate

`tactical.py` sets `expected_move = 0.5 × σ_30d_daily` and never scales it by the intended
hold. That silently assumes a 1-day hold. Correcting to `0.5 × σ_1d × √h`:

**Gate A** (`MOVE_TO_COST_MIN = 3×`), required h in days:

| σ_1d | 4 legs | 3 legs | 2 legs |
|---|---|---|---|
| 3.0% | 13.2 | 7.4 | 3.3 |
| 5.0% | 4.8 | 2.7 | 1.2 |
| 7.0% | 2.4 | 1.4 | 0.6 |
| 10.0% | 1.2 | 0.7 | 0.3 |

**Gate B** — the `edge.py` EV test, which is the **binding** one. Gross is discounted by
the coin-flip factor (2p−1); `success_probability` is capped at p = 0.62 → **(2p−1) = 0.24**.

| σ_1d | 4 legs | 2 legs |
|---|---|---|
| 3.0% | 57.3 d | 14.3 d |
| 5.0% | 20.6 d | 5.2 d |
| 7.0% | 10.5 d | 2.6 d |
| 10.0% | 5.2 d | 1.3 d |

**The dominant term is not the leg count — it is the 0.24 coin-flip discount**, a 4.2×
multiplier on the required move. Halving cost halves the required move. Raising p from
0.62 to 0.70 cuts it by 40%. Both changes together cut it by ~70%.

### 2.3 Does the signal decay faster than √t grows?

Conditional on the tactical trigger (vol_ratio ≥ 1.5 AND positive momentum), cross-sectionally
demeaned, date-clustered SE — the methodology that killed R1/R2.

Full-history pairs only (24 pairs, listing bias removed):

| h | n | mean | t_clu | median | win% | 10%-trimmed mean | top-decile share of total |
|---|---|---|---|---|---|---|---|
| 1 | 1247 | +1.151% | 4.27 | +0.005% | 50.2% | +0.334% | 131.9% |
| 3 | 1244 | +2.011% | 4.19 | +0.065% | 51.0% | +0.651% | 120.2% |
| 7 | 1211 | +3.908% | 4.99 | +0.104% | 51.5% | +0.953% | 116.8% |
| 14 | 1204 | +6.058% | 4.92 | +0.254% | 52.0% | +1.686% | 107.0% |

**Do not read this as an edge, and do not cite these means.** The top decile contributes
**more than 100%** of the total (the other 90% is net negative), the median is ~0, and the
win rate is ~51%. That is a right-skewed lottery, not a harvestable signal. It is exactly
the failure mode that got R1 and R2 rejected, and REGISTRY R1/R2 stand.

The **only** safe reading, and the one Q3 needs: **there is no evidence the signal decays
faster than √t grows.** The mean and the trimmed mean both rise monotonically with h. So
extending the holding period is not self-defeating on decay grounds. It also nearly triples
the *trimmed* mean from 1d to 14d (+0.33% → +1.69%), while cost stays fixed — but note that
even +1.69% over 14 days does not clear a 0.97% cost with a 1.5× EV margin.

---

## 3. MAKER FILL MODELLING in volatile conditions

### 3.1 What the bars can and cannot tell us

Posting a buy at the touch means posting `close × (1 − δ)` where δ = half the snapshot
spread. Median eligible half-spread is **2.59 bps** (85th pct 5.52 bps, LINK 2.44 bps).
Per-hour Parkinson volatility is **0.83% calm / 1.31% volatile**.

Bracket from 1h bars, pooled over 32 alts, regime split using the identical definition in
`execution_stats.vol_regime`:

| regime | n bars | P(touch ≤1h) | P(traded *through* ≤1h) | σ_1h | σ_1min |
|---|---|---|---|---|---|
| calm | 19,706 | 90.6% | 88.8% | 0.831% | 10.7 bps |
| volatile | 3,334 | 91.8% | 90.4% | 1.309% | 16.9 bps |

**Volatile/calm per-minute volatility ratio = 1.57× (MEASURED).**

**Negative result, stated plainly:** this bracket is degenerate and therefore uninformative.
A 2.6 bps offset against an 80–130 bps hourly range is reached in >90% of hours in every
regime. Bar data **cannot** resolve maker fill probability for an order at the touch.

### 3.2 Signal-conditional touch — this went against my prior

Trigger defined on 1h bars so it matches an intraday entry decision (bar return ≥ 1.5× the
trailing 720h σ of 1h returns, and positive):

| condition | n | touch ≤1h | touch ≤2h | E[2h move] | **E[2h move &#124; NO fill]** |
|---|---|---|---|---|---|
| unconditional | 16,608 | 91.1% | 93.9% | +0.123% | +1.641% |
| signal fired | 1,172 | **96.2%** | 97.4% | +0.053% | **+2.678%** |

I expected the momentum trigger to *lower* the touch rate. It **raises** it, because the
trigger also selects for high volatility and the half-spread offset is trivially small next
to that volatility. Recording that my prior was wrong.

What this *does* establish is the **miss cost**: in the 3.8% of signal cases where price
never returned to the touch within 1h, the 2h forward move averaged **+2.68%**. Expected
forgone move from insisting on passive entry = 0.038 × 2.68% = **0.10% of notional** —
an order of magnitude below the 40 bps/leg fee saving. **Passive entry remains correct**,
but the misses are concentrated in exactly the trades that would have worked, so realised
win-rate will look worse than the model predicts.

### 3.3 Queue-clearing model — and its falsification

Since price-path is not the constraint, queue position is. Model:

- sell-side flow to the bid = 0.5 × usd_vol_24h / 1440 per minute *(MEASURED volume;
  MODELLED 50/50 split and uniform arrival — real flow is bursty)*
- touch-level queue = depth_bid_usd(±0.5%) × (spread_bps / 50 bps) *(MODELLED uniform
  order density across the band)*
- we join at the **back**; our $8–17 is 0.1–0.5% of a typical queue, so **our size is
  irrelevant** — the whole queue ahead must clear

Median modelled time-to-clear = **7.1 min** (quartiles 3.1 / 7.1 / 13.1). Fastest: XBT,
ZEC, XLM, HYPE, XRP, NIL (<2 min). Slowest: LTC (129 min), PUMP (29), ARB (27), AAVE (24),
ZRO (22), LINK (21).

**Calibration check against the only real data we have — the model fails, in our favour.**
It predicts LINKUSD clears in 20.7 min. The two real post-only LINKUSD fills completed in
**25 s and 30 s** — roughly **45× faster**. So my "books are denser at the touch" assumption
was backwards: the touch queue is far *thinner* than uniform density implies. A real
observation beats an armchair assumption; recording that the model, not the data, is wrong.

Caveats that stop this settling the question:
- n=2, CALM, LINKUSD only, no directional signal — easiest possible case.
- `latency_sec` of exactly 30 and 25 look like **poll boundaries**, not measured fill times.
  True fill was probably faster; it cannot have been slower.
- In a volatile one-directional up-move, sell flow into the bid is *reduced*, and the spread
  widens so a resting order goes stale behind the new touch. Neither effect is in the calm sample.

### 3.4 Working estimate

```
P(maker fill | volatile regime, momentum entry, 15–30 min patience)
      point estimate 0.65     plausible range 0.40 – 0.85     [MODELLED end-to-end]
```

`execution_stats.maker_fill_prob` currently returns 0.50 for volatile with source
`"assumed (insufficient data)"`. 0.65 is the better central value, but the range is wide
enough that 0.50 is a defensible conservative choice. **Do not relabel it "measured".**

### 3.5 Adverse selection in volatile conditions

MEASURED calm: **5.4 bps/leg** at ~25–30 s latency. LINK's half-spread is 2.44 bps — so the
two real fills gave back **2.2× the spread they saved**. Passive execution captured
*negative* spread edge. Maker still wins only because the **fee** saving is 40 bps/leg,
which dwarfs a 5–20 bps adverse term. That is the whole case for posting passively, and it
is robust.

Scaling the measured calm figure by the measured 1.57× per-minute vol ratio
(adverse ∝ σ√latency): **8.5 bps/leg in volatile [MODELLED]**.

Bar-implied 1h-horizon markout conditional on a through-fill is **−16.4 bps in volatile**
(i.e. *favourable* — a dip-buy that bounced) and **+7.8 bps in calm**. I am not using the
volatile figure as a cost credit: it is a 1-hour mark from a bull-market sample, not a
30-second fill latency, and it would only be the right number if our orders rested for a
full hour before filling.

---

## 4. PARTIAL FILLS — depth is a non-issue; **min-notional residuals are the real risk**

### 4.1 Depth-driven partials: not a constraint

A $17 clip against the thinnest eligible book (SPXUSD, $15k bid within ±0.5%) is **0.11%**
of near-touch depth. MEASURED est_slippage across the universe is **0.01–10.4 bps**. A
marketable order of our size fills in full, instantly. Impact is <0.01% and can be dropped
from the cost model entirely.

### 4.2 The real risk: a stranded residual below min notional

If a $C clip fills fraction f, the residual $(1−f)·C must still be tradeable. Below
min_notional it is **stranded** — untradeable on its own.

**7 of 32 eligible alts cannot take an $8.25 clip at all** (min notional exceeds the clip):
**NEAR ($17.51), ZEC ($14.80), UNI ($13.45), NIL ($12.24), ARB ($10.60), HYPE ($9.11), VVV ($8.69)**.

This is severe: NIL, ARB, VVV, ZEC and NEAR are **five of the six most volatile eligible
alts** — precisely the ones that clear the gate in §5. The min-notional constraint knocks
out most of the qualifying universe at a 15% position size.

Stranding thresholds on the rest (fill fraction above which the remainder is untradeable):

| clip | median strand threshold |
|---|---|
| $8.25 (15%) | any partial below ~34% fill strands the remainder |
| $16.50 (30%) | any partial below ~66% fill strands the remainder |

Most liquid-and-cheap pairs are safe: XRP ($2.42), ETH ($2.64), BCH ($3.34), SPX ($3.84),
XBT ($4.17), PUMP ($4.16), XDG ($4.61), ADA ($4.71), SUI ($4.75), HBAR ($4.95), AVAX ($5.00).

**Cost of a stranded residual [MODELLED]:** the residual must exit taker rather than maker,
costing (0.831% − 0.400%) = 0.431% on that slice. At a 20% residual that is **0.086% of
notional** per affected leg. Small, but not zero, and it compounds with the cancel/re-post
cycle.

**Mitigation, and it is large:** size tactical clips at **≥ 2× the pair's min_notional** so
that a 50% partial still leaves a tradeable remainder. At $55 that means min_notional ≤ $8.25
for a 30% clip — which already excludes 7 pairs, and means **the eligible tactical universe
should be filtered on min_notional ≤ notional/2 before anything else is computed.**

---

## 5. BEST ACHIEVABLE COST, and the resulting gate

Per-leg building blocks:

| component | status | value |
|---|---|---|
| maker leg, CALM | 0.400% MEASURED + 5.4 bps MEASURED | **0.454%** |
| maker leg, VOLATILE | 0.400% MEASURED + 8.5 bps MODELLED | **0.485%** |
| taker leg | MEASURED, incl. spread crossing | **0.831%** |
| market impact at $8–17 | MEASURED depth | <0.01%, negligible |

### Policy grid

| policy | cost/round trip | 3× gate | EV gate @ p=0.62 |
|---|---|---|---|
| P1 current model: 4 legs maker, calm adverse | 1.816% | 5.45% | 11.35% |
| P1 honest: 4 legs maker, **volatile** adverse | 1.940% | 5.82% | 12.13% |
| P1b 4 legs: maker entries, taker exits | 2.632% | 7.90% | 16.45% |
| P2 park-in-USD, N=3, all maker | 1.132% | 3.40% | 7.07% |
| P2 park-in-USD, N=5, all maker | 1.067% | 3.20% | 6.67% |
| P2 **marginal** (already in USD), 2 legs maker | **0.970%** | 2.91% | 6.06% |
| P2\* conservative: maker entry + taker exit | 1.316% | 3.95% | 8.23% |
| **P2\*\* realistic: maker entry, 70/30 maker-target / taker-stop exit** | **1.074%** | **3.22%** | **6.71%** |

### The answer

> **Best achievable realistic cost per tactical round trip = 1.07%**
> (maker entry; exit passively at target ~70% of the time, cross on stop ~30%;
> already in USD so only 2 marginal legs; volatile-regime adverse selection).
> Conservative bound if every exit must cross: **1.32%**.
> Floor if every leg fills passively: **0.97%**.
>
> **This is a 41% reduction from 1.83%, and 45% from the honest 1.94%.**

Required expected move at that cost:

| gate | required expected gross move |
|---|---|
| tactical.py 3× move/cost | **3.22%** (was 5.45%) |
| edge.py EV test @ p = 0.62 | **6.71%** (was 11.35%) |
| edge.py EV test @ p = 0.70 | **4.03%** |

### Who actually clears the gate (§F of the script)

Number of *tradeable* pairs (min-notional-blocked excluded) passing each gate:

| gate | 4 legs, 1-day hold | 2 legs, 1-day hold | 2 legs, 3-day hold | 2 legs, 7-day hold |
|---|---|---|---|---|
| A: 3× move/cost | 0 | 8 | 23 | — |
| **B: EV @ p=0.62 (binding)** | **0** | — | **1** | **13** |

Under the current model **zero** pairs clear the binding gate — which is exactly the
observed symptom. Correct leg counting plus a 3-day hold takes it to 1; a 7-day hold takes
it to 13. **Neither change alone is sufficient; together they make the gate non-vacuous.**

This says nothing about whether those trades are *profitable*. It says the gate stops being
an unconditional "no". Whether there is any edge to put through it is Q1/Q2.

---

## 6. Recommendations

Ordered by value. Items 1–4 are code changes; item 5 is the highest-value experiment.

**1. `tactical.py` — stop charging 4 legs. [largest single effect: −45% cost]**
Replace `edge.costs(..., sides=4, ...)` and `edge.evaluate(..., sides=4, ...)` with
`sides=2`, and add a separate one-time `CAMPAIGN_ENTRY_COST = 0.00485` charged once when
transitioning LINK→USD, not per trade. Make the campaign decision explicit and logged.
Justification: §1. The LINK re-entry leg is never required — the experiment is valued in USD.

**2. `tactical.py` — scale `expected_move` by the intended holding period.**
`expected_move()` currently returns `0.5 × σ_30d_daily × uplift`, which implicitly assumes a
1-day hold while `exit_thesis` contemplates a trailing multi-day hold. Add a `hold_days`
parameter and return `0.5 × σ × sqrt(hold_days) × uplift`, defaulting to **3**, and make
`hold_days` an explicit, logged field of the trade plan. Justification: §2. The measured
scaling exponent is b = 0.561, so √t is if anything conservative.

**3. `tactical.py` — filter the universe on min_notional before anything else.**
Add `MIN_NOTIONAL_RATIO = 2.0` and drop any candidate with
`min_notional > portfolio_usd × size_frac / 2`. At $55 and a 15% clip that removes NEAR,
ZEC, UNI, NIL, ARB, HYPE, VVV — five of which are in the top six by volatility and would
otherwise show as qualifying trades we cannot actually size. Justification: §4.2. Without
this, the scanner will eventually emit a "QUALIFIES" on a pair whose entry cannot be placed
or whose partial fill strands an untradeable residual.

**4. `edge.py` — separate the fill-probability discount from the absolute floor.**
`evaluate()` computes `net = gross*fill_p − total*fill_p` and then tests
`net >= MIN_ABS_EDGE_PCT` (0.5%). Scaling both sides by `fill_p` is correct for the *sign*
of EV-per-attempt, but it makes `net_pct` an expected-value-per-attempt number that is no
longer comparable to an absolute per-completed-trade floor — so a high-quality trade with a
0.40 fill probability is rejected by a floor it would clear if it filled. Gate on
`net_per_completed_trade = gross − total` against `MIN_ABS_EDGE_PCT`, and use `fill_p` only
(a) in the sign test and (b) to rank opportunities by throughput. Also update the `TAKER`
constant: it is `0.0080` in code but REGISTRY A1 records the measured all-in taker leg as
**0.831%**; the extra 0.031% is being added separately as spread, which is close but is
double-bookkeeping the same measurement.

**5. Measure the thing we are guessing at. [highest value overall, costs ~$0]**
Every volatile-regime number in this document is modelled from n=0 fills. Place **5–10 small
post-only orders (~$7–8, at or just inside the touch)** on eligible alts while
`execution_stats.vol_regime()` returns `volatile`, record fill/no-fill, true latency and
adverse selection, and replace the 0.65 estimate with a measured one. Post-only orders that
do not fill cost nothing. This collapses the single largest uncertainty in the tactical EV
calculation, and it also fixes the `latency_sec` instrumentation, which currently reports
poll boundaries (25 s, 30 s) rather than fill times.

**Do not** raise `success_probability` above 0.62 on the strength of anything in this
document. §2.3 shows why: the apparent conditional means are a right-skewed lottery whose
top decile carries more than 100% of the total. That is the R1/R2 failure mode and it stays
rejected.

---

## 7. What would prove this analysis wrong

- **Leg counting (§1):** if LINK's forward drift over the remaining horizon turns out to be
  large and forecastable, P1 (return to core) becomes correct and the 4-leg model is
  vindicated. The measured drift t-statistics (0.75–2.00) do not support that today.
- **Fill probability (§3):** ≥5 real post-only orders in volatile conditions with a fill
  rate below 0.40 would invalidate the 0.65 estimate and push the realistic cost toward the
  taker-exit bound of 1.32% — or make passive entry unusable for tactical mode entirely.
- **Adverse selection (§3.5):** if measured volatile adverse selection exceeds ~40 bps/leg,
  the fee advantage of posting passively disappears and maker vs taker becomes a coin flip.
  The 1.57× vol-scaling says 8.5 bps; it would have to be wrong by ~5× for this to bite.
- **Hold-period extension (§2):** if realised multi-day trades show materially worse
  slippage/gap risk than the bar-derived E|move| implies, or if the wider stop that a 3–7
  day hold requires makes the per-trade loss exceed the per-trade gain, the amortisation
  argument fails even though the arithmetic holds.
- **Partial fills (§4):** an observed partial fill leaving a residual below min notional, on
  a pair that passed the `MIN_NOTIONAL_RATIO = 2.0` filter, would show the filter is too loose.

---

## 8. Interaction with R6 — does cheaper execution revive confluence trading? **No.**

R6 (rejected 2026-09-24, `Q1_signal_combinations.md`) explicitly leaves one door open:
*"Reconsideration requires … a cost structure low enough to change the arithmetic."*
Q3 is that lever, so it must be answered directly rather than left for someone to infer.

Q3 cuts the modelled round-trip cost from 1.83% to **1.07%**, a saving of **0.76 pp**.
R6's best combination, with the single NILUSD 2026-09-20 asset-day removed, was
**+1.72% gross / −0.11% net**. Applying the 0.76 pp saving moves that to roughly
**+0.65% net**, i.e. the sign flips.

**That is not a revival, and it must not be cited as one.** The number whose sign flips has:

- family-wise permutation p = **0.971** — random asset selection typically produces a
  better-looking best result;
- largest |t| anywhere of 2.40 against a Bonferroni threshold of 3.461;
- negative medians on all top-3 combinations;
- its entire magnitude sitting out-of-sample at |t| ≈ 1.0–1.2.

A cost reduction changes the arithmetic of a quantity that is statistically indistinguishable
from noise. It converts "reliably negative noise" into "noise". **R6 stays rejected.**

The correct summary of Q3 is narrower and should be stated as such:

> The execution-cost constraint was real, was **overstated by roughly 45%**, and can be
> structurally reduced to ~1.07% per round trip. That removes execution cost as the
> *binding* constraint on tactical mode. It does not supply an edge, and Q1/R6 found none.
> After Q3, the reason not to trade tactically is **no demonstrated signal**, not **cost** —
> which is a more honest place to be, and a different research problem.
