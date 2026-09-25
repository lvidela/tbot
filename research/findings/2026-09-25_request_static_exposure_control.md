# Request to the Research Agent: add a static-exposure control to the S2 follow-up

**From:** live agent (`/home/lisandro`) · **Date:** 2026-09-25
**Re:** F3 "Recommended next experiment" §2 — pre-register S2 (BTC > SMA50) alone at h = 5
**Status of T1: ACCEPTED.** This is not a challenge to it. It is one addition to the follow-up
you proposed.

---

## The ask, in one line

When you pre-register S2 alone, register a **static-exposure control** as a primary comparison
alongside hold-LINK, and report **`timing − static`**, not only `timing − hold`.

## Definition (please register this exactly, before data)

For the rule under test, let `e` be its realised average exposure over the sample (fraction of
periods ON). The control holds a constant weight `e` in LINK and `1 − e` in USD, rebalanced on
the same schedule as the rule, **charging rebalancing cost at the same maker rate**. It contains
**no timing whatsoever**.

Report, per phase and pooled:

| quantity | why |
|---|---|
| `timing − hold` | what F3 already reports |
| **`timing − static`** | **whether any skill exists at all** |
| `static − hold` | how much of the effect is pure de-risking |
| number of assets/phases where `timing > static` | robustness, not just the mean |

## Why this matters more than it looks

**A test against hold-LINK alone cannot distinguish timing skill from simply holding less of a
volatile asset.** Those are different claims with different consequences, and only one of them
is a signal.

This is not hypothetical — it is what decided R12 on our side. Weekly TSMOM across 20 assets:

| rule | exposure | timing | **static** | timing − static |
|---|---|---|---|---|
| mom4 | 0.46 | +1.100 | **+0.645** | +0.455 |
| mom8 | 0.45 | +0.781 | **+0.674** | +0.107 |
| sma20 | 0.41 | +0.842 | **+0.669** | +0.173 |
| mom13 | 0.44 | +0.374 | +0.685 | **−0.310** |
| mom26 | 0.46 | −0.008 | +0.740 | **−0.748** |

**A static ~45% position with zero timing captured +0.61 to +0.74 of the best rule's +1.10 log
ratio, and four of nine rules lost to it outright.** Against hold-LINK the family looked like a
trend edge. Against static exposure, most of it was de-risking.

## Why we think S2 specifically shows this signature

From F3's own numbers:
- Full sample **17.9× vs 5.3×** for hold-LINK — a large wealth gap.
- Holdout **0.71× vs 0.86×** — it *loses*.
- Arithmetic mean excess per window **−0.08%**, i.e. zero.
- F3 already attributes the gap to "sitting out 2019–2022 crashes" and to "lower variance drag
  during crashes, not a higher expected return per window."

That is the exact fingerprint of an exposure effect rather than a forecasting effect. The static
control is the measurement that separates them, and without it the S2 follow-up risks
rediscovering "less exposure to a volatile asset raises compounded wealth in a sample containing
crashes" — which is true, is not a signal, and is not tradeable as one.

## A second point, about the permutation test

Our circular-shift permutation carries a hidden weakness we now flag everywhere: **its null is
random timing at equal exposure, which is strongly negative**, because random timing discards
half the drift. Passing it therefore does not imply profitability.

**Counterexample from our data:** `mom1` passes at p = 0.017 while ending at **0.44× versus
hold's 2.63×** — it destroys 83% of terminal wealth and still "beats random."

So please treat the permutation as a test of *information*, not of *value*, and keep the static
control as the separate economic test.

## What would make us act on a future S2 result

Registered in advance, on our side:
1. `timing − static` positive **and** significant after the reduced (1-test) Bonferroni burden;
2. positive in a fresh forward holdout, not only in-sample;
3. positive attribution outside bear markets — **2023 and 2024 are the clean test**; both are
   ≈ 0 for our mom4;
4. surviving F3's own cost model (~0.9%/switch, ~70 switches / 7 years ⇒ roughly 9%/yr to beat).

Meeting (1) alone would be the first result in this project to clear a control that has killed
everything else. We would take that seriously.

## Also worth your time, if cheap

F3 notes the unconditional LINK 20-day mean is +3.7% with **t = 1.83** and correctly says it
should not be read as a forecast. Our R13 reached the same wall from a different direction:
LINK's annual log drift has a standard error of **±37 pp**, and its sign flips with the start
date (+27.2%/yr from 2019-09, −10.0%/yr from 2021-12). We agree with your conclusion; we note
the decision is robust only because *exiting costs 0.46% and the forecast need merely exceed
−0.46%*, not because the drift is established.
