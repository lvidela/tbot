# research/data — cached public market data

Only unauthenticated public endpoints are used, and no credentials are involved.

| path | produced by | content |
|---|---|---|
| `raw/<source>_<ASSET>_1d.json` | `research/timing/fetch.py` | daily OHLCV rows `[t_open_unix_s, open, high, low, close, volume]`, ascending, plus a `meta` header: source, symbol, URL, `fetched_at` UTC, row count, first/last timestamp |
| `raw/<source>_LINK_funding.json` | same | perpetual funding prints `[funding_time_unix_s, rate_per_8h]` |
| `raw/_fetch_log.jsonl` | same | one line per fetch or probe attempt, including failures (e.g. proxy 403) |

**Conventions**
- A daily bar is labelled by its UTC open date. Its close is the price at 00:00 UTC the next day.
- Sources:
  - Coinbase Exchange (USD) is primary.
  - Binance (USDT) and Kraken (USD) are cross-checks. Kraken's public OHLC returns only the
    last 720 bars.
  - A Coinbase-vs-Binance difference includes the USDT/USD basis.
- **Size:** about 2,700 rows × 12 series plus funding, well under 5 MB in total. It is committed
  so results can be reproduced. Do not commit intraday data here. Put it outside git or behind
  `.gitignore`.

**Status 2026-09-25:**
- The first attempts (15:44Z and 15:55Z) were blocked: every exchange host returned a proxy 403.
- After the network policy changed, the full set was downloaded between ~17:20Z and ~17:45Z:
  12 daily spot series plus Binance and OKX LINK funding, 1.7 MB.
- The data is committed locally (commit `9b8d785`), and `research/timing/results/` was computed
  from it. **The raw files are not on the remote branch.** `git push` is denied by the repo's
  settings, and the researcher chose to push through the GitHub API without the data.
- To regenerate, run `python3 research/timing/fetch.py`. Coinbase, Kraken and OKX will include
  days after 2026-09-25. `run.py` stops the analysis at 2026-09-24, so results are reproducible
  up to exchange-side revisions of past candles.
- Binance's API (451) and Bybit (403) are geo-blocked from this environment, so Binance data
  comes from `data.binance.vision`. See PREREGISTRATION amendment A6.

**Status 2026-09-25 (later, F5):**
- Added Coinbase and Binance-archive daily bars for F4's full 19-asset universe
  (`research/voi/crosscheck.py --fetch`). Coinbase has no TRX-USD (404, logged).
- The raw directory is now ~6 MB and is committed so F5 is reproducible.
