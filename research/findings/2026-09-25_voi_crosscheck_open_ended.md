# Finding: F4's parameters replicate on Coinbase and Binance; nothing is MEANINGFUL under the open-ended horizon

**Date:** 2026-09-25 · **Author:** Research Agent (cloud session) · **Branch:** `research/voi-crosscheck`
**Label: NEGATIVE** (no candidate reaches EVSI ≥ $0.25 at H365 under the decision parameter set,
so no new study is started). The H730 sensitivity is labelled **REQUIRES VALIDATION**: C6 and C9
cross $0.25 there, but that horizon cannot trigger a study.
Does not edit F4; F4 stands as recorded.

## Question
F4 estimated its forward-ledger nuisance parameters from one exchange (Kraken), and left the
horizon ambiguous. The researcher has now fixed the horizon as **open-ended**. This finding asks
two questions:
1. Do σ_x, ρ and LINK's daily sd replicate on a second and a third venue?
2. Does any candidate become MEANINGFUL under the open-ended horizon?

## Hypothesis (pre-registered)
`research/voi/PREREGISTRATION_V2.md` was committed (`1a619c7`) and pushed before any
cross-venue statistic was computed. Fixed in advance:
- **Horizons:** H365 is primary (F4's stand-in for open-ended). H730 is a sensitivity check that
  cannot trigger a study.
- **Material disagreement:** |Δσ_x| > 20% relative or |Δρ| > 0.10.
- **Step-2 trigger:** a new study starts only if some candidate reaches central EVSI ≥ $0.25 at
  H365 under the across-venue median parameters.
- **Stated beforehand:** only C9 depends on these parameters.

## Data sources / period / timestamps
- **Kraken:** F4's file `research/tsmom/ohlc_long.json` (key `1440`), unchanged.
- **Coinbase Exchange** (USD) and the **Binance spot archive** (`data.binance.vision`, USDT; the
  API is geo-blocked, A6).
  - Fetched 2026-09-25 ~21:35–22:07Z by `research/timing/fetch.py` and
    `research/voi/crosscheck.py --fetch`.
  - Every file carries a provenance header (URL, `fetched_at`, row count), and every attempt is
    in `research/data/raw/_fetch_log.jsonl`.
- **Missing:** Coinbase has no TRX-USD (HTTP 404, logged).
- **Windows:**
  - F4's window: 2024-10-05 → 2026-09-24, 720 bars.
  - Long window: 2021-01-01 → 2026-09-24, 2,093 bars.
  - Bars are aligned on exact UTC open timestamps. No forward filling: an asset with any gap is
    dropped for that window.
- **Unauthenticated public endpoints only.** No credentials were read or used.

## Methodology
- **Estimator:** F4's own (`voi_screen.ledger_params`), applied to aligned matrices.
  - Non-overlapping 3-day windows, median over the 3 phases, σ_x = sd of (asset − LINK) 3-day
    log return, ρ = mean pairwise correlation of those excess returns.
  - A test proves it reproduces F4's Kraken numbers to 1e-12.
- **Comparisons:**
  - **P1:** matched 18-asset set on all three venues, F4's window.
  - **P2:** each venue's full set, F4's window.
  - **P3:** Coinbase and Binance, long window.
- **VOI rerun:** `voi_screen.py` is imported unchanged. A test proves the rerun reproduces F4's
  `voi.json` exactly given F4's parameters.
- **Reproduce:**
  - Run: `python3 research/voi/crosscheck.py` → `research/voi/results/crosscheck_v2.json`.
  - Tests: `python3 research/voi/test_crosscheck.py` (6/6) and `test_voi.py` (7/7).

## Results

### 1. Nuisance parameters

| set | venue | assets | σ_x (3d) | ρ | LINK daily sd |
|---|---|---|---|---|---|
| F4 | Kraken | 19 | 5.79% | 0.369 | 4.54% |
| **P1 matched** | Kraken | 18 | 5.70% | 0.368 | 4.54% |
| **P1 matched** | Coinbase | 18 | 5.71% (+0.2%) | 0.368 (+0.000) | 4.55% |
| **P1 matched** | Binance | 18 | 5.71% (+0.2%) | 0.367 (−0.002) | 4.54% |
| P2 | Coinbase / Binance (own sets) | 18 / 19 | 5.71% / 5.80% | 0.368 / 0.367 | — |
| **P3 long** | Coinbase | 12 | **6.76%** | 0.398 | 5.15% |
| **P3 long** | Binance | 19 | **7.08%** | 0.385 | 5.15% |

- **P1 (same window):** no venue disagrees materially. The largest gap is 0.2% relative in σ_x.
  F4's single-exchange estimate was not a data artefact.
- **What agreement does not show:** that the 2024–26 window is representative of the future.
  Venues are arbitrage-linked, so they *should* agree on the same window.
- **P3 (regime check):** the long window, which includes the 2021–22 cycle, gives a σ_x 17–22%
  higher and a ρ up to +0.03. This is the only material shift found.
  - It moves V1b in the *unfavourable* direction for the ledgers.
- LINK daily sd, 4.5% (2-year) and 5.2% (long), sits inside F3's 3.3–5.4%.

### 2. VOI rerun (central EVSI, USD)

| candidate | H20 | **H365 (primary)** | H730 (sensitivity) |
|---|---|---|---|
| C1 LINK vs USD | 0.000 | 0.000 | 0.000 |
| C2 other asset | 0.000 | 0.000 | 0.000 |
| C3 new tactical signal | 0.004 | 0.066 MARGINAL | 0.131 MARGINAL |
| C4 volatile fills | 0.000 | 0.000 | 0.000 |
| C5 switch execution | 0.003 | 0.009 | 0.009 |
| C6 LINK tail monitoring | 0.009 | 0.158 MARGINAL | **0.317** |
| C7 partial exposure | 0 | 0 | 0 |
| C8 derivatives | 0 | 0 | 0 (not actionable: Hard Rule 2) |
| C9 forward ledgers (median params) | 0.001 | **0.172 MARGINAL** | **0.568** |
| C9 with P3 long-window params | 0.001 | 0.119–0.126 | 0.417–0.443 |

C1–C8 match F4 exactly, as expected, since they do not use these parameters. C9 at H365 moves
from $0.168 to $0.172. No label changes.

### 3. Forward-ledger timetable (V1b), decision parameters vs long-window parameters

| picks/scan m | MDE at 365 d | days to MDE ≤ 1.83% | days to MDE ≤ 1.0% (net-edge test) |
|---|---|---|---|
| 1 | 1.45% (P3: 1.72–1.80%) | 229 (P3: 321–352) | 767 (P3: 1,074–1,178) |
| 3 | 1.10% (P3: 1.33–1.38%) | 133 (P3: 192–208) | 444 (P3: 643–695) |
| 10 | 0.95% (P3: 1.16–1.20%) | 99 (P3: 147–157) | 331 (P3: 492–526) |

If the next year looks like 2021–26 rather than 2024–26, every ledger milestone arrives
**~40–55% later** than F4 stated.

## Comparison vs hold-LINK and hold-USD
This study is not a strategy and makes no return comparison.
- It leaves F4's conclusion intact: hold-LINK vs hold-USD (C1) and LINK vs another asset (C2) keep
  large EVPI, and no feasible data can raise their EVSI above $0.
- Nothing here is evidence that LINK beats USD or BTC.
- No timing rule was tested, so the static-exposure control requested for S2 does not arise. It
  remains committed for any future S2 study.

## Robustness
- **Across venues:** Δσ_x ≤ 0.2%, Δρ ≤ 0.002.
- **Across windows:** σ_x +17–22% in the long window, which lowers C9's value (it stays MARGINAL
  at H365).
- **Across phases:** the per-phase ranges are stored in the JSON, and are as tight as in F4.
- **Across asset sets:** dropping TRX moves σ_x 5.79% → 5.70%. Coinbase's long window keeps only
  12 assets, yet agrees with Binance's 19 to within 5%.

## Limitations
- The EVSI scenario inputs (π, e, tail rates) are judgements carried over from F4. Replicating the
  nuisance parameters does not validate them.
- H365 and H730 are stand-ins for "open-ended". The step-2 rule is anchored at H365 by
  pre-registration.
- **Most EVSIs grow ~linearly with horizon.** A long enough horizon makes almost any positive
  candidate "meaningful". That is why H730 cannot trigger a study.
- The fee tier, account size ($58.62, F4's fixed input) and objective are unchanged. EVSI scales
  linearly with account size.
- As in F4, V1b ignores multiplicity across ledger strategies and uses a normal MDE on
  fat-tailed returns. Both flatter the ledgers.

## Conclusion
- **Nothing is MEANINGFUL under the open-ended horizon at the pre-registered H365, so no new cloud
  study is started.**
- F4's Kraken parameters replicate on Coinbase and Binance almost exactly.
- The one material change comes from the calendar window, not the venue: a longer history implies
  noisier excess returns and a slower ledger timetable.
- At H730, C6 (tail monitoring) and C9 (forward ledgers) cross $0.25. Both are live-system tasks
  that accrue at no research cost, not cloud studies.
- F4's rule stands: re-screen only if the horizon, the fee tier, the account size (~10×),
  Hard Rule 2 or the objective changes.

## What the Live Agent should independently validate
1. **Plan ledger milestones on the slower timetable.** If a ledger result is to be cited, use the
   long-window row (e.g. m = 3: ~200 days to MDE ≤ 1.83%, ~650–700 days to separate a +1% net
   edge). Once ≥10 decision times ≥72h apart have closed, recompute σ_x from the ledger's own
   72h outcomes.
2. **C6 is the cheapest positive-value item and needs no statistics.** Confirm that a check
   exists for LINK-specific non-price events: a Kraken LINK delisting or maintenance notice, a
   minimum-order or precision change on LINKUSD, and a deposit/withdraw status change. Its
   central value reaches ~$0.16 at one year and ~$0.32 at two.
3. **Keep the ledgers running and counting correctly** (C9). Count decision times ≥72h apart,
   not records, and measure excess vs LINK (D8), not absolute return.
4. **Re-trigger this screen if the account grows or fees fall.** If the tactical notional
   (F4's fixed $13) grows ~1.5× (e.g. with the account, to ~$85), C9 reaches $0.25 at H365 under
   the decision parameters, since C9's EVSI is linear in notional. This is arithmetic, not a forecast.
5. **Nothing here recommends a trade.** HOLD LINK remains the zero-cost default under
   uncertainty. That is not evidence it is optimal.
