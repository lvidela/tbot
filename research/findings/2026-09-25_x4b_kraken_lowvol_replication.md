# Finding X4b: X4's low-volatility effect replicates on Kraken's own prices

**Date:** 2026-09-25 · **Author:** Research Agent (cloud) · **Branch:** `research/x4b-kraken-lowvol`
**Label: POSITIVE** for the information replication, which was the pre-registered question.
**Economically, same as X4:** the low-vol basket beats random selection but not hold-LINK.

## Question
Does X4's negative relation between trailing volatility and forward 28-day return hold on the live
venue's own prices and listed assets?

## Hypothesis (pre-registered)
- `research/x4b_kraken/PREREGISTRATION.md` (`35f10bc`) was committed before computation.
- **Test:** one test, mean Spearman IC(vol60, fwd 28d) < 0, one-sided α = 0.05.

## Data sources / period / timestamps
- Kraken public daily OHLC for 20 USD pairs (`research/tsmom/ohlc_long.json`, key `1440`),
  2024-10-05 → 2026-09-24.
- There are 22 non-overlapping 4-week periods on X4's grid, with a median 20 assets per period.
- **Survivorship-biased:** these are today's listings.
- **The window overlaps X4's holdout.** This replicates venue and universe, not time.

## Methodology
Identical to X4's primary test: vol60 from the 60 daily log returns ending at close(t), with
non-overlapping 28-day windows. Reproduce with `python3 research/x4b_kraken/replicate.py`.

## Results

**Information:**

| | mean IC | t | one-sided p | MDE |
|---|---|---|---|---|
| **phase 0 (primary)** | **−0.195** | **−4.69** | 0.00006 | 0.117 |
| phase 1 | −0.181 | −2.73 | 0.006 | 0.185 |
| phase 2 | −0.170 | −2.86 | 0.005 | 0.166 |
| phase 3 | −0.140 | −2.60 | 0.008 | 0.150 |

**Economics (descriptive, maker 0.46% per leg, 22 periods):**

| basket | wealth |
|---|---|
| lowest-5-vol | 0.54× |
| random-5 (median) | 0.38× |
| highest-5-vol | 0.35× |
| hold-LINK | **0.63×** |

- The low-5 basket's mean excess over random-5 is +1.3% per 28d.
- Against LINK it is −1.9% per 28d.
- Within this 20-asset Kraken set, LINK sits at a median **61st** volatility percentile (range
  26th–100th). In X4's broader Binance universe it sat at the 32nd.

## Comparison vs hold-LINK and hold-USD
Every basket and hold-LINK lost against hold-USD over this window, a falling market. Hold-LINK
beat every volatility-sorted basket.

## Limitations
- 20 survivorship-biased assets.
- The window overlaps X4's holdout.
- 22 periods.

## Conclusion
The low-vol ranking effect is not a Binance or universe artefact. It holds on Kraken's prices and
listings with a similar magnitude (IC ≈ −0.2). Its economic use for this account remains a
**filter** (avoid the high-vol end, especially for tactical entries), not a reason to leave LINK.

## What the Live Agent should independently validate
1. **Rerun `replicate.py` on the live VM's own Kraken cache**, extended to the 37 eligible pairs.
   Expect IC < 0.
2. **Check whether tactical-mode and shadow-ledger entries fall in the top volatility half.** If
   they do, X4/X4b argue for a vol60 ≤ median filter on tactical entries.
3. **Nothing here says to sell LINK.** Hold-LINK beat every volatility-sorted basket over this
   window.
