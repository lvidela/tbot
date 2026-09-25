# Finding: where the remaining dollars are (stakes analysis) + forward-evidence status

**Date:** 2026-09-25 · **Author:** Research Agent (cloud session) · **Label: INCONCLUSIVE (decision analysis; no new market data)**

## Research question
With 20 days left and a ~$59 account, which decision levers can materially move final net USD
relative to the hold-LINK benchmark, and is further tactical-signal research worth its cost?

## Hypothesis (stated before computing)
The LINK-vs-USD exposure decision dominates any plausible tactical edge by roughly an order of
magnitude, so tactical-signal research has low dollar value before the end date.

## Data sources / period
- No new market data. This cloud environment's network policy returns HTTP 403 for Kraken,
  Binance, Coinbase, OKX, Bybit, Deribit, CoinGecko and similar hosts (checked 2026-09-25 ~15:10Z).
  Only GitHub and PyPI were reachable.
- Inputs come from repo records: `STATE.md` (account $58.94, 2026-09-25 13:05Z), `REGISTRY.md`
  (A1 cost 1.83% per maker round trip, R9/D5 MDE 2.5–7.5%), `DEEP_REVIEW_2026-09-25.md`
  (LINK 21d forward mean +2.23%, CI [−3.77%, +8.48%]).
- Forward ledgers: `data/counterfactual_ledger.json` (30 records), `data/shadow_trades.json`
  (19 open records).

## Methodology
Pure arithmetic in `research/stakes/stakes.py` (reproducible, no network). LINK daily sigma was
not measurable here, so the analysis sweeps 3.5% / 4.5% / 6.0%.

## Results
| Lever | USD magnitude over 20 days |
|---|---|
| Exposure (LINK vs USD), 1σ tracking vs benchmark | **±$9.2 / ±$11.9 / ±$15.8** (σ 3.5 / 4.5 / 6.0%) |
| Expected-value gap of exiting to USD (from 21d CI) | −$5.00 … +$2.22, point −$1.31 |
| Tactical, TRUE 1% net edge × 10 trades on $13 notional | **+$1.30** |
| Tactical, TRUE 0.5% net edge × 10 trades | +$0.65 |

- Exposure lever ÷ tactical lever ≈ **9×** at σ 4.5% and a 1% net edge (an edge larger than
  anything this repo has been able to detect).
- **Validation is impossible in the time left:** detecting a 1% net edge at t = 2 needs about
  324 independent trades (per-trade sd ≈ 9%). Twenty days of 72h trades gives about 6 per slot.

### Forward evidence (the uncontaminated data)
- Counterfactual ledger: all 30 records were made between 11:20:26Z and 11:21:24Z on
  2026-09-25. That is **one cross-sectional snapshot**, not 30 observations. Excess vs LINK:
  5m mean −1.31% (2/30 positive), 30m mean −1.45% (2/30 positive), charged at taker fees.
- Shadow ledger: 19 positions, all still open, opened within a 12-hour window. Mean excess
  −0.82%, median +0.09%, 10/19 positive. Effectively one to two independent observations.
- Neither ledger supports loosening the gate. Neither can refute it either.

## Statistical evidence / robustness
The ranking holds across the whole sigma sweep, and for any net edge below about 4.5%/trade
at 10 trades. The conclusion flips only if a true net edge of ≥4–5% per trade existed. Existing
studies could not exclude one (MDE), but none has estimated one with a positive median.

## Assumptions
- Tactical notional $13 per position (≈22% of account), the size the ledgers use.
- Maker round trip 1.83% incl. adverse selection (A1). Taker is worse.
- Minimum order sizes permit $13 positions on the eligible pairs (per `universe.py` gate: min
  order ≤ 35% of portfolio).

## Limitations
- No fresh market data. Sigma is swept, not measured.
- The hold-vs-cash CI comes from one earlier in-repo study over a single bullish window.
- Derivatives/hedging could change the exposure lever, e.g. hedging LINK beta. However: (a)
  the live agent's Hard Rule 2 forbids them, so they are **not actionable without a researcher
  rule change**; (b) no derivatives data was reachable to test them here.

## Conclusion
For the remaining horizon, **almost all of the variance in final USD is the LINK exposure
decision**, and that decision is not statistically resolvable (the CI straddles zero and the
switch cost). Tactical trading can add at most around a dollar even under optimistic edge
assumptions, and no edge could be validated before 2026-10-15. This supports the current
HOLD-LINK posture. Treat the tactical gate as a risk filter, not a profit centre. This does not
prove tactical edges are absent. It shows they are too small, in dollars, to be the priority.

## What the Live Agent should independently validate
1. Measure LINK's realised daily sigma over the last 30/90 days and rerun `stakes.py` with it.
2. Check that no pending tactical plan puts more than a few dollars at risk for a sub-dollar
   expected gain.
3. Treat the ledgers as clustered: count independent decision *times*, not records, before
   citing them.

## Recommended next experiment
- **Exposure decision as a regime question, with more history:** can any pre-registered
  market-level signal (BTC trend, funding extremes, drawdown state) forecast LINK's 20-day
  return vs USD with non-overlapping t ≥ 2 over multiple years? This is the only lever large
  enough to matter. It needs multi-year daily data from a reachable source, or a network-policy
  change for this environment.
- Keep the shadow ledger accruing and spread decision times out. Today's records are
  concentrated in one or two market moments.
