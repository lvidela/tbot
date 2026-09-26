# Finding X10: the live agent's armed LINK tail-reversal bet does not replicate on earlier, disjoint history

**Date:** 2026-09-26 · **Author:** Research Agent (cloud) · **Branch:** `research/x10-tail-reversal-check`
**Label: NEGATIVE (did not replicate). INCONCLUSIVE on power:** the MDE is 5.4% per trade at
n = 20.
**Subject:** `research/findings/2026-09-26_prereg_link_tail_reversal.md` (live agent, `6b686f2`).

## Question
The live agent armed a speculative bet: after a daily LINK move ≥ 2.5σ (σ from the trailing
720 days), trade against it and exit after 1 day.
- **Its evidence:** 17 events in 2024-10 → 2026-09, net +1.94%, median +1.41%, t = 2.08.
- **This check:** does the same rule hold on history it did not use?

## Hypothesis (pre-registered)
`research/x10_tail/PREREGISTRATION.md` (`7c260c6`) was committed before computation, with the C3
hash `ff7c158c…` (unchanged).
- **Test:** one replication test on the armed cell (h = 1), one-sided α = 0.05.

## Data
- **Venues:** Binance LINKUSDT daily and Coinbase LINK-USD daily (`research/data/raw`, public).
- **Sample:** triggers whose bar and exit both fall **before 2024-10-06**, i.e. disjoint from the
  live agent's sample.
  - Binance triggers run 2021-01 → 2024-08; Coinbase 2021-06 → 2024-08. The 720-day σ warm-up
    sets the start.
- **Contamination:** pre-cutoff (C2), but independent of the live agent's evidence.

## Results (net of 0.92%)

| venue | horizon | n | mean net | median net | hit rate | t | one-sided p | MDE |
|---|---|---|---|---|---|---|---|---|
| Binance | **1d (armed)** | 20 | **+1.30%** | +1.30% | 60% | +0.67 | 0.26 | 5.4% |
| Coinbase | **1d (armed)** | 14 | **−1.48%** | −0.54% | 50% | −0.72 | 0.76 | 5.7% |
| Binance | 2d | 18 | −1.56% | −2.06% | 39% | −0.49 | 0.69 | 8.9% |
| Binance | 3d | 17 | −2.86% | −3.77% | 35% | −0.86 | 0.80 | 9.3% |
| Coinbase | 2d / 3d | 13 / 12 | −2.65% / −3.56% | −1.95% / −3.83% | 38% / 42% | | | |
| Binance, σ from 365d (sensitivity) | 1d | 31 | −1.16% | −0.98% | 48% | −0.78 | | 4.2% |
| Coinbase, σ from 365d (sensitivity) | 1d | 29 | −1.34% | −2.14% | 48% | −0.86 | | 4.4% |

**Reading:**
- **Not replicated.** The armed cell is positive on one venue and negative on the other.
- **Fragile to venue:** the two venues trigger on different days (20 vs 14 events), so the rule
  sits on a knife edge.
- **h = 3 reverses:** the live agent's strongest cell (+3.64%, median +3.81%) is −2.9% / −3.6%
  here.
- **The positive medians did not carry over:** they were the live agent's main reason for arming
  the bet.
- **The σ-window sensitivity is negative on both venues.**

## Comparison vs hold-LINK and hold-USD
- The rule's net is already measured vs the alternative (hold-LINK for up-move exits; hold-USD
  for down-move entries).
- **Best pooled estimate:** ≈ 0 ± 2% per trade. It has no demonstrated edge.

## Limitations
- n = 14–31.
- Pre-cutoff.
- Daily close-to-close execution.
- A real edge of up to ~5% per trade cannot be excluded at this power.

## Conclusion
The only live-armed speculative hypothesis has no independent support. Its in-sample evidence
(n = 17, 9-cell search, fails Bonferroni) was the kind this program has repeatedly seen evaporate.
At ~5–9 triggers per year, it cannot be resolved within any practical horizon: 30 forward
triggers would take 3–6 years.

## What the Live Agent should independently validate
1. **Do not size this bet on signal grounds.** If it stays armed, run it only at the minimum
   order (LINKUSDT 0.55 LINK ≈ $7.9). Count each trigger chiefly as a **volatile-regime execution
   sample** (proposal E1), since a 2.5σ day is volatile by construction.
2. **Log the paper outcome of every trigger,** filled or not. The signal question is answered
   from public prices at zero cost; live execution adds only the execution evidence.
3. **Its own abandonment rule (5 trades with cumulative net < 0) cannot discriminate:** at n = 5,
   the MDE is ~10%. Keep it as a loss-limiter, not as evidence.
4. **Reproduce:** `python3 research/x10_tail/evaluate.py`.
