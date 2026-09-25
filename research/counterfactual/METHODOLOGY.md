# Counterfactual P&L Ledger — methodology

**Purpose:** determine whether the opportunities the live gate rejects would actually have
made or lost money. Observational forward-validation only.

**Status: data collection. No conclusions are available or claimed yet.**

---

## Why this dataset is uncontaminated

Every backtest in this repository shares one defect: the model that chose the thresholds also
evaluated them. Five results have collapsed under correction as a result (registry R1, R2, R6,
R9, R10).

This ledger avoids that **structurally, not by discipline**:

1. The decision-time snapshot — bid, ask, spread, signals, confluence, rejection reason — is
   written at the **instant of rejection**.
2. Each horizon is resolved **later**, when the wall clock reaches it, from a fresh quote.
3. At write time the future does not exist. At resolve time the entry is already frozen.

**No code path can consult a future price to set an entry.** `test_counterfactual.py` asserts
this by inspecting the source: `record_rejection` never touches a horizon field, and
`resolve_due` never rewrites an entry price or a decision quote.

## Execution economics

Identical to the live strategy's measured tier.

| assumption | value | rationale |
|---|---|---|
| Taker fee | 0.80% / leg | measured |
| Maker fee | 0.40% / leg | measured |
| Adverse selection | 5.4 bps / leg | measured on real fills |
| **Hypothetical entry (primary)** | **the ASK** | we would cross the spread to get in |
| Hypothetical exit | the BID | we cross back to get out |
| Maker variant | entry at bid, flagged `maker_fill_contingent` | reported but never primary |

**The primary figure assumes a taker entry deliberately.** A passive entry is not guaranteed to
fill, and assuming it does is precisely the optimistic-fill error this ledger exists to avoid.
The maker variant is recorded alongside so the cost difference is visible, explicitly flagged as
contingent on a fill we cannot assume.

A flat market therefore produces a **loss equal to costs** — the correct null.

## The four reported quantities

| | meaning |
|---|---|
| **A** `A_gross_move_pct` | mid-to-mid price movement. **Not executable.** Reported only for contrast. |
| **B** `B_executable_gross_pct` | entry at ask → exit at bid. Real prices, no fees. |
| **C** `C_net_after_fees_pct` | B minus both legs' fees. **The headline number.** |
| **D** `D_excess_vs_benchmark_pct` | C minus LINK's return over the *same* horizon. |

D is the one that matters: we already hold LINK, so the real question is not "would this trade
have profited" but "would it have beaten what we were already doing".

## Horizons

5m, 30m, 2h, 6h, 24h, 72h — each resolved independently against a fresh quote.

## Selection rule — fixed in advance

**Every** asset reaching confluence ≥ 2 is logged, whatever its rejection reason and whatever it
subsequently does. The threshold sits deliberately *below* the live gate's minimum of 3, so the
ledger captures exactly the setups the gate turns away. Losers are recorded identically to
winners. There is no post-hoc filtering anywhere in the write path.

## Clustering

Multiple signals on one asset within 30 minutes share an `opportunity_id`. **Raw rows are always
preserved** — nothing is merged away — but the id allows cluster-level analysis so that one
underlying opportunity firing five detectors is not counted as five independent observations.
`report()` prints both a raw CI and a cluster-de-correlated CI.

## Statistical rules

- 95% confidence intervals on every mean.
- Cluster-level CI reported alongside the raw one.
- Horizons **overlap** across rows and are serially correlated, so any t-statistic computed on
  raw rows is inflated (registry D7). The report says so on every run.
- Sample size printed for every statistic.
- **A positive point estimate is never presented as alpha.**

## Two prohibitions

1. **This dataset must not be used to fit gate thresholds.** Doing so would recreate exactly the
   contamination it exists to avoid. It is observational, not a parameter search.
2. **It cannot authorise a trade.** `counterfactual.py` does not import `execute.py`, and
   `execute.py` does not import `counterfactual.py`. Both directions are asserted by tests.

## What would make this actionable

Roughly **30+ distinct opportunity clusters** resolved at the 24h and 72h horizons, with a
cluster-level CI excluding zero. Below that, the honest statement is "insufficient data", and
that is what the report will print.
