# Finding: no remaining research question is worth running before 2026-10-15; the forward ledgers cannot validate a tactical edge within a year

**Date:** 2026-09-25 · **Author:** Research Agent (cloud session) · **Branch:** `research/voi-screen`
**Label: NEGATIVE** for research value at the 2026-10-15 horizon: every candidate is under
$0.05 EVSI (central), and none reaches $0.25 even in its high scenario. **INCONCLUSIVE** under an
open-ended horizon: three candidates are MARGINAL and none is MEANINGFUL.

## Question
The live decision is about final net USD on a ~$59 account. Which remaining research question
has enough expected value of information (EVSI) to be worth a study? And how long until the
forward shadow/counterfactual ledgers can detect an edge? REGISTRY's horizon amendment lists that
second question as a live task.

## Hypothesis (pre-registered)
Nothing was stated as expected. The classification rule was fixed in advance:
- NEGLIGIBLE: EVSI < $0.05.
- MARGINAL: $0.05 to $0.25.
- MEANINGFUL: EVSI ≥ $0.25.

Horizons:
- **H20:** 20 days to 2026-10-15. This is the end date in CLAUDE.md §1 and in the research brief.
- **H365:** 365 days. STATE.md records the experiment as open-ended, so one year is used as a
  sensitivity bound.

Commits, in order:
- `research/voi/PREREGISTRATION.md` was committed first (`42c1a7d`).
- The code with its scenario values fixed came next, before any run.
- The one post-run addition is labelled "supplementary, not pre-registered" below and in the code.

## Data sources / period / timestamps
- **No new market data.** At 2026-09-25 ~19:58Z the environment's network policy refused every
  host with a proxy 403: api.kraken.com, api.exchange.coinbase.com, api.binance.com,
  fapi.binance.com, data.binance.vision, www.okx.com, api.bybit.com and www.deribit.com. This is
  broader than the known 451/403 geo-blocks. `research/data/raw/` is empty in this checkout, so T1
  cannot be regenerated here. `test_timing.py` passes 11/11 on the committed code.
- **V1a inputs:** repo records only. Account $58.62 (STATE.md, 13:55Z). Costs from REGISTRY A1:
  0.46%/maker leg including adverse selection, 1.83% for a 4-leg round trip. Scenario ranges are
  stated in `voi_screen.py`.
- **V1b nuisance parameters:** Kraken public daily OHLC in `research/tsmom/ohlc_long.json`, key
  `1440`. It covers 720 complete bars, 2024-10-05 → 2026-09-24, for 20 assets; the partial
  2026-09-25 bar is dropped. This is one exchange, which is acceptable for a nuisance parameter
  but not for an effect test.
  - Cross-check: LINK daily sd is 4.54% in this file, inside F3's Coinbase range of 3.3% (last
    90 days) to 5.4% (full sample).

## Methodology
- **V1a:** each candidate is modelled as a decision.
  - EVPI (perfect knowledge of the estimand) bounds every possible study.
  - EVSI is for the best study feasible now. It uses a normal preposterior closed form, the same
    one as `timing/evsi.py`, or a stated expected-gain model for candidates that are not a single
    switch (C3, C4, C6, C9).
  - Three scenarios (low, central, high value of information) are run at both horizons.
- **V1b:** the unit of observation is one decision time, i.e. all records from one scan; its value
  is the cluster-mean 72h excess vs LINK. Only clusters ≥72h apart count as independent, so
  n = T/3 after T days.
  - Cluster variance: Var = σ_x²(ρ + (1−ρ)/m).
  - MDE = 2.80·√Var/√n. This is a single test with no multiplicity charge, which flatters the
    ledgers.
- Reproduce: `python3 research/voi/voi_screen.py`. Tests: `python3 research/voi/test_voi.py`
  (7/7). The tests cover a Monte Carlo check of the closed form, EVSI ≤ EVPI for every cell, and
  recovery of a planted ρ and σ.

## Results

### V1a: USD value of information (EVPI / EVSI), from `results/voi.json`

| candidate | H20 central | H20 high | H365 central | H365 high | label (central, H20 / H365) |
|---|---|---|---|---|---|
| C1 LINK vs USD, drift/timing re-run | $0.20 / **$0.00** | $0.86 / $0.00 | $4.95 / **$0.00** | $17.86 / $0.28 | NEGLIGIBLE / NEGLIGIBLE |
| C2 hold BTC/ETH instead | $0.07 / **$0.00** | $0.23 / $0.00 | $4.41 / **$0.00** | $7.92 / $0.00 | NEGLIGIBLE / NEGLIGIBLE |
| C3 new tactical signal search | $0.04 / $0.00 | $0.26 / $0.16 | $0.79 / $0.07 | $4.75 / $2.89 | NEGLIGIBLE / MARGINAL |
| C4 maker fills in volatile regimes | $0.09 / $0.00 | $0.35 / $0.00 | $1.58 / $0.00 | $6.33 / $0.00 | NEGLIGIBLE / NEGLIGIBLE (not feasible in cloud) |
| C5 switch execution timing | $0.01 / $0.00 | $0.04 / $0.02 | $0.02 / $0.01 | $0.11 / $0.05 | NEGLIGIBLE / NEGLIGIBLE |
| C6 LINK tail-event monitoring | $0.06 / $0.01 | $0.15 / $0.05 | $1.06 / $0.16 | $2.81 / $0.84 | NEGLIGIBLE / MARGINAL |
| C7 partial exposure | $0 / $0 | $0 / $0 | $0 / $0 | $0 / $0 | zero by linearity of the objective |
| C8 derivatives / hedging | $0 / $0 | $0 / $0 | $0 / $0 | $0 / $0 | not actionable (Hard Rule 2) |
| C9 forward ledgers | $0.02 / $0.00 | $0.13 / $0.02 | $0.40 / $0.17 | $2.37 / $2.33 | NEGLIGIBLE / MARGINAL |

C3 has a *negative* EVSI in its low scenario (−$0.01 at H20, −$0.11 at H365). A backtest that
admits false positives at MDE 7.5% costs more in fees than it earns.

### V1b: forward-ledger detectability
Estimated from the Kraken data:
- σ_x, the sd of an alt's 3-day log return minus LINK's, is **5.79%**. Across phases it ranges
  5.62–6.08%.
- ρ, the cross-alt correlation of those excess returns, is **0.369**, with a range of 0.34–0.38.

| picks per decision time m | MDE at 20 d | 60 d | 180 d | 365 d | days to MDE ≤ 1.83% (pre-reg.) | days to ≤ 2.83% (pre-reg.) | days to ≤ 1.0% (suppl.) | days to ≤ 0.5% (suppl.) |
|---|---|---|---|---|---|---|---|---|
| 1 | 6.3% | 3.6% | 2.1% | 1.5% | 236 | 99 | 789 | 3,156 |
| 3 | 4.8% | 2.8% | 1.6% | 1.1% | 137 | 57 | 457 | 1,829 |
| 10 | 4.1% | 2.4% | 1.4% | 1.0% | 102 | 43 | 341 | 1,365 |

How to read it:
- The pre-registered targets test against *zero gross* edge.
- Acting needs the *net* edge separated from zero. That is the supplementary column, added after
  the first run.
- ρ = 0.37 caps the benefit of more picks per scan. Beyond ~5 picks, the floor is
  σ_x·√ρ ≈ 3.5% per cluster.

Descriptive check: the 19 open shadow records show an excess sd of 3.3%, but they are still
under 72h old and come from 4 scan hours. That is consistent with the modelled 5.8% at full
horizon. It is not evidence either way.

## Comparison vs hold-LINK and hold-USD
This study is not a strategy, so it has no return comparison of its own. Its relevance to both
benchmarks:
- The only large quantities are EVPI of the exposure decisions: C1 (LINK vs USD) and C2 (LINK vs
  another asset), $4–5 central at H365.
- **No feasible study can reach that value.** The existing history was used by T1 and R13, and
  drift SE depends on calendar span, not on sampling frequency. EVSI is $0.00 for both.
- Hold-LINK vs hold-USD therefore remains a choice made under irreducible uncertainty. It is not
  a question research can answer in this experiment.

## Robustness
- **H20 conclusion:** it holds in all three scenarios. The highest H20 EVSI is $0.16, for C3 in
  its high scenario (π = 15% prior that a new signal is real, 2% net edge, 2.5% MDE). That prior
  is generous given 13 rejections.
- **σ_x and ρ:** stable across the three phases (±4% and ±6% relative).
- **C1 under H365:** C1's high-scenario EVSI of $0.28 comes from ~1 new day of data scaled over a
  year with a 50%/yr prior sd. It is not a study anyone can run now.

## Limitations
- The scenario values for π, the tail-event rate, fill misestimation and similar inputs are
  judgements, not estimates. That is why three scenarios are reported and the H20 conclusion is
  checked in all of them.
- **Direction of bias:**
  - V1a ignores a study's own cost and the chance that the live agent never acts on it. Both push
    EVSI down, so the NEGLIGIBLE labels are conservative.
  - V1b ignores multiple testing across strategies in the ledgers. That flatters the ledgers.
- V1b assumes 72h outcomes and the current alt universe. Excess returns are fat-tailed, so the
  normal MDE is optimistic.
- The horizon is ambiguous across repo records (H20 vs open-ended). Both are reported, and the
  researchers should settle which applies.

## Conclusion
- **At the 2026-10-15 horizon, no research question has meaningful value of information.** Every
  candidate is NEGLIGIBLE in the central scenario and at most MARGINAL in the high one. Timing
  (C1), asset choice (C2) and partial exposure (C7) are dead ends: data (C1, C2) or the objective's
  linearity (C7) caps their value. That is not the same as the answer being known.
- **Under an open-ended horizon,** three candidates are MARGINAL, and none of them is a cloud
  research task:
  - C9, forward ledgers: accrues free in the live system.
  - C6, tail monitoring: a live monitoring task.
  - C3, a new signal search: $0.07 central, and it only pays if the prior that a new signal is
    real is generous.
- **The forward ledgers cannot validate a tactical edge within a year.** Separating a +1% net
  edge from zero needs ~340–790 days of scans spaced ≥72h apart. Even the weaker test (a gross
  edge equal to cost vs zero) needs 100–240 days. Twenty days gives an MDE of 4–6%.

## What the Live Agent should independently validate
1. **Recompute σ_x and ρ from live 72h shadow outcomes** once ≥10 decision times ≥72h apart have
   closed, and rerun `voi_screen.py`'s `days_to()` with them. If σ_x is well below 5.8%, V1b's
   timetable shortens proportionally in sd, or quadratically in days.
2. **Count ledger evidence in decision times ≥72h apart, not records.** No ledger result should be
   cited as validation before MDE ≤ the claimed net edge (see the table).
3. **Check which horizon is authoritative:** CLAUDE.md §1 and the research brief say 2026-10-15,
   STATE.md says open-ended. The labels above flip from NEGATIVE to MARGINAL-at-best depending on
   it.
4. **C6 needs no statistics:** confirm that a cheap check exists for LINK-specific non-price events
   (a Kraken delisting or maintenance notice for LINK, a LINK minimum-order change). Its value is
   small but positive under an open-ended horizon.
5. Nothing here recommends a trade or a change of position. HOLD LINK stays the zero-cost default
   under uncertainty. **This does not show that LINK beats USD or BTC.**

## Recommended next step
Do not open a new cloud research study for this experiment unless one of these happens:
- the horizon is extended *and* the researchers want the MARGINAL C3 search anyway;
- the fee tier changes materially, which rescales every tactical EVSI;
- the account grows by ~10× or more, since every EVSI here scales linearly with account size;
- a researcher rule change makes derivatives actionable (C8 would then need its own screen);
- the objective changes from expected to median USD, which reopens C7 and the variance-drag
  argument of R13.
