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
- **2026-09-25 23:20Z — X1 closed: NEGATIVE.** Finding `2026-09-25_x1_funding_crowding.md`.
  - **Evidence:** strong against the spot-actionable form (holdout CIs exclude 0 on the harmful
    side). The information test is unstable: the IC sign flips between 2020–23 and 2024–26.
  - **Learned:**
    1. Positioning signals are regime-dependent in sign.
    2. Extreme negative funding marks distressed coins.
    3. The survivorship-free liquid-alt basket was 0.16× vs LINK 0.84× in 2024–26, so broad
       rotation priors should be pessimistic.
  - **Invalidation:** a new regime with a negative IC on a fresh holdout.
  - **Re-prioritisation:**
    - X2 (OI / long-short ratio) is demoted to priority 5. It measures the same crowding
      mechanism, and X1 shows that mechanism's sign is unstable.
    - **X4 (low-vol / low-beta cross-section, monthly) is next.** It reuses X1's survivorship-free
      panel. It is the only rotation idea whose mechanism predicts the 2024–26 pattern (high-vol
      alts bleeding) ex ante. At monthly turnover it could clear 0.92% switches. It also answers
      R13's "hold another asset" question with far more assets than a single pair.
    - X3 (capitulation rebound) follows.
- **2026-09-25 23:25Z — X4 closed: REQUIRES VALIDATION.** Finding
  `2026-09-26_x4_low_volatility.md`.
  - **Evidence:** strong for information (holdout t = −6.87, every year negative). Weak for
    economics vs the live holding (hold-LINK/BTC CIs span 0).
  - **Learned:** unlike positioning (X1), volatility ranks are regime-stable. The decision value
    is as a filter against high-vol rotation and tactical entries, not as a switch.
  - **Invalidation:** a positive IC over two consecutive quarters of fresh data.
  - **Next:** X4b, a **venue replication on Kraken's own public daily data**. It is cheap, and it
    is exactly what the live agent would need before any filter:
    - `research/tsmom/ohlc_long.json`, 20 Kraken assets, 2024-10 → 2026-09;
    - pre-registered IC(vol60, fwd 28d) < 0.
  - **Then:** X3 (capitulation rebound).
  - **New idea (priority 4):** X12, vol-managed exposure to LINK itself. Scale LINK exposure
    inversely to its trailing volatility (the time-series analogue of X4). It needs the
    static-exposure control from the live agent's S2 request.
- **2026-09-25 23:35Z — X4b closed: POSITIVE (replication).** Kraken IC −0.195 (t = −4.69). The
  low-vol effect is venue-robust. The filter recommendation stands; there is no switch
  recommendation.
  - **Next: X3,** capitulation rebound. Pre-register first. It uses daily data already in hand:
    X1's survivorship-free panel and Coinbase for BTC/LINK. An hourly version comes only if the
    daily result is promising.
