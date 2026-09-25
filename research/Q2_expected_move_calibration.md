# Q2 — Is the production expected-move model calibrated?

**Date:** 2026-09-24
**Script:** `/home/lisandro/backtests/expected_move_calibration.py`
**Data:** local cache only (`/home/lisandro/data/cache`, built 2026-09-24T23:27Z). No API calls, no orders.
**Cost assumption:** A1 — **1.83% round trip** (4 legs, maker, incl. spread + adverse selection).

## What was audited

```
expected_move_pct   = 0.5 * daily_sigma * (1 + 0.15 * max(0, confluence - 3))
success_probability = min(0.50 + 0.03 * confluence, 0.62)
```

Confluence conditions were reconstructed **exactly** as `tactical.analyse()` defines them
(`VOL_EXPANSION_MIN 1.5`, `VOLUME_MIN 3.0`, `MOMENTUM_MIN 0.02`, `REL_STRENGTH_MIN 0.03`,
`pos_in_range >= 0.95 & rng/bid >= 0.03 & mom_4h > 0`, spread ≤ 25 bps as a veto),
evaluated at each daily bar close (00:00 UTC), which is the decision instant. Every input
uses only bars that had closed at that instant — **no look-ahead**. The last daily bar in
the cache (the in-progress day) was dropped.

Methodology required by the registry (the R1/R2 fixes) was applied throughout:
cross-sectional demeaning against the same-day equal-weight universe mean, **date-clustered**
robust standard errors, plus a **moving-block bootstrap** over dates (block = 4) to handle the
fact that 3-day forward windows on consecutive dates overlap.

---

## 0. THE HEADLINE CONSTRAINT: the sample cannot support fine calibration

The 4h cache spans only **2026-05-27 → 2026-09-24**. Three of the five confluence conditions
(`momentum_continuation`, `breakout_confirmed` via `mom_4h`, `relative_strength`) depend on 4h
bars, so the production signal can only be reconstructed over ~115 days.

| Primary (exact production definition) | value |
|---|---|
| universe | 32 non-stable USD pairs (EUR/GBP/PAXG excluded) |
| observations | 3,712 pair-days over **116 days** |
| setups, confluence ≥ 3, spread OK | **n_events = 168**, **n_days = 62** |
| date range | 2026-05-28 → 2026-09-20 |
| mean σ of setups | 4.82%/day |
| mean predicted move | 2.67% |

Firing is violently clustered: setups fired on 62 of 116 days; the single largest day carried
**26 of the 168 events (15%)**, the next two 15 each. Four days account for ~37% of the sample.
This is precisely the pseudo-replication that killed R1 and R2, and it is why every number
below is clustered by date.

**Every predicted-move bucket in the primary sample has fewer than 30 clustered observations
and is marked LOW CONFIDENCE.** Confluence 4 (27 days) and confluence 5 (14 days) are also
LOW CONFIDENCE. Only confluence 3 (46 days) clears the bar.

Also note: **the spread veto never binds in this cache** — all 32 pairs show ≤ 25 bps in
`meta.json`. `spread_bps` there is a single live snapshot, not a history, so the veto's real
effect is untested here.

A **PROXY** study over the full 721-day daily history is also reported. It replaces `mom_4h`
with the day-D return and `mom_12h` with the 3-day return. It is **not the production signal**
and its absolute numbers must not be quoted as production calibration; it is used only to see
whether the *shape* of the primary result survives 449 days instead of 62.

---

## 1. Predicted vs realized (primary sample, n=168 / 62 days)

| horizon | pred | realized raw | t_cl | realized demeaned | t_cl | median raw | net raw | net demeaned |
|---|---|---|---|---|---|---|---|---|
| 1d | 2.67% | +2.48% | +1.70 | **+0.59%** | +1.05 | +0.71% | +0.65% | −1.24% |
| 2d | 2.67% | +4.31% | +2.03 | **+0.34%** | +0.58 | +1.14% | +2.48% | −1.49% |
| 3d | 2.67% | +5.04% | +2.03 | **+0.68%** | +0.78 | +1.81% | +3.21% | −1.15% |

The raw +5.04% looks like a large beat of the 2.67% prediction. **It is almost entirely market
beta.** The universe mean 3d forward return was **+2.08% on event days** versus **+0.50% on
non-event days** (all days +1.34%) — confluence setups preferentially fire on days the whole
market is about to rip. After demeaning, the selection edge is **+0.68%, t = 0.78**, i.e.
indistinguishable from zero, and *below* the 1.83% round-trip cost.

Proxy sample (449 days): raw +2.07% (t=+3.42), demeaned **+1.14% (t=+4.16)**, but median −0.29%
and **net demeaned −0.69% (t=−2.53)**. So over the long history there is a small, statistically
detectable demeaned drift, and it is smaller than the cost.

---

## 2. Calibration table (primary; realized = 3d close-to-close, gross)

| predicted bucket | n | n_days | mean pred | mean realized | P(>pred) | P(>3%) | P(>1%) | P(<0) | P(MFE>pred) |
|---|---|---|---|---|---|---|---|---|---|
| 0–2% | 54 | 25 | 1.51% | +3.81% | 50.0% | 46.3% | 53.7% | 42.6% | 83.3% |
| 2–3% | 56 | 28 | 2.43% | +4.55% | 44.6% | 44.6% | 51.8% | 48.2% | 91.1% |
| 3–4% | 33 | 23 | 3.44% | +3.59% | 36.4% | 39.4% | 42.4% | 54.5% | 90.9% |
| 4–6% | 23 | 19 | 4.54% | +11.84% | 56.5% | 60.9% | 65.2% | 34.8% | 95.7% |
| 6%+ | 2 | 2 | 6.20% | −2.37% | 0.0% | 0.0% | 50.0% | 50.0% | 100.0% |

**All buckets: LOW CONFIDENCE (<30 clustered observations).**

Demeaned version (market removed) — the honest read:

| predicted bucket | n | n_days | mean pred | mean demeaned | P(>pred) | P(>3%) | P(>1%) | P(<0) |
|---|---|---|---|---|---|---|---|---|
| 0–2% | 54 | 25 | 1.51% | **−1.68%** | 29.6% | 25.9% | 31.5% | 63.0% |
| 2–3% | 56 | 28 | 2.43% | +1.15% | 28.6% | 26.8% | 33.9% | 55.4% |
| 3–4% | 33 | 23 | 3.44% | **−0.20%** | 30.3% | 30.3% | 30.3% | 63.6% |
| 4–6% | 23 | 19 | 4.54% | +7.24% | 52.2% | 52.2% | 52.2% | 43.5% |
| 6%+ | 2 | 2 | 6.20% | −10.04% | 0.0% | 0.0% | 0.0% | 100.0% |

There is **no monotone relationship between the predicted move and the realized demeaned move**.
Buckets alternate sign. The proxy sample (n=1,464 / 449 days) confirms the non-monotonicity:
demeaned means run +0.85%, +0.56%, +0.95%, +1.47%, +6.49% while P(>pred) *falls* from 38.5% to
27.3% as the prediction rises. **The model's predicted move does not rank outcomes.**

Only **~30% of setups achieve their own predicted move** on a demeaned basis, and **55–63% are
negative**, versus an unconditional base rate of 57% negative (demeaned). That is a coin flip.

---

## 3. Fitted σ multiplier

Regression through the origin, `target = k · σ`, cluster-robust by date, with a block-bootstrap
CI as a second opinion.

**Primary sample (n=168, 62 days):**

| target | k̂ | SE | 95% CI (clustered) | 95% CI (block bootstrap) |
|---|---|---|---|---|
| 3d return, raw | **+0.925** | 0.420 | [+0.102, +1.749] | [−0.186, +1.852] |
| 3d return, **demeaned** | **+0.228** | 0.216 | [−0.195, +0.652] | [−0.216, +0.586] |
| 3d \|return\| | +2.122 | 0.331 | [+1.474, +2.770] | [+1.415, +2.711] |
| 3d MFE | **+3.132** | 0.462 | [+2.227, +4.037] | [+1.992, +4.084] |
| 3d \|MAE\| | +1.377 | 0.145 | [+1.093, +1.662] | [+1.066, +1.688] |
| 1d return, raw | +0.393 | 0.229 | [−0.056, +0.842] | [−0.053, +0.832] |
| 1d MFE | +1.723 | 0.204 | [+1.322, +2.123] | [+1.255, +2.157] |

**Proxy sample (n=1,464, 449 days):** 3d raw **+0.344** [+0.154, +0.535]; 3d demeaned **+0.218**
[+0.096, +0.340]; 3d MFE **+2.023** [+1.839, +2.208]; 3d \|MAE\| +1.275 [+1.168, +1.381].

The answer depends entirely on what `expected_move` is meant to represent:

* **As the expected close-to-close move you will actually capture (what the EV gate needs):**
  the demeaned fit is **k ≈ 0.22–0.23**, and the two independent samples agree to within 0.01.
  The current **0.50 is roughly 2× too generous**, though the primary CI [−0.20, +0.65] does
  contain 0.50 and even contains zero. The proxy CI [+0.10, +0.34] **excludes 0.50**.
* **As the best price reachable inside the window (MFE):** **k ≈ 2.0–3.1**, so 0.50 is ~5× too
  low. But MFE is a look-ahead-optimal statistic you cannot systematically capture, and it is
  bracketed by \|MAE\| ≈ 1.3σ over the same window — a wide, symmetric-ish flail, not an edge.

**The confluence uplift.** k by confluence (MFE target): primary 2.65 / 2.72 / 4.91 for
confluence 3/4/5; proxy 1.75 / 2.32 / 2.44. Directionally the uplift is real for MFE and the
model's 1.00/1.15/1.30 is if anything understated. But on **demeaned returns** there is no
pattern (primary: +0.13 / −0.33 / +1.39; proxy: +0.16 / +0.31 / +0.26), and confluence 4 and 5
are LOW CONFIDENCE. The uplift term is not supported for the quantity that matters.

---

## 4. Success-probability anchor

Primary sample, 3d horizon:

| confluence | n | n_days | model p | P(raw>0) | 95% CI (clustered) | P(demeaned>0) | P(raw>cost) | flag |
|---|---|---|---|---|---|---|---|---|
| 3 | 83 | 46 | 0.590 | **0.494** | [0.349, 0.639] | 0.434 | 0.434 | |
| 4 | 59 | 27 | 0.620 | 0.559 | [0.379, 0.740] | 0.339 | 0.525 | LOW CONFIDENCE |
| 5 | 26 | 14 | 0.620 | 0.654 | [0.418, 0.889] | 0.538 | 0.654 | LOW CONFIDENCE |
| all | 168 | 62 | — | 0.542 | [0.396, 0.688] | 0.417 | — | |

Unconditional baseline (every pair, every day, n=3,712 / 116 days): **P(raw>0) = 0.501**,
P(demeaned>0) = 0.429.

Proxy sample (449 days), where there is real power:

| confluence | n | n_days | model p | P(raw>0) | 95% CI | P(demeaned>0) |
|---|---|---|---|---|---|---|
| 3 | 860 | 370 | 0.590 | 0.486 | [0.434, 0.538] | 0.465 |
| 4 | 377 | 208 | 0.620 | 0.488 | [0.423, 0.553] | 0.456 |
| 5 | 227 | 141 | 0.620 | 0.507 | [0.427, 0.586] | 0.445 |

Baseline over 674 days: P(raw>0) = 0.476, P(demeaned>0) = 0.431.

**Verdict on `0.50 + 0.03 · confluence`:** the *intercept* 0.50 is right — it is the coin flip,
and confluence ≥ 3 delivers 0.49–0.54 in the primary sample and 0.49 in the proxy. The
*slope* 0.03 per confluence level is **not supported**: the proxy sample, with 370/208/141
clustered days per bucket, shows a flat 0.486 / 0.488 / 0.507 — no gradient at all. The primary
sample's apparent gradient (0.494 → 0.559 → 0.654) rests on 27 and 14 clustered days with CIs
spanning [0.38, 0.74] and [0.42, 0.89]; it is noise. Demeaned, the gradient disappears or
inverts in both samples.

So the formula's *point values* (0.59–0.62) are **too generous by ~7–13 points** relative to the
measured 0.49–0.54, but the primary-sample CIs are wide enough that 0.59 is not statistically
excluded for confluence 3. The proxy sample does exclude it.

---

## 5. MFE / MAE profile (primary, entry at decision close, daily high/low)

| horizon | mean MFE | median MFE | mean MAE | median MAE | MFE/MAE | MFE/pred | P(MFE>pred) |
|---|---|---|---|---|---|---|---|
| 1d | +9.18% | +7.83% | −5.01% | −3.72% | 1.83 | 3.44 | 82.1% |
| 2d | +13.69% | +10.75% | −6.23% | −5.42% | 2.20 | 5.13 | 85.7% |
| 3d | **+16.57%** | +11.47% | **−7.10%** | −6.51% | 2.33 | 6.21 | 89.3% |

Proxy (449 days): 3d MFE +12.36% / MAE −7.83%, ratio 1.58, P(MFE>pred) 80.3%.

**Time-to-peak** (4h resolution over the 3d window): median **28h**, mean 31h, and only **47.6%**
of setups peak inside the first 24h. The favourable excursion is spread across the whole window,
so a 1-day hold systematically leaves the excursion on the table while a 3-day hold sits through
a −7.1% mean adverse excursion.

The critical reading: the predicted move (2.67%) is trivially reachable — MFE exceeds it 89% of
the time — but the adverse excursion is **2.7× the predicted move** over the same window. The
model predicts a target that is easy to touch and ignores that the path to it routinely goes
through a drawdown far larger than the target.

---

## 6. What happens if you actually trade the model's own plan

`tactical.evaluate()` publishes an exit thesis: target = predicted move, invalidation = close
below entry − 1σ. Simulating exactly that on **4h bars** (finer than daily, so the ordering of
target vs stop is far more realistic):

| tie rule | target-before-stop | stop | timeout | mean net P&L | t_cl | median | P(profit) |
|---|---|---|---|---|---|---|---|
| pessimistic | 136 (**81.0%**) | 31 | 1 | **−0.59%** | −1.77 | +0.35% | 58.3% |
| optimistic | 137 (81.5%) | 30 | 1 | −0.54% | −1.64 | +0.37% | 58.9% |

(The same simulation on daily bars gives −2.44%, t=−3.64, but that is an artefact of forcing
the stop whenever both levels are touched inside one daily bar. The 4h figures are the fair ones.)

**This is the single most important result in the study.** The realized probability of hitting
the target before the stop is **81%** — *far above* the model's 0.59–0.62, i.e. the success
probability is badly **too conservative** when read as "P(target before stop)". And the strategy
still loses money, because the geometry is 1:2 against:

```
mean sigma = 4.82%
EV = 0.81 × (0.5σ) − 0.19 × (1.0σ) = +1.04% gross → −0.79% net of 1.83%
breakeven p for target 0.50σ / stop 1.00σ, after cost = 0.920
breakeven p for target 0.75σ / stop 1.50σ, after cost = 0.835
```

You need **92% accuracy** to break even on the model's own exit plan. You get 81%.

### Target/stop geometry sweep (primary, 4h path, net of 1.83%)

| target ×σ | stop ×σ | P(target) | mean net | t_cl | median | P(profit) |
|---|---|---|---|---|---|---|
| 0.50 | 1.00 | 82.1% | −0.69% | −2.46 | +0.20% | 56.0% |
| 0.75 | 1.00 | 76.8% | −0.19% | −0.48 | +0.99% | 72.0% |
| 0.75 | 1.50 | 82.7% | **+0.17%** | +0.51 | +1.29% | 77.4% |
| 1.00 | 1.50 | 72.6% | +0.12% | +0.24 | +1.76% | 72.6% |
| 1.50 | 1.50 | 58.9% | +0.05% | +0.06 | +2.23% | 60.7% |
| 2.00 | 1.50 | 52.4% | +0.31% | +0.31 | +2.22% | 54.2% |
| 3.00 | 1.50 | 35.1% | +0.16% | +0.10 | −3.67% | 45.2% |

18 cells were searched on 62 clustered days. The best cell is **+0.31% with t = 0.31**. Nothing
in this grid is significant; the positive cells are what a noise field looks like after a grid
search (the same pathology as R3). In the proxy sample **all 18 cells are negative**, from
−2.77% to −0.57%. The only consistent signal in the sweep is that tighter stops are strictly
worse — the setups get whipsawed — which is a statement about volatility, not about edge.

### The gate almost never fires anyway

`MOVE_TO_COST_MIN = 3.0` against a 1.83% round trip requires a predicted move ≥ **5.49%**, i.e.
σ ≥ 11%/day at confluence 3. Of the 168 setups in four months, **2 (1.2%)** cleared it, on 2
distinct days. Their realized 3d return was −2.37% mean (n=2 — uninformative).

---

## 7. Answers

**Is the model calibrated?** It is miscalibrated in **both directions at once**, which is why
it fails:

1. **`0.5 · σ` as an expected captured move is too generous (~2× too high).** Empirical
   demeaned k = **0.23** (primary, CI [−0.20, +0.65]) and **0.218** (proxy, CI [+0.10, +0.34]).
   Read as a *reachable* level rather than a captured return, 0.5σ is instead far too low
   (MFE k ≈ 2.0–3.1) — but that reading is not decision-useful.
2. **`0.50 + 0.03·confluence` is too conservative as P(target before stop) — the realized value
   is 81%, not 62%** — and simultaneously too generous as P(positive forward return), where the
   realized value is 0.49–0.54 against a 0.50 coin-flip baseline.
3. **The confluence slope is not supported at all.** Flat 0.486/0.488/0.507 across confluence
   3/4/5 over 449 clustered days.
4. **The real defect is neither number.** It is the **1:2 target/stop geometry** in the exit
   thesis, which requires 92% accuracy to break even against the 1.83% cost. No σ multiplier
   fixes that.

**Is the sample big enough to recalibrate?** For the production signal definition, **no.**
n_days = 62, every predicted-move bucket under 30 clustered days, confluence 4 and 5 at 27 and
14 days, a single day carrying 15% of the events, and a fitted k whose 95% CI spans
[−0.20, +0.65] — a range in which the current 0.50 sits comfortably. **The honest answer to
"what multiplier is empirically correct" is that the primary sample cannot distinguish 0.22
from 0.50 from 0.65.** The proxy sample points at ~0.22 with a tight CI but uses a different
momentum definition and cannot be substituted for the production signal.

---

## 8. Recommendation

**Do not retune the two constants. They are not the binding problem, and the sample cannot
support a retune of the production definition.** Specifically:

* **Do NOT raise the σ multiplier**, and do not let the k ≈ 3 MFE fit or the 81% target-hit rate
  be read as "the model is too conservative, be more aggressive". The setups with the largest
  MFE also carry \|MAE\| ≈ 1.4σ, and the full-path simulation of the model's own plan loses
  −0.59% per trade net.
* **Do NOT lower it to 0.22 either**, tempting as the two-sample agreement is. 0.22σ ≈ 1.06% on
  the mean setup, which is below the 1.83% round trip — adopting it would be equivalent to
  switching the tactical mode off, and it would be doing so on a 62-day primary sample.
* **DO drop the confluence uplift `(1 + 0.15·(confluence−3))` and flatten
  `success_probability` to 0.50.** These are the two components with clear, powered evidence
  against them: 449 clustered days show a flat 0.486/0.488/0.507 success rate and no monotone
  relationship between confluence and demeaned outcome. Both changes make the gate *stricter*,
  which is the direction the evidence supports. With p = 0.50 the EV gate can essentially never
  pass, which is the correct behaviour given everything measured here.
* **DO record that the published exit thesis is EV-negative as written.** If tactical mode is
  ever enabled, a 0.5σ target against a 1.0σ stop needs 92% accuracy at current costs. The
  geometry must be at least 1:1 before any target/stop plan is viable, and even then the
  sweep's best cell is t = 0.31 on 18 searched cells.
* **Q3 (execution cost) dominates Q2.** At 1.83% round trip nothing in this study is tradeable;
  at a hypothetical 0.6% round trip several sweep cells would be clearly positive. The binding
  constraint is cost, not the expected-move formula.

**What would change this conclusion:** ~6+ more months of 4h history (target ≥ 150 clustered
days, ≥ 30 per confluence bucket) showing (a) a demeaned k stable and above cost/σ, and
(b) a monotone confluence gradient in demeaned outcomes, not just in MFE. Until then the
correct statement is: **the production expected-move model cannot be calibrated on the
available sample, and the only defensible edits are the ones that remove unsupported
optimism (the uplift and the probability slope).**

## Registry impact (proposed)

* New REJECTED entry: **the `0.15` confluence uplift and the `0.03` per-level probability slope**
  — flat 0.486/0.488/0.507 over 449 clustered days, no monotone demeaned relationship.
* New ACCEPTED entry: **the tactical exit geometry (0.5σ target / 1.0σ stop) is EV-negative**:
  realized P(target before stop) 81% vs 92% breakeven; measured −0.59%/trade net, t = −1.77.
* Note against Q2: the primary sample is **62 clustered days**; no fine calibration of `0.5σ`
  is possible, CI [−0.20, +0.65].
