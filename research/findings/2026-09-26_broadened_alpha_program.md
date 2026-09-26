# Broadened alpha search: which genuinely different directions are worth compute, and which are already dead

**Author:** live agent · **Date:** 2026-09-26
**Purpose:** researcher directive — stop searching only breakout / momentum / volatility /
confluence. This screens the named alternatives against the **live cost structure**, which is
the thing that kills most of them, so compute goes to the two or three that can actually clear.

**Live economics, measured, not assumed:** maker **0.40%/leg** + **5.4 bps** realised adverse
selection ⇒ **~0.46%/leg**. A 2-leg move (LINK→USD→LINK, or in/out of the held asset) costs
**~0.92%**. A 4-leg rotation (out of LINK, into X, out of X, back) costs **~1.83%**.
Account ≈ $59. Next fee tier is at **$2,500 / 30d volume** (taker 0.80% → 0.60%); we are at $88,
and buying that tier costs more than it saves at this size.

---

## Screened OUT on cost, with the arithmetic

| direction | edge lives at | our cost | verdict |
|---|---|---|---|
| **Order-flow / microstructure** | 1–10 bps | 46 bps/leg | **Dead. 5–46×short.** Confirmed twice: registry R11, and again live on 2026-09-25 when the spread-capture watcher fired four times and every hit failed on realised round-trip drift (GRASS −67.5 bps vs an 80 bps hurdle). |
| **Market-making / spread capture** | the spread, minus adverse selection | 92 bps round trip | **Dead.** 152 of 618 USD pairs exceed the hurdle on quoted spread and none is liquid — wide spreads exist precisely where market-making is unprofitable. That is equilibrium, not opportunity. |
| **Variance-risk-premium harvesting** (X5) | options / perps | — | **Structurally unavailable.** Requires derivatives; CLAUDE.md Hard Rule 2 is spot-only. Not a cost question. |

Please do not spend further compute on these three without a **material fee-tier change**,
stated explicitly. That is the only input that moves them.

## Worth compute, in priority order

### A1. Short-horizon reversal in the HELD asset (2 legs, not 4)

**Why it is the best candidate:** it is the only family that avoids the 4-leg penalty entirely.
We already hold LINK, so the trade is LINK→USD→LINK and the hurdle is **0.92%, not 1.83%**.
Halving the hurdle roughly doubles the fraction of the return distribution that can clear it.

**Why R4 does not already answer it.** R4 rejected LINK mean reversion on **lag-1
autocorrelation of returns** at daily/1h/4h. That is a test of *unconditional* linear
dependence and it is weak: it averages over every state of the world. The open question is
**conditional** reversal — after an N-sigma move, after a volume spike with no news, into a
session boundary. Those are different estimators and R4 does not cover them.

**Pre-registration should fix, before looking:** the trigger (e.g. |1h return| ≥ 2σ of trailing
1h vol), the horizon (1h / 4h / 24h), the cost (0.92%, 2 legs), and the direction (reversal).
Non-overlapping or phase-averaged windows, per D7.

**Hurdle to be interesting:** mean net > 0.92% per round trip with a CI excluding zero, or a
median > 0 with a hit rate that survives the cost.

### A2. Regime-conditional versions of already-rejected signals

T1 killed *unconditional* market timing (family-wise p = 0.47). It did **not** test whether any
signal works **conditional on regime** — high vs low realised vol, trending vs ranging, BTC
dominance rising vs falling. This is cheap because the data and the pipelines already exist;
it is a re-slice, not a new collection.

**The trap, and it is the whole reason to pre-register:** conditioning multiplies the trial
count. Three regimes × the existing signal family is a large family, and the trial ledger is
already at K = 262. Register the regime definitions and the exact cells **before** looking, and
charge the full multiple-testing cost. A regime-conditional result found after the fact is
worth nothing here.

### A3. Relative value / cointegration on WIDE divergences only

4 legs ⇒ **1.83%**, so only large divergences can clear. That makes the interesting question
narrow and testable: **conditional on a cointegrated pair diverging by ≥ X σ, is the
convergence larger than 1.83% net?** Screening every pair for cointegration is the wrong
experiment — it is a multiple-testing swamp with a cost floor most pairs can never clear.

Constraint worth knowing: our eligible set is 37 pairs, and any second leg must clear the
volatility veto (`scripts/volfilter.py`, from X4) — rotating into a much higher-vol name is
refused regardless of the spread signal.

## Two things the live side now provides

1. **`scripts/decisions.py`** — every meaningful decision records thesis, expected return,
   estimated cost, confidence, horizon, size and an **invalidation condition**, with the outcome
   appended later. Predictions are written before outcomes exist, so calibration becomes
   measurable rather than remembered.
2. **`scripts/selfreview.py`** — periodic FN/FP review across the counterfactual, shadow,
   decision and execution records, run on the 24h cycle.

**First result from it, and it is relevant to what you test next.** Rejected opportunities,
marked forward at 6h: **n = 43 over 28 distinct opportunities, mean −1.73% net, median −1.94%,
win rate 19%, clustered 95% CI (−3.24, −0.18) — entirely negative.** Excess vs the held asset
−0.59%. Hypothetical P&L had we taken them: **−$8.55.**

So the gate is not currently producing false negatives; it is avoiding losses. Combined with the
volatility-bias finding — 18 of 22 of our own candidates sit above LINK in volatility rank — the
conclusion is that **the detector family is the problem, not the threshold.** Loosening the gate
would buy more of a losing distribution. That is the argument for spending compute on A1–A3
rather than on re-tuning what exists.

## Standing caveat

Small samples. 43 overlapping observations across 28 opportunities is not a law, the horizons
are serially correlated (D7), and the whole record spans two days. None of it should be used to
fit a threshold, and `counterfactual.py` says so in its own docstring for the same reason.
