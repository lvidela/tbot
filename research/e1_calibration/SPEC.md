# E1 — live maker-execution calibration: frozen evaluation spec (research side)

**Date:** 2026-09-26 · **Author:** Research Agent (cloud) · **Status:** frozen before any live E1 order.
- **Proposal:** `research/findings/2026-09-26_exploration_proposals.md`.
- **Research decision (DECISIONS.md D-4):** GO. Execution belongs to the live agent, because
  research never places trades.

## Change from the proposal (decided, with reason)
- **Pairs:** **LINKUSD, XBTUSD, XRPUSD** instead of the USDT pairs.
- **Reason:** all three are in P3's virtual sampler, so each live order can be paired with P3's
  virtual orders on the **same order book**. That is the whole point of the calibration. ETH is
  dropped because it isn't sampled by P3.
- **Cost:** converting ~$10 of the new USDT to USD costs ~0.40% ≈ $0.04, once. That's cheaper than
  an inexact calibration.

## What the live agent needs to do so research can evaluate
1. **Tag** every E1 order in `data/execution_log.json` with `"experiment": "E1"`. The existing
   fields are sufficient: `ts`, `pair`, `side`, `post_only`, `status`, `vol_exec`, `cost`,
   `latency_sec`, `regime`, `vol_ratio`.
2. **Log canceled or unfilled attempts too,** with `status: "canceled"`. Without them the fill
   rate cannot be computed.
3. **Mirror `data/execution_log.json` to main.** Research reconstructs markouts itself from Kraken
   public Trades, so no new live fields are needed.

## Protocol (from the proposal; unchanged except the pairs)
- **Order size:** minimum clips (LINK 0.55 ≈ $7.9, XBT 0.00005 ≈ $4.2, XRP 1.65 ≈ $2.6).
- **Buy leg:** post-only BUY at the best bid, cancelled at 30 min, never crossing.
- **Sell leg:** on a fill, post-only SELL at the best ask, re-posted every 15 min for up to 24 h,
  never crossing.
- **Schedule:** Poisson, about 1 attempt per pair per day, plus an immediate attempt (max 1/day)
  when the pair turns *volatile*.
- **Stops:** hard stop at −$5 cumulative realised cost; at most one open inventory per pair;
  within the ≤ 10% sleeve.

## Evaluation (`analyze_e1.py`, sha256 `08addafd61ff07e616b359602ed8309b1522742fcd378fb9cfd792c1efac7927`)
Per regime:
- the live 5-min fill rate, with a Clopper–Pearson 95% CI;
- the paired P3 bracket: the mean strict and touch 5-min fill rates of P3 virtual orders on the
  same pair and side within ±2 h, after the gap filter;
- the live 5-min markout, from public trades, vs P3's paired strict markout.

**Decision rules:**
- **(H-a) CALIBRATED** if the live fill CI overlaps the P3 [strict, touch] bracket. Evaluated
  once there are ≥ 30 calm E1 orders, ≥ 10 of them LINK.
  - **If calibrated:** live calibration stops and P3's virtual sampler is used from then on.
  - **If not:** the measured bias (live − P3 midpoint) becomes a correction applied to all
    virtual results.
- **(H-b)** Evaluated at ≥ 10 volatile-regime E1 orders. The report gives the volatile fill
  probability and markout with CIs. These replace `edge.py`'s volatile prior of 0.50; the live
  agent decides the wiring.
- **Stop reporting** at the budget stop or 6 weeks after the first E1 order, whichever comes
  first. Report the n reached, with CIs.
- **Trial ledger:** one row per resolved hypothesis, stage `live-calibration`.
