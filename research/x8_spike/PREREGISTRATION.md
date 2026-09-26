# Pre-registration — X8: conditional reversal after LINK hourly up-spikes (2-leg exit and re-entry)

**Date:** 2026-09-26 · **Author:** Research Agent (cloud) · **Branch:** `research/x8-link-spike-reversal`
**Origin:** the live agent's proposal A1 (`research/findings/2026-09-26_broadened_alpha_program.md`).
**Status:** committed before any hourly LINK data is downloaded or examined.

## C1 prior-exposure disclosure
- **Seen before this:**
  - R4: unconditional LINK lag-1 autocorrelation at 1h, t = −1.32. A mild, non-significant
    reversal sign.
  - T1 S4: daily LINK-crash state.
  - X3: daily market capitulation. Inconclusive; tactical rotation negative.
  - The live agent's A1 proposal and its 6-hour rejected-opportunity review.
- **Not seen:** I have not examined LINK hourly data.
- **Knowledge cutoff:** 2026-06. The 2019–2026-06 price path may be in training data, so all
  pre-cutoff results are *discovery / reused* evidence only (C2). Confirmation can only come from
  a forward FROZEN-2 entrant.

## C3 code hash
`evaluate.py` sha256 `51d83671822a223eaab8054ac7d39ba4f1840a910fa364b49def3d051469047c`.

## Hypothesis and mechanism
**H8:** after LINK rises unusually fast within one hour, it partly gives the move back over the
next hours by more than the 0.92% cost of selling to USD and buying back.

**Mechanism:** a liquidity-driven overshoot. A market buy sweep or short squeeze temporarily
pushes the price past what informed flow supports, and liquidity providers get paid for the
reversal.

**Why only UP spikes:** the live account is 100% LINK. The actionable trade is
LINK → USD → LINK after an up-spike. After a down-spike there is nothing to buy with, so down
events are not tested.

## Definitions (no look-ahead)
- **Hour boundary T:** the close of the bar opened at T−1h.
- **Event:** r = log close(T)/close(T−1h) ≥ k·σ, where σ is the sd of the 168 hourly returns
  ending at T−1h. The event hour is excluded from σ.
- **Non-overlap:** after an event, the next can start only at T + h.
- **Trade:** sell LINK at close(T), buy back at close(T+h).
- **Excess vs holding LINK:** −(close(T+h)/close(T) − 1) − 0.92%, i.e. 2 maker legs including
  adverse selection (A1).
- **Also reported:** the gross reversal, and the gross minus the unconditional −r over
  non-overlapping random h-hour windows (the drift cost of sitting in USD).

## Tests
Family of 6: k ∈ {2, 3} × h ∈ {1, 4, 24} hours.
- **Statistic:** mean **net** excess > 0, one-sided.
- **Primary cell:** k = 2, h = 4.
- **Evidence standard (audit C4):**
  - A cell counts as a discovery pass only if its one-sided p < 0.05 / (K_program + 6). At
    registration, K_program = 262, so the bar is p < 1.87×10⁻⁴.
  - **And** the same cell has the same sign on Coinbase LINK-USD hourly data.
- **Discovery:** 2019-07-01 → 2023-12-31 (Binance spot archive LINKUSDT 1h).
- **Reused / pre-cutoff window:** 2024-01-01 → 2026-06-30. Run once, after discovery is
  committed; per C2 it is *not independent confirmation*.
- **Post-cutoff window:** 2026-07-01 → 2026-09-24. Descriptive only (too small).
- **If some cell passes discovery:** freeze it as a FROZEN-2 forward entrant (new id, hashes,
  access log), with the static-exposure and random-exit-time nulls. That entrant is the only
  route to a POSITIVE label.
- **Otherwise:** NEGATIVE if the primary's point estimate is ≤ 0, INCONCLUSIVE if not. The MDE is
  always reported.

## Economics
Reported per cell:
- events per year;
- the mean net per event;
- the implied net per year;
- the hit rate.

An effect only matters if the net per year is material relative to the account's exposure.

## Known risks
- **Hourly-close execution is optimistic** for a spike hour. Maker exit fills during a spike are
  exactly P3's open question; P3's measured fill and markout will be applied if it completes
  first.
- **Correlated events** despite the non-overlap rule, e.g. several spikes in one volatile day.
- **Selection:** the idea came from the live agent after seeing live rejected-opportunity data.
  That data is short-horizon and cross-sectional, not LINK hourly.
