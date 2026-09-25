# Which asset should the account hold? (first direct test)

**Author:** live agent, session `s-2026-09-25T1427Z-08`
**Status: NOT RESOLVABLE from available data. No trade. Position unchanged: 100% LINK.**

---

## Why this question, and why it is new

Every strategy study in this project has asked *when* to trade. None has asked *what to hold*.
The registry rejects rotation (R3), reversal (R9) and timing (this session) — all of which are
frequency questions. But the account's outcome over an open-ended horizon is dominated by a
single decision that costs **0.81% once** (2 maker legs): which asset sits in the account.

Q5 in `DEEP_REVIEW_2026-09-25.md` tested LINK vs *cash* and found it unresolvable. LINK vs
*another crypto asset* had not been tested.

## Data

20 Kraken USD pairs, weekly closes from `research/tsmom/ohlc_long.json` (fetched read-only from
the public API). Two windows, deliberately both reported because the answer is start-date
sensitive:

### A. Common window across all 20 assets — 249 weeks from **2021-12-16**

| asset | W_hold | log/yr | vol/yr | maxDD |
|---|---|---|---|---|
| TRXUSD | 4.33 | +30.8% | 45.9% | −41.9% |
| XBTUSD | 1.74 | +11.6% | 51.1% | −67.4% |
| XRPUSD | 1.57 | +9.5% | 79.0% | −69.3% |
| ETHUSD | 0.67 | −8.3% | 69.5% | −73.7% |
| **LINKUSD** | **0.62** | **−10.0%** | **80.5%** | **−80.4%** |
| … | | | | |
| DOTUSD | 0.04 | −67.5% | 76.9% | −97.2% |
| FILUSD | 0.03 | −76.6% | 91.3% | −98.1% |

**14 of 20 lost money. Median W_hold = 0.57. Six lost more than 90%. LINK ranks 9/20.**

### B. LINK's own full history — 366 weeks from 2019-09-19 (paired, identical weeks)

| | W_hold | log/yr ± 1 s.e. | vol/yr |
|---|---|---|---|
| LINKUSD | 6.68 | +27.2% ± 37.1 | 98.2% |
| XBTUSD | 10.00 | +32.9% ± 22.4 | 59.3% |
| ETHUSD | 15.80 | +39.5% ± 30.5 | 80.7% |

Paired weekly log-drift differences:
- **LINK − BTC: −5.8%/yr, t = −0.20**
- **LINK − ETH: −12.3%/yr, t = −0.50**

## Finding

**The drift comparison is not resolvable and it is not close to resolvable.** The standard
error on LINK's annual log drift is ±37 percentage points. The point estimates favour BTC and
ETH, and both are less than one standard error away from zero difference. Switching on these
numbers would be selecting on past returns, which is exactly the error the registry rejects in
R3 and R9 — and it would cost 0.81% to act on.

Note also that window A and window B **disagree in sign** for LINK (−10.0%/yr vs +27.2%/yr).
Window A begins within weeks of the cycle top. Neither window is privileged, which is itself
the finding: **crypto drift estimates at 5–7 year samples are dominated by start-date choice.**

## The one precisely-estimated quantity, and why it still does not justify a trade

Volatility converges far faster than mean return, so this difference *is* real:
**LINK 98.2%/yr vs BTC 59.3%/yr — LINK is ~1.66× as volatile.**

The tempting argument: if arithmetic drifts were equal, then since log-drift = arith − σ²/2,
BTC's *median* outcome would compound about 30%/yr faster, and a one-off 0.81% switch would be
trivially worth it.

**I do not think that argument survives, and I am recording why so it is not re-made.** The
premise is unsupported in both directions. Adding σ²/2 back to the realised log drifts gives
implied arithmetic drift of roughly **LINK +75%/yr vs BTC +50%/yr** — i.e. in this sample the
higher-volatility asset had the *higher* arithmetic drift, which is also what any risk-premium
reasoning would predict. So "equal arithmetic drift" is not a neutral null; it is an assumption
that happens to favour the conclusion, and the data contradict it. The variance-drag argument
for BTC and the risk-premium argument for LINK are the same size as the noise.

This is the same trap as registry R8 (volatility drag double-counting) wearing different
clothes: realised returns already contain the drag.

## Robust observation that is NOT a trading signal

The left tail of the altcoin distribution is severe and it is a measured base rate, not an
extrapolation: **6 of 20 Kraken-listed, reasonably liquid assets lost >90% in 4.8 years.** For
an open-ended horizon, concentration in a single mid-cap protocol carries genuine permanent-loss
risk that a drift estimate does not capture.

I am deliberately **not** acting on it, for a reason worth stating: those 20 assets share one
dominant factor and one 2022 bear market, so "6 of 20" is nearer one or two independent
observations than twenty — the same correction that sank R1 and the TSMOM cross-asset count.
It constrains far less than it appears to.

## Decision

**HOLD 100% LINK. No trade.** Not because LINK is established as the best asset — it is not —
but because no alternative is distinguishable from it at any conventional standard, and every
alternative costs 0.81% to reach.

## What would change it

1. A drift difference that is significant on paired weekly data — needs either far more history
   or far lower volatility than crypto offers. Realistically unreachable.
2. An asset-specific, non-price fact about LINK (delisting notice, protocol failure, a Kraken
   minimum or liquidity change). This is a **monitoring** task, not a statistical one, and it is
   the only route by which this decision should flip quickly.
3. A change in the objective from expected to median final USD, which would reopen the
   variance-drag argument — but that is a researcher's call, not mine to assume.
