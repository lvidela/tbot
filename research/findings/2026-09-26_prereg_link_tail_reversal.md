# PRE-REGISTRATION: LINK tail-reversal speculative bet (committed before any setup exists)

**Author:** live agent · **Written 2026-09-26, and this is the point:** at the time of writing
**no trigger is present** — LINK's most recent daily move is +5.26% = **1.16σ** against a
trigger of **2.5σ = 11.36%**. So this commits to the bet before the opportunity exists, which is
the only way a speculative bet can be judged honestly rather than rationalised after the fact.

**Status: ARMED, not validated.** Speculative mode, small clip. Expected to fail more often than
not; recorded so that failure is informative.

---

## What the search actually found

Working the priority list from `2026-09-26_broadened_alpha_program.md`, starting with A1
(short-horizon conditional reversal in the held asset, 2 legs at 0.92%).

**First result — the cost arithmetic kills the whole short-horizon family, independently of any
signal.** LINK 4h σ = 1.30%, round-trip cost 0.92%:

| horizon | mean abs move | move / cost | net with PERFECT timing |
|---|---|---|---|
| 4h | 0.935% | **1.02×** | **+0.015%** |
| 12h | 1.561% | 1.70× | +0.641% |
| 1d | 2.503% | 2.72× | +1.583% |
| 2d | 3.450% | 3.75× | +2.530% |

At 4h, perfect direction-calling on every bar nets **+0.015%**. So short-horizon LINK trading is
arithmetically dead at this fee tier — not statistically weak, *arithmetically* dead. Clearing
cost by 3× requires **≥18 hours** of holding. **Any future LINK-vs-USD work must use a multi-day
horizon.** This kills A1 as specified, and it is the more useful half of the result.

Direct confirmation at short horizons (non-overlapping, cost charged): every cell negative net.
Best was 4h/k=2.5σ at mean reversion +0.264% against a 0.92% hurdle. MDE was 0.29–0.65%, so a
0.5% effect *was* detectable and is not there — and would not have been tradeable anyway.

## The pattern that survived, and its weaknesses stated first

Moving to the tradeable horizon, on 720 daily bars (2024-10-06 → 2026-09-25, σ = 4.54%/d),
non-overlapping, reversal signed positive, 0.92% charged:

| horizon | trigger | n | mean | median | t | net |
|---|---|---|---|---|---|---|
| 1d | 2.5σ | 17 | +2.86% | **+1.41%** | +2.08 | **+1.94%** |
| 2d | 2.5σ | 17 | +2.34% | −0.05% | +1.34 | +1.42% |
| 3d | 2.5σ | 14 | +3.64% | **+3.81%** | +1.33 | **+2.72%** |
| 1d–3d | 1.5σ / 2.0σ | 27–67 | −0.83% to +0.73% | negative | ~0 | negative |

**Why this is not a validated edge:**
- **9 cells were searched.** Best |t| = 2.08; Bonferroni over 9 needs ≈ 2.77. **It fails.**
- **n = 14–17**, and the effect appears *only* in the extreme tail where n is smallest. That is
  the shape of a small-sample artefact.
- The in-sample/holdout split **flips sign** for the 1.5σ cells (−0.99% → +2.93% at h=2), which
  is the X1 failure mode the registry already rejected.

**Why it is nonetheless worth a small bet:**
- The 2.5σ cells are positive at **all three** horizons, so it is not one lucky cell.
- **Medians are positive** at h=1 (+1.41%) and h=3 (+3.81%). Almost every rejected finding in
  this project had a negative median while the mean was dragged up by a tail; this is the
  opposite shape, which is what a real overreaction effect should look like.
- The mechanism is orthodox and documented outside this project: short-term overreaction to
  large moves, then partial retracement.
- It survives the cost hurdle by 1.5–3×, not by a hair.

## Pre-registered rules — fixed now, before any trigger

- **Trigger:** a completed daily bar with |log return| ≥ **2.5σ**, σ = sd of the trailing 720
  daily log returns as of that bar. Currently 2.5σ = 11.36%.
- **Direction:** against the move (reversal). Up-move ⇒ sell LINK to USD; down-move ⇒ buy LINK.
- **Horizon:** exit at **+1 day** (the cell with the best t and a positive median). No discretion.
- **Size:** conviction-based via `scripts/conviction.py`, `validated_edge = 0.5` (suggestive,
  unreplicated) — a small speculative clip, **not** a core reallocation. Hard ceiling **10%** of
  portfolio for this hypothesis regardless of what the sizer returns.
- **Costs:** 2 maker legs, 0.46%/leg including measured adverse selection.
- **Execution:** post-only. A failed passive fill is a missed trade, never a reason to cross
  (`edge.should_cross_spread`).
- **Invalidation / abandonment:** abandon after **5 triggered trades** if cumulative net < 0, or
  immediately if any single trade loses more than 2× the 4.54% daily σ.
- **Record:** every trigger gets a `decisions.py` entry with thesis, expected net, confidence and
  invalidation, written before the outcome; rejected triggers are recorded too.

**Expected net per trade: +1.9%.** **Confidence: 0.35** — i.e. I expect this to be wrong about
two times in three, and it is sized accordingly.

## What would make me stop, and what would make me scale

**Stop:** 5 trades with cumulative net < 0; or the pooled t falling below 1.0 as n grows; or the
median turning negative (the mean alone was never the reason).

**Scale up** only if an independent, uncontaminated sample reaches |t| > 3 with a positive median
— and even then via the conviction sizer, not by fiat.

## Honest summary

No trade was taken today, and not out of caution: **there is no setup.** 1.16σ against an 11.36σ
threshold. The deliverable is the arithmetic that rules out the entire short-horizon family, plus
one hypothesis armed and pre-committed so that when a 2.5σ day arrives the bet is already
specified.
