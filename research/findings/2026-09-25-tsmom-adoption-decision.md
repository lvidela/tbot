# Adoption decision — weekly time-series momentum (TSMOM)

**Decider:** live agent (`/home/lisandro`), session `s-2026-09-25T1427Z-08`
**Source research:** `research/tsmom/` (tsmom.py, tsmom_log.py, tsmom_pooled.py, tsmom_verdict.py)
**Decision: REJECTED for live use. Position unchanged: 100% LINK.**

---

## What was proposed

Hold LINK or USD, decided weekly at the bar close by a trend rule (sign of trailing L-week
return, or close vs N-week SMA; 9 rules). 366 weekly bars, 20 assets — by a wide margin the
longest history this project has used. Prior studies were cross-sectional (market factor
removed by demeaning) or intraday, so market timing had genuinely never been tested.

## Independent validation performed

I re-ran `tsmom_pooled.py` and `tsmom_verdict.py` myself rather than accepting reported
numbers. **`tsmom_verdict.py` had died before writing any output** (process gone, output file
0 bytes) — the V1–V4 results below are from my own run, not the research agent's.

Code audit before running, all clean:
- **No look-ahead.** `signal(c, i)` uses bars `<= i`; the return applied is `c[i+1]/c[i] - 1`.
- **Incomplete current weekly bar dropped.**
- **Benchmark-relative throughout** (the D8 lesson) — excess is vs holding the same asset.
- **Costs charged** at 0.45%/switch maker (0.40% fee + measured 5.4 bps adverse selection),
  one leg per switch. Verified the closed-form log and arithmetic excess formulas by hand
  against the multiplicative definition; both correct.
- Survivorship is acknowledged and argued to bias *against* timing. I agree — dead coins went
  to ~0 and a trend rule would have exited them.

This is careful work. The rejection is not a criticism of the method.

## Why it was rejected

### 1. On the stated objective — expected final USD — every rule loses to holding

The mission maximizes *expected* final USD. That is the arithmetic statistic. V2:

| | mom4 | mom8 | sma20 | best of 9 |
|---|---|---|---|---|
| pooled arithmetic excess vs hold, all | **−1.010%/wk** (t=−1.36) | −0.881 (t=−1.23) | −1.015 (t=−1.36) | all negative |
| common-shift permutation, arithmetic obs | **−0.199** | −0.286 | −0.306 | all negative |

Every rule, every era-aggregate, negative. The rules beat *random* timing on this metric, but
random timing at 50% exposure is catastrophic, so that is not a profitability test (see §3).

### 2. In log/median terms, nothing survives correction for searching 9 rules

V1 max-statistic common-shift permutation, 2,000 draws, each rule standardised by its own null:

| rule | p_rule | **p_FWER** |
|---|---|---|
| mom2 | 0.006 | **0.055** |
| mom4 | 0.014 | **0.055** |
| sma10 | 0.022 | 0.070 |
| mom8 | 0.028 | 0.078 |

Best family-wise p is **0.055** — nothing clears 0.05. The single-rule p=0.009 that motivated
the handoff is a 1-of-9 selection; corrected, it is marginal.

### 3. The de-risking control is decisive: most of the effect is not timing

V4 — static exposure equal to each rule's own average exposure, weekly rebalanced, rebalancing
cost charged (i.e. *no timing skill whatsoever*):

| rule | exposure | timing | **static** | timing − static |
|---|---|---|---|---|
| mom4 | 0.46 | +1.100 | **+0.645** | +0.455 (14/20 assets) |
| mom8 | 0.45 | +0.781 | **+0.674** | +0.107 (14/20) |
| sma20 | 0.41 | +0.842 | **+0.669** | +0.173 (10/20) |
| mom13 | 0.44 | +0.374 | +0.685 | **−0.310** (8/20) |
| mom26 | 0.46 | −0.008 | +0.740 | **−0.748** (4/20) |

**Simply holding ~45% of the asset and the rest in USD, with zero timing, captures +0.61 to
+0.74 of a ~+1.10 total.** Four of nine rules do *worse* than that static control. What looked
like a trend edge is mostly an exposure-reduction effect, and exposure reduction is a variance
preference, not an edge — it raises the median and lowers the mean, which is why §1 is negative.

### 4. Attribution: the effect is one or two bear markets, not 636 weeks

V3, per-year pooled log excess for mom4:
`2021:+0.33 2022:+0.77 2023:−0.13 2024:+0.07 2025:+0.51 2026:+0.03`
and negative in 2015, 2016, 2017, 2019, 2020.

**2022 and 2025 carry it.** The pre-2021 / 2021+ split shows the same thing from the other
side: every rule is negative pre-2021 and positive after. A rule that cuts exposure wins when
the market falls and loses when it rises — 20 correlated crypto assets sharing the 2022 bear
is closer to **one or two effective observations** than to 636 weeks. This is registry R1's
correlated-observations error reappearing at regime scale.

### 5. A weak-bar warning worth keeping

The circular-shift permutation asks "does this rule time better than random timing at the same
exposure?" That null is *strongly negative* — random timing throws away half the drift. So the
bar is low, and passing it does not imply profitability. **Proof by counterexample from the
data: `mom1` passes at p_rule = 0.017 while ending at W = 0.44 against hold's 2.63 — it
destroys 83% of terminal wealth relative to holding and still "beats random".** Any future use
of this permutation must be paired with the vs-hold and vs-static-exposure comparisons.

## What would reverse this decision

1. A rule with **p_FWER < 0.05 on the arithmetic statistic** (currently all negative).
2. `timing − static` positive and material **across rules**, not only for the best-of-9.
3. Positive attribution in years that are not bear markets — 2023 and 2024 are the clean test
   and both are ~0 for mom4.

## Operational note

At the time of this decision **all 9 rules signalled IN LINK** (last complete weekly bar
2026-09-17, close 12.35149). Adoption would not have changed the current position, so nothing
was forgone by rejecting it. The live decision is HOLD under every reading of this study.
