# Pre-registration T1: market-level timing of LINK vs USD

**Registered:** 2026-09-25T15:46Z by the Research Agent (cloud session), **before any data for this
test was obtained or inspected.** No market data could be downloaded from this environment at
registration time: the network policy returned 403 for every exchange host. The git commit that
adds this file is the timestamp of record. Any change after the first data run must be appended
under "Amendments", dated, with the reason. Past text is never edited.

## 1. Question

Can a small, fixed set of market-level signals forecast LINK's forward return vs USD over
5–20 days well enough that switching between LINK and USD beats hold-LINK after costs?

Why this question: F1 showed the LINK-vs-USD exposure decision is about 9× larger in dollars
than any plausible tactical edge. DEEP_REVIEW Idea B (majors lead/lag) used only ~120 days of
1h/4h bars. Not previously tested: multi-year daily data, trend / crash / volatility / funding
state variables.

Not a repeat of a rejected hypothesis:
- R3 and R9 were cross-sectional. Demeaning removes the market factor, so they say nothing about timing.
- R4 was LINK daily lag-1 autocorrelation, a 1-day horizon.
- Idea B was 1h/4h BTC/ETH lead/lag over ~120 days.
- New material here: ~7 years of daily data, horizons of 5–20 days, and state variables none of
  those tests used.

## 2. Hypotheses (direction fixed a priori)

H1–H6: when signal S_i is OFF, LINK's mean forward h-day return is lower than when it is ON.
The trading rule holds LINK when ON and USD when OFF.

| id | name | ON (hold LINK) when… | a-priori rationale for the direction |
|---|---|---|---|
| S1 | BTC_SMA200 | BTC close > 200-day SMA of BTC close | time-series momentum / market trend |
| S2 | BTC_SMA50 | BTC close > 50-day SMA of BTC close | faster trend variant |
| S3 | LINK_SMA50 | LINK close > 50-day SMA of LINK close | own-asset trend |
| S4 | LINK_NO_CRASH | LINK drawdown from its trailing 90-day max close > −30% | crash momentum: deep drawdowns keep falling |
| S5 | LINK_CALM_VOL | LINK 20-day realised vol (sd of daily log returns) ≤ 1.5 × the median of that series over the trailing 365 days | volatility-managed exposure; high-vol states have worse risk-adjusted returns |
| S6 | FUNDING_NOT_CROWDED | 7-day mean of Binance LINKUSDT perpetual funding (per 8h) ≤ 90th percentile of that 7-day mean over the trailing 365 days | crowded longs precede drawdowns |

All inputs are known at the daily close of day t (00:00 UTC bar boundary). Moving averages and
percentiles use data up to and including day t only.

Open interest is **not** in the family. Binance public OI history covers only ~30 days, so no
multi-year series exists. It may be added as exploratory only.

Horizons: **h ∈ {5, 10, 20} days**. **Family = 6 signals × 3 horizons = 18 tests.**

## 3. Data (planned)

| series | primary | cross-check | notes |
|---|---|---|---|
| LINK/USD daily | Coinbase Exchange LINK-USD | Binance LINKUSDT (spot); Kraken LINKUSD (last 720 days only) | Coinbase listing mid-2019 |
| BTC/USD daily | Coinbase BTC-USD | Binance BTCUSDT; Kraken XBTUSD | |
| ETH, SOL daily | Coinbase ETH-USD / SOL-USD | Binance ETHUSDT / SOLUSDT | robustness only |
| LINK funding | Binance USDⓈ-M LINKUSDT fundingRate | Bybit linear LINKUSDT funding | perp from ~2020-01 |

- Period: from the first date both LINK sources exist (expected ~2019-07) to 2026-09-24.
- Daily bar = the 00:00–24:00 UTC candle close.
- Cross-exchange check: flag any day where |log(close_A / close_B)| > 2%. Investigate and
  report every flagged cluster. Use primary data unless it is shown wrong.
- A 365-day warm-up applies where a signal needs it (S5, S6). S6 therefore starts ~2021.

## 4. Test protocol

- **Decision dates:** non-overlapping, every h days. All h phase offsets are run and averaged
  (registry rule D7).
- **Forward return:** R = close[t+h] / close[t] − 1, executed at close t.
- **Robustness:** a 1-day execution lag, deciding at t and executing at close t+1.
- **Strategy per window:** ON → R; OFF → 0 (USD).
- **Cost:** charged per leg whenever the state changes between consecutive decision dates.
  - maker: 0.46%/leg (0.40% fee + 5.4 bps adverse selection, rounded up; a round trip is 0.92%)
  - taker: 0.83%/leg
- **Account:** $59 notional. LINK ordermin is 0.55 LINK (~$7.7), so a full switch of ~4.19 LINK
  is always feasible and there is no partial-size effect.
- **Excess vs hold-LINK per window:** strategy_net − R. Also reported vs hold-USD, i.e. strategy_net − 0.

**Statistics per test:**
1. **Conditional spread** d = mean(R | ON) − mean(R | OFF): Welch t per phase, then
   phase-averaged. The reported t is the phase-averaged d divided by the phase-averaged SE, with
   the per-phase min and max also shown.
2. **Mean net excess vs hold-LINK** per window, with the same phase treatment.
3. **95% CI:** d ± t₀.₉₇₅ · SE.
4. **MDE** at 80% power, both unadjusted (α = 0.05) and Bonferroni-adjusted (α = 0.05/18).
5. **Family-wise permutation:** 2,000 circular shifts of each signal series against returns,
   each shift ≥ 90 days. This keeps the autocorrelation of both series. The statistic is the
   family max |t| over all 18 tests.

**Train/test split (chronological):**
- In-sample: start to 2023-12-31.
- Holdout: 2024-01-01 to 2026-09-24.
- Parameters are fixed above, so nothing is fitted. The split exists to test replication. The
  holdout is only examined after the in-sample table is written to disk.

## 5. Decision rule for labelling (fixed now)

**POSITIVE** requires all of the following for a given signal:
- (a) the full sample passes Bonferroni (|t| ≥ critical at α = 0.05/18) in the registered direction;
- (b) the family-wise permutation p < 0.05;
- (c) in the holdout, the spread has the same sign and the net excess vs hold-LINK is > 0 at maker cost;
- (d) the spread has the same sign in at least 2 of 3 sub-periods (2019–21, 2022–23, 2024–26);
- (e) ETH or SOL shows the same sign (for S3–S5, recomputed on that asset's own series);
- (f) at least 3 of 4 perturbations keep the sign. Perturbations: lookback ×0.7 and ×1.3,
  threshold ±1/3 of its distance from the neutral value.

**Otherwise:**
- **REQUIRES VALIDATION** if (a) or (b) passes but any of (c)–(f) fails.
- **NEGATIVE** if no test passes (a) and the Bonferroni MDE is ≤ 3% per 20 days, i.e. the
  test had power against economically relevant effects.
- **INCONCLUSIVE** otherwise.

## 6. Secondary, decision-theoretic analysis (pre-registered)

The live decision is taken once, in the current state, over ~20 days. So a significance test is
not the right decision tool.

- **Prior:** the h = 20 spread d ~ N(0, τ²) with τ = 3% per 20 days. Sensitivity runs use
  τ = 1.5% and 6%.
- **Posterior mean:** d · τ² / (τ² + SE²).
- **Implied shrunk forecast:** E[R | current state] = unconditional mean + shrunk deviation of
  the current state.
- **Exit to USD only if:** that shrunk forecast < −0.46% (exit-and-stay costs one leg, because the
  account is valued in USD at the end).
- The output states the current signal states and this number. It is advisory. The live agent
  decides.

## 7. Amendments

These amendments were made on 2026-09-25 while writing the code, before any data was obtained.
No data has been seen. Each one fills a gap the original text left open.

- **A1 (criterion e):** S1 and S2 are BTC signals, so for replication they are evaluated against
  ETH and SOL returns unchanged. S3–S5 are recomputed on ETH's and SOL's own prices. S6 depends
  on LINK funding, and no multi-year ETH/SOL funding is fetched, so (e) is waived for S6. S6
  therefore needs (a)–(d) and (f), and a POSITIVE S6 must be reported as carrying weaker
  replication evidence.
- **A2 (section 6, combining signals):**
  - The six signals are strongly correlated because they describe one market state, so their
    shrunk tilts are **not summed**.
  - The forecast is the unconditional non-overlapping 20-day mean plus the single largest
    shrunk tilt, by absolute value.
  - For signal i, the tilt is the shrunk spread × (1 − P(ON)) when the signal is ON, and
    −(shrunk spread) × P(ON) when it is OFF.
- **A3 (unconditional mean):** the unconditional mean is the mean of non-overlapping 20-day LINK
  returns over the full sample, with no shrinkage. Its SE is reported alongside it, since it
  dominates the forecast uncertainty.
- **A4 (criterion f, S6):** moving S6's threshold outward by 1/3 of its distance from neutral
  gives an invalid quantile (0.9 + 0.133 > 1). The end-to-end synthetic smoke test found this.
  The outward S6 perturbation is therefore 1/3 of the way from 0.90 to 1, i.e. q = 0.933. The
  inward one is unchanged at q = 0.767.
- **A5 (criterion f, S1–S3):** S1–S3 are pure SMA-vs-price signals and have no threshold. Their
  four perturbations are therefore lookback ×0.7, ×0.85, ×1.15 and ×1.3.
- **A6 (data sources, 2026-09-25T17:00Z, before any download):** from this environment
  `api.binance.com` and `fapi.binance.com` return HTTP 451, and `api.bybit.com` returns HTTP 403.
  These are the exchanges' own geo-restrictions and are not routed around.
  - Binance spot klines and USDⓈ-M funding history come from Binance's official public archive,
    `data.binance.vision`. It holds the same data, in monthly files.
  - The funding cross-check uses OKX (`www.okx.com` funding-rate-history) instead of Bybit. OKX
    exposes only recent months, so the cross-check covers their overlap only.
  - The archive's funding files are monthly, so S6 may lack the most recent weeks. S6's current
    state is then reported as unknown rather than filled from another exchange.
