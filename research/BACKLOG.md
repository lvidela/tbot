# Research backlog

Maintained by the Research Agent under `research/PROGRAM.md`.
- **Priority** is a judgement of three things: the plausible net edge after 0.46%/leg costs at a
  ~$58 account, how new the mechanism or data is relative to REGISTRY R1–R13, and whether it is
  feasible with public data.
- **The table is a snapshot.** The **Log** at the bottom is append-only, and its latest entry
  wins.

## Queue (snapshot 2026-09-25)

| id | hypothesis / objective | mechanism | data | why now / novelty | priority | status |
|---|---|---|---|---|---|---|
| X1 | Assets with high trailing perp funding underperform low-funding assets over the next 1–4 weeks | Funding measures leveraged-long crowding. Crowded longs pay carry and unwind | Binance archive: USDT-perp funding + spot 1d, **incl. delisted** (survivorship-free) | New dataset. Funding was only ever tested as LINK timing (T1 S6), never cross-sectionally. Weekly/monthly turnover suits 0.46% legs | 1 | **active** |
| X2 | High open-interest growth or an extreme long/short account ratio predicts cross-sectional underperformance | Positioning crowding, a second measure independent of funding | Binance archive `futures/um/daily/metrics` (from ~2021-12) | New dataset; shares X1's infrastructure | 2 | queued |
| X3 | After market-wide capitulation hours (BTC and the alt index down more than k·σ within hours), alts rebound over 1–3 days | Forced liquidations overshoot; liquidity providers are paid to absorb | Binance spot 1h archive (multi-year), Coinbase 1h cross-check | R4 tested only unconditional autocorrelation, and vol_expansion was demeaned on a short sample. A conditional, market-level event with large moves has not been tested | 3 | queued |
| X4 | A low-volatility / low-beta cross-section beats high-beta over a month (a betting-against-beta analogue) | Leverage-constrained buyers overpay for lottery-like, high-beta coins | X1 universe, monthly rebalance | A different mechanism from momentum/reversal (R3, R9); low turnover | 4 | queued |
| X5 | Deribit DVOL (BTC/ETH implied vol) level or term structure times LINK-vs-USD exposure | The volatility risk premium; implied vs realised as a regime signal | Deribit public API (reachable) | New dataset. T1 used only price- and funding-based states | 5 | queued |
| X6 | Post-listing drift: newly listed perps/spot underperform for their first N weeks | Hype decay and supply unlocks | Binance archive first-file dates | Mostly an *avoidance* rule for spot; lower value | 6 | queued |
| X7 | Stablecoin depegs (USDT/USDC vs USD) mean-revert fast enough to capture | Arbitrageurs restore the peg | Coinbase USDT-USD / USDC; Kraken 720 bars | Rare events, small n | 7 | queued |
| X8 | Day-of-week / time-of-day return effects | Flow seasonality | 1h archive | Expected magnitude is well below a 0.92% switch; kept only as an execution-timing input | 9 | parked (magnitude) |
| X9 | Cross-exchange price dislocations | Fragmented liquidity | multi-venue | **Not actionable:** the live agent trades one venue and may not transfer funds | — | closed by constraint |

## Log (append-only)

- **2026-09-25:** program started under researcher directive (`research/PROGRAM.md`). X1 chosen
  first, because it:
  - is the only candidate combining new data, a mechanism untested here, low turnover, and a
    survivorship-free universe (delisted perps are in the archive, e.g. LUNAUSDT);
  - builds the infrastructure that X2, X4 and X6 reuse.
