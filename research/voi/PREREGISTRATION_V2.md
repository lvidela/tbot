# Pre-registration — V2: cross-exchange check of F4's nuisance parameters, and VOI rerun (open-ended)

**Date:** 2026-09-25 · **Author:** Research Agent (cloud session) · **Branch:** `research/voi-crosscheck`
**Status:** committed before any cross-exchange statistic is computed. The Coinbase and Binance
daily files for LINK/BTC/ETH/SOL were downloaded in this session by `research/timing/fetch.py`
and have not been analysed. No other asset has been downloaded yet.

## Why

F4 (`research/findings/2026-09-25_voi_screen.md`) estimated its V1b nuisance parameters from one
exchange: Kraken public daily OHLC (`research/tsmom/ohlc_long.json`, 720 bars, 2024-10-05 →
2026-09-24, 19 non-LINK assets):
- σ_x = 5.79%. This is the sd of an asset's 3-day log return minus LINK's.
- ρ = 0.369. This is the mean pairwise cross-asset correlation of those excess returns.
- LINK daily sd = 4.54%.

These parameters drive C9 (forward ledgers) and the V1b timetable. The researcher has now set the
horizon to **open-ended**. This study checks whether a second and third venue give the same values,
and whether any candidate becomes MEANINGFUL under the open-ended horizon.

## Horizon handling (fixed now)

- **Primary: H365**, F4's pre-registered stand-in for "open-ended". Every step-2 decision below is
  taken at H365.
- **Sensitivity only: H730.** It is reported, but it cannot trigger a study on its own. Most EVSIs
  here scale roughly linearly with horizon, so an unbounded horizon would make any positive EVSI
  "meaningful" and the screen would be vacuous.
- The H20 column is still computed for continuity with F4. It is not a decision input.

## Data (fixed now)

- **Coinbase Exchange** (USD pairs) and **Binance spot** (USDT pairs, via `data.binance.vision`;
  the API is geo-blocked, PREREGISTRATION amendment A6). Both are fetched by the existing
  `fetch.py` functions, and every file is stored with its provenance header.
  - Binance excess returns are LINKUSDT-relative, so the USDT/USD basis cancels.
- **Asset set:** the same 19 non-LINK assets as F4. Symbol mapping: XBT→BTC, XDG→DOGE, and
  otherwise the same ticker.
  - An asset absent from a venue, or lacking full coverage of the window, is dropped for that
    venue and listed.
- **Kraken** is F4's file, unchanged.

## Estimands and method (identical to F4's `ledger_params`)

- The method is F4's: 3-day non-overlapping windows, the median over the 3 phases, and ρ as the
  mean off-diagonal correlation.
- Bars are labelled by UTC open date. Only complete bars are used, and all venues are aligned to
  common timestamps.

| id | comparison | window | assets |
|---|---|---|---|
| **P1 (primary)** | Kraken vs Coinbase vs Binance | F4's window, 2024-10-05 → 2026-09-24 | the **matched set**: assets present on all three venues |
| P2 | each venue, own full set | F4's window | every asset available on that venue |
| P3 (regime check) | Coinbase and Binance | long window, 2021-01-01 → 2026-09-24 | assets with full coverage of that window on the venue |

P3 exists because V1b is a statement about the *future*. A 2-year window may not represent it,
and the long window includes the 2022 bear market.

## Materiality rules (fixed now)

**Parameter disagreement.** In P1, a venue disagrees materially with Kraken if either condition
holds:
- its σ_x differs by more than 20% relative;
- its ρ differs by more than 0.10 absolute.

This is a descriptive flag. The decision rule is the rerun below.

**VOI rerun.**
- **Parameters left at F4's values:** every fixed input (A = $58.62, c₁ = 0.46%, RT4 = 1.83%,
  notional = $13) and every scenario value.
- **Parameters that are swapped:** the nuisance parameters (σ_x, ρ) are replaced in turn by:
  - (a) each venue's P1 values;
  - (b) the **across-venue median** of P1. This is the decision set;
  - (c) the P3 long-window values, as a sensitivity check.
- LINK daily sd does not enter any EVSI (C1 uses a fixed 4%). It is reported only, compared
  against F3's 3.3–5.4%.
- **Code:** `voi_screen.py` is imported unchanged; it is not edited, because it is F4's record.
  A new script passes the alternative parameters and horizons.

**Step-2 trigger.** A new pre-registered study is started only if some candidate reaches central
EVSI ≥ $0.25 at H365 under **(b), the across-venue median**.
- MEANINGFUL under one venue's parameters only, or only at H730, or only in P3 → labelled
  REQUIRES VALIDATION, and no study is started.
- Otherwise the result is reported plainly as "nothing is MEANINGFUL".

**Known in advance:** only C9, and the V1b timetable, depend on σ_x and ρ. C1–C8 will reproduce
F4 exactly at H20/H365. This is stated now so that it is not mistaken for a finding.

## Tests

- The existing `test_voi.py` must stay 7/7.
- New tests will check:
  - the multi-venue loader aligns timestamps and drops the partial last bar;
  - `ledger_params` on a matched set is invariant to asset order;
  - the rerun reproduces F4's `voi.json` exactly when it is given Kraken's parameters.
