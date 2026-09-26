# Research Registry — permanent record

Append-only in spirit. **Disproven results stay disproven.** Anything listed under
REJECTED must not be quietly reused as evidence. Reconsidering one requires an explicit
entry stating what *new* evidence justifies it.

---

## REJECTED — do not reuse as evidence

### R1. Naive volatility-expansion edge (+2.40% / 3d, t=+4.96)
**Rejected 2026-09-24.** Two defects: forward windows overlap (pseudo-replication), and 32
correlated assets firing on the same day were counted as 32 independent observations.
After cross-sectional demeaning and date clustering: **+1.75%, t=+1.19, median −1.29%.**
*Never cite the +2.40% figure again.* Even the corrected +1.75% has a negative median.

### R2. Naive volume-spike edge (+1.79% / 3d, t=+3.41)
**Rejected 2026-09-24.** Same defects. Corrected: **−0.00%, t=−0.00, median −1.97%.** Zero edge.

### R3. Cross-sectional momentum rotation
**Rejected 2026-09-24.** Information coefficient ≈ 0 at all 12 lookback/horizon pairs
(|t| < 1.1). The 36-cell backtest grid had median 1.081 vs hold-LINK 1.456, only 11/36 cells
beating hold, and violently disagreeing adjacent cells — a noise field, not an edge surface.

### R4. LINK single-asset mean reversion
**Rejected 2026-09-24.** Lag-1 autocorrelation indistinguishable from zero (daily t=−0.55,
1h t=−1.32). The 4h reading (t=−2.31) fails Bonferroni for 3 tests and implies 0.079%/trade
against a ≥0.81% round trip.

### R5. "Maker execution costs 0.40%/leg everywhere"
**Rejected 2026-09-24.** Measured fills (n=2) were 100% filled at 0.400% — but both in CALM
conditions. `vol_expansion` fires at ≥2.5× the 30d vol while a regime is volatile at ≥1.5×, so
that signal *always* fires in a volatile regime **by construction**. Calm-market fill data can
never apply to it. Adverse selection also measured at **5.4 bps/leg**, not zero as I first claimed.

### R6. Confluence signal combinations as a tradeable edge
**Rejected 2026-09-24** (Q1, `research/Q1_signal_combinations.md`). 31 subsets × 3 horizons = 93
tests, cross-sectionally demeaned and date-clustered.

- **0 of 93 survive Bonferroni** (|t| ≥ 3.461 required; largest |t| anywhere is 2.40, and that
  cell's net is −0.34%).
- **Schedule-preserving permutation test (2,000 draws): family-wise p = 0.971.** Observed max
  |t| 2.404 vs null *median* max |t| 3.329. **Randomly selecting assets typically produces a
  better-looking best result than the real signals do.** This is stronger evidence than
  Bonferroni and it is damning.
- **Every top combination is driven by one asset-day: NILUSD, 2026-09-20.** I verified this
  independently from the cache — NILUSD went 0.0617 → 0.1261 in three days, **+104%**. Remove
  that single day and the best combination falls +5.86% → +1.72%, i.e. **net −0.11%**.
- **All top-3 medians are negative** (−0.50%, −1.21%, −2.09%). Two trades in three lose after costs.
- Out-of-sample shape is wrong: in-sample flat, the entire apparent result sits out-of-sample
  with |t| ≈ 1.0–1.2.

*Do not revive "confluence combinations" without materially new data.* Reconsideration requires
either a 4h history extending 12+ months (the momentum/rel_str subsets are confined to a 120-day
window with 10–26 clustered observations) or a cost structure low enough to change the arithmetic.

### R7. Confluence uplift and the confluence-slope in success probability
**Rejected 2026-09-24** (Q2). `expected_move` multiplied by `(1 + 0.15·(conf−3))` and
`success_probability = 0.50 + 0.03·conf`. Over **449 clustered days** realised P(positive 3d
demeaned return) is **0.486 / 0.488 / 0.507** at confluence 3/4/5 — flat, and indistinguishable
from the 0.476 unconditional baseline. The apparent gradient in the production sample rests on
27 and 14 clustered days with CIs of [0.38,0.74] and [0.42,0.89]. **The intercept 0.50 was right;
the slope was invented.** Both terms removed from `tactical.py`.

### R8. "Volatility drag" as a reason to prefer one holding over another
**Rejected 2026-09-24** (found by Q4). `STRATEGY.md` Test 3 priced LINK's 21-day drag at 1.46%
and used it to reject diversification — then justified holding LINK on a +0.117%/day in-sample
drift, the exact class of estimate rejected as noise elsewhere. **The error is double-counting:
realised returns already include volatility drag.** Subtracting it again as a separate term is
invalid. Test 3's drag arithmetic is void. Replaced by a direct empirical comparison
(`backtests/hold_vs_cash.py`), which is the correct method.

### R9. Cross-sectional REVERSAL (bottom-k), and the momentum result that looked significant
**Tested and not supported, 2026-09-24/25.** Q4 correctly flagged that 11 of 12 IC cells were
negative (a mild reversal signature) yet `rotation.py` only ever sorted descending — the
complement my own data pointed at had never been run. Ran it: 36 cells, cross-sectionally
demeaned and date-clustered.

**Reversal is not supported:** only 4 of 18 reversal cells have positive net, versus 10 of 18
momentum cells. Buying losers is worse than buying winners here.

**The momentum result that appeared to survive did not.** Five cells initially showed |t| > 3.3
with *positive* medians — the first thing all session to clear a Bonferroni-scale bar. It was an
artefact of **serial overlap**: at `fw=14` consecutive days share 13/14 of their forward window,
so ~212 date-clustered days are ~15 effective observations. Correcting by resampling every `fw`
days and averaging over all phase offsets:

| cell | t (overlapping) | **t (non-overlapping)** | n_eff | net |
|---|---|---|---|---|
| mom lb14 fw14 k3 | +4.35 | **+1.19** | 15 | +1.82% |
| mom lb30 fw14 k3 | +4.34 | **+1.29** | 14 | +2.21% |
| mom lb14 fw14 k1 | +3.33 | **+0.99** | 15 | +4.19% |
| mom lb14 fw7 k3 | +3.47 | **+1.32** | 31 | +0.75% |

Nothing above |t| = 1.32. **The point estimates stay positive (+0.75% to +4.19% net) — what
collapses is the confidence.** And since 36 cells were searched, selecting the best and quoting
its t is exactly the selection bias Bonferroni exists to catch; several |t| > 1 are expected by
chance alone.

**Honest status: cannot detect. Not "no edge".** Non-overlapping MDE at these horizons is
**2.5–4.4%**, so a true edge below that is invisible to this dataset.

### R10. Trailing-stop asymmetry as a substitute for directional edge
**Rejected 2026-09-25.** The session's most promising idea: since Kraken supports an
exchange-side trailing stop attached at entry, and Q2 measured MFE/MAE ≈ 2.33, an asymmetric
payoff might be +EV even at p = 0.50 — removing the need for a directional edge entirely.

Initial run looked good: trail 12% / 72h showed **net +3.68%, t = +3.28**. Three controls killed it:

- **C1 (decisive): the stop makes things WORSE in every cell.** Naked buy-and-hold of the same
  asset over the same window beats the trailing-stop version by **0.33 to 4.89 pp**. The stop
  exits on noise before recoveries. "Stop adds" is negative 6 times out of 6.
- **C2: random entry days beat the signal-filtered entries** (+1.43%, t=2.26 vs +0.88%, t=1.00).
  The setup filter contributes nothing.
- **C3:** the original basket was chosen using end-of-sample volatility — asset-selection
  look-ahead. Removed.

The apparent edge was **beta in a 30-day bullish sample**, which is what the earlier run's own
"12% trail barely binds" behaviour should have told me immediately: at a trail wide enough not to
bind, you are simply holding the asset.

*Do not revive trailing-stop-as-edge.* The trailing stop remains valuable as **risk control**
(bounding downside on a position taken for other reasons) — it is not a source of return.

### R11. Micro-arbitrage (triangular, stablecoin, spread capture, passive-fill reversion)
**Rejected 2026-09-25** — see `research/micro_arb/FINDINGS.md`. Measured with executable prices
only (ask to buy, bid to sell, never mid), one simultaneous snapshot plus a time series.

Four-level taxonomy on 702 real triangles: **21 theoretical → 9 executable (depth-checked) →
0 after fees → 0 repeatable.** Twelve of twenty-one evaporate on *depth alone*.

Every mechanism falls short of its fee hurdle: triangular **2.1–4.5×**, stablecoin **3.7×**,
spread capture **3.3–16.3×**, passive-fill reversion has the **wrong sign**.

**Structural cause:** microstructure edges live in the 1–10 bps band; we pay **40 bps/leg**
maker. The class sits below our fee floor. Kraken's 0 bps tier needs $10M/30d against our ~$75.

Most durable single fact: **152 of 618 USD pairs have spreads over the 80 bps hurdle, and zero
of them are liquid.** Wide spreads exist precisely where market-making is unprofitable — that is
equilibrium, not opportunity.

*Do not revive without a material fee-tier change, stated explicitly.*

---

## ACCEPTED / IN PRODUCTION

### A1. Execution cost structure (measured, live)
Taker **0.831%/leg** incl. spread crossing; maker **0.400%/leg** + ~5.4 bps adverse selection.
A tactical round trip is **4 legs ≈ 1.83%** at maker pricing on a ~$55 account.

### A2. Confluence requirement (v4.0) — **QUALIFIED 2026-09-24 by R6**
≥3 independent conditions; spread is a veto. Derived from R1/R2: single signals carry no edge.

**Qualification (important, and it undercuts my own design reasoning):** R6 shows confluence does
raise the *mean* — 3/4/5-condition subsets do sit at the top of the table — but it does so by
shrinking n to 10–26 fat-tailed days while **medians stay negative**. Confluence buys lottery
tickets, not edge. "Single signals carry no edge" remains true; my inference that *combinations
therefore do* was never established, and R6 refutes it. The confluence gate is retained as a
**risk filter** (it keeps us out of thin, spread-heavy, unconfirmed setups), **not** as an
established source of expected return. It must not be described as the latter anywhere.

**Structural problem this exposes for a $55 account:** the mean of these distributions is paid
for by roughly a 1-in-23 tail. You cannot size a tail at this account size — you must take all 23
trades and pay 23 × 1.83% of turnover to catch one NILUSD. Positive mean is not sufficient when
the account is too small to survive the sampling.

---

## HORIZON AMENDMENT — 2026-09-25 (researcher directive)

The experiment is now **open-ended**; the 2026-10-15 end date is withdrawn.

**No rejection here is reopened by this.** R1–R11 failed on cross-sectional demeaning, date
clustering, serial overlap, permutation testing and the fee floor — every one of those is
horizon-independent. A longer runway does not resurrect a signal that a permutation test scored
at family-wise **p = 0.971**.

**One ACCEPTED item is weakened.** A2's structural objection — "the mean is paid for by roughly a
1-in-23 tail; you cannot size a tail at this account size, you must take all 23 trades and pay
23 × 1.83% of turnover to catch one NILUSD" — was partly an argument about *insufficient time to
sample*. With no end date the sampling is feasible. The fee drag per trial is unchanged, so the
objection survives as an arithmetic point about cost, not as an impossibility.

**The substantive gain is power, not permission.** D5's standing rule (every null carries its
MDE) now cuts the other way: MDE falls as forward observations accumulate, and the shadow and
counterfactual ledgers accumulate indefinitely. R9's "cannot detect below 2.5–4.4%" is a
statement about n, and n is no longer bounded. Re-deriving MDE as a function of accumulated
observations is now a live research task — it tells a future session when the ledgers become
decisive instead of guessing.

**Standing rule, unchanged and now more important:** do not lower the gate because there is more
time. More time is a reason to *wait for evidence*, never a reason to trade on less of it.

---

## OPEN QUESTIONS (current research program, 2026-09-24 → 2026-09-26)

| # | Question | Why it matters |
|---|---|---|
| ~~Q1~~ | ~~Which combination produces positive net EV?~~ **ANSWERED: none. See R6.** | Closed 2026-09-24. Signal search is deprioritised; the binding constraint is cost (Q3). |
| Q2 | Is the expected-move model (0.5σ, p≤0.62) calibrated, or too conservative / too generous? | Sets the gate. Miscalibration either blocks good trades or admits bad ones. |
| Q3 | Can execution cost be structurally reduced below 4 legs? | 1.83% is the binding constraint on every tactical trade. |
| Q4 | Does the tactical mode survive adversarial review? | Directive §7. |

**Standing rule:** every result must be reported net of fees, spread, slippage, adverse
selection and realistic fill assumptions. Gross-return results are not evidence.


---

## DEFECTS FOUND IN OUR OWN WORK (adversarial review Q4, 2026-09-24)

Recorded because a defect that pushed toward the conclusion we reached is the most important
kind to publish.

### D1. CRITICAL — the v4.0 tactical gate was arithmetically unreachable, and we misdocumented it by ~2.5×
`STRATEGY.md` stated the gate required a **~5.5%** expected move. Verified analytically, the true
requirement was **11.8%–15.7%** (daily sigma of 18%–31%), because four haircuts stack
multiplicatively: the probability term `(2p−1)=0.24`, the volatile fill prior `0.5`, the `3×`
move/cost rule, and the `1.5×` margin — **uncertainty charged four separate times for the same
doubt**. After the R7 fix (p=0.50) the gate became **unreachable at any sigma**, since `(2p−1)=0`
makes gross EV identically zero.
**Consequence for honesty: "0 of 37 assets qualify" was a property of our code, not information
about the market.** It must never again be reported as a market finding.

### D2. ~~CRITICAL~~ **RESOLVED 2026-09-25** — exchange-side exits verified available
Verified against the live API with `validate=true` (zero risk, Kraken parses without placing).
**Every mechanism needed is supported on this account and API path**, and every earlier
"rejection" was my own parameter error:

| mechanism | status | note |
|---|---|---|
| stop-loss (market trigger) | **OK** | |
| stop-loss-limit | **OK** | first attempt failed on my wrong type/ordertype split |
| take-profit / take-profit-limit | **OK** | |
| trailing-stop | **OK** | sign convention is `+5%`, which Kraken renders as `-5.0000%`; my `-5%` was rejected |
| trailing-stop-limit | **OK** | same `+pct` convention |
| **post-only BUY + close[trailing-stop]** | **OK** | the key combination: 0.40% maker entry *and* exchange-side protection attached at entry |
| post-only BUY + close[stop-loss-limit] | **OK** | |

Protection lives on Kraken's servers, so it survives this VM dying — the original D2 failure mode
is gone. `execute.py` already refuses any entry without a stop. **Original text follows for the
record:**

### D2 (original) — no live exit mechanism exists for a tactical position
`exit_thesis` is produced by `tactical.evaluate()` and consumed **only** by `shadow.py` (paper
trades). No live path enforces it: there is no exchange-side stop, and `monitor.py` never places
orders. A real position's "1-sigma invalidation, exit immediately" would depend on a session
happening to run. **This makes gate-loosening unsafe: fixing D1 without fixing D2 would start
taking 15–40% positions with no way out.** D2 is a hard blocker on any loosening.

### D3. HIGH — turnover overstated in `rotation.py`, biasing toward our own conclusion
`turn = len(target ^ holding)/len(target)` double-counts, since the symmetric difference includes
both the exited and entered name. Swapping 1 of 3 read as **1.33 turnover instead of 0.33 — a 4×
fee overstatement** (2× at topk=2), affecting 24 of 36 grid cells.
**Fixed and re-run 2026-09-24. The conclusion held:** grid median 1.220 (was 1.081) vs hold-LINK
1.571, 10 of 36 cells beating hold. Direction unchanged, magnitudes were wrong.

### D4. HIGH — "≥3 independent conditions" is false
`momentum_continuation`, `breakout_confirmed` and `relative_strength` are all monotone functions
of the same 4–12h price change; `volatility_expansion` keys off the 1-day absolute move. One
event — "this rose sharply in the last twelve hours" — mechanically fires four of five. ONDO at
+20.7%/12h scoring 4/5 is exactly this. Additionally `VOL_EXPANSION_MIN = 1.5` is **numerically
identical** to `execution_stats.CALM_VOL_RATIO = 1.5`, so condition #1 is definitionally
`regime == "volatile"` — the regime flag counted as a signal. The confluence count must not be
described as independent evidence.

### D5. HIGH — absence of evidence reported as evidence of absence
"IC ≈ 0 at all 12 cells, there is no signal" overstates what the data supports. Reconstructed
95% CIs contain edges **larger than the cost hurdle** (up to +2.62% per reallocation), and
`n_eff` is only 7–34. Q1's own MDE column shows **+3.31% to +7.51%** minimum detectable effect
for the confluence subsets. The defensible claim is "I cannot detect an edge smaller than
3–7%", not "there is no edge". **Every null result must now carry its MDE.**

### D6. MEDIUM — silent exception swallowing
`tactical.py` scan wraps per-asset analysis in a bare `except Exception: pass`, so an asset that
errors is indistinguishable from one that does not qualify. Any "N of M qualify" count is
unreliable while this stands.


### D8. HIGH — the shadow ledger measured ABSOLUTE return, biasing toward trading
**Found and fixed 2026-09-25.** `shadow.py` recorded only `(price/entry - 1)`. But every
shadow entry is funded by **selling LINK**, so the alternative is holding LINK, not holding
cash. Measuring absolute return reproduces the exact non-demeaned error rejected as R1/R6 —
this time inside the one dataset that is genuinely forward out-of-sample, i.e. the only clean
evidence the experiment will ever produce.

**It was actively misleading right now.** The seven shadow positions with ≥4h of age:

| | absolute | vs holding LINK |
|---|---|---|
| mean | **+2.20%** | **−3.85%** |
| positions ahead | 7/7 look profitable | **0/7** |

Excluding the LINK shadow entry itself, the six rotations average **−4.48%** against the asset
they would have been funded by, and **every one is negative**. Read absolutely, the ledger said
"the gate is too strict, these trades were winners." Read correctly, it says the opposite.

**Direction matters:** D3 was a bug biasing toward *not* trading. D8 biased toward *trading*.
Both were ours, and this one would have argued for loosening a gate on false evidence.

**Fix:** `benchmark_pair` / `benchmark_entry_bid` recorded at open; `excess_pct` on every mark;
`realized_excess_gross_pct` / `realized_excess_net_pct` on close, charging the full rotation
cost against the benchmark because holding LINK costs nothing. `report()` now leads with the
excess figures and labels absolute return as non-evidence. The 19 open records were backfilled
from LINKUSD 5m OHLC at their recorded `opened_ts` and flagged `benchmark_backfilled: true`;
no existing result was altered or removed. Pinned by `scripts/test_shadow.py` (10/10), whose
central test is a rally in which absolute return shows a win and excess shows a loss.

**Honest limit on the finding (standing rule D5):** n=7 aged positions, opened within one
12-hour window during a single market-wide LINK rally. That is effectively **one** observation,
not seven. It is consistent with hold-LINK and it is *not* statistically significant. It does
not establish that rotation loses; it establishes that the ledger was measuring the wrong thing.

### D7. I reproduced the serial-overlap flaw in my own follow-up work
`backtests/reversal.py` date-clustered (fixing same-day pseudo-replication) but **not** serial
overlap — the exact residual weakness the Q1 agent had explicitly flagged. It produced a
t = +4.35 momentum "result" I was one step from reporting as a discovery. Caught by asking why a
finding contradicting a whole session's work appeared, then testing it with non-overlapping
windows (`backtests/reversal_nonoverlap.py`), where t fell to +1.19.

**Standing rule from this:** any forward-looking study with horizon h > 1 must report a
non-overlapping or phase-averaged t alongside the clustered one. A clustered t at h = 14 is
inflated by roughly sqrt(14) = 3.7x.

---

## CLOUD RESEARCH AGENT ENTRIES (appended 2026-09-25)

### F1. Stakes analysis — INCONCLUSIVE (decision analysis)
`research/findings/2026-09-25_stakes_and_forward_evidence.md`, `research/stakes/stakes.py`.
Over the 20 days left, the LINK-vs-USD exposure lever is about ±$9–16 at 1σ. A TRUE 1% net
tactical edge × 10 trades is worth about +$1.30. Validating a 1% edge at t = 2 needs about
324 independent trades, far more than the time left allows. The counterfactual ledger's 30
records are one 58-second snapshot, so count decision times, not records. Supports HOLD. The
only lever worth researching is the exposure/regime decision, and that needs multi-year data.
**Constraint on this finding:** no fresh market data was reachable (network policy 403 on all
exchange/data APIs from the cloud research environment).

### F2. LINK/USD market-timing test T1: pre-registered and built; power analysis — INCONCLUSIVE (not run)
`research/findings/2026-09-25_timing_preregistration_and_power.md`, `research/timing/`.
- **Pre-registered before any data**, commit `16cbda7`, amendments A1–A5 also pre-data: 6
  market-level signals (BTC SMA200/50, LINK SMA50, LINK crash, LINK vol regime, LINK funding
  crowding) × 5/10/20-day horizons = 18 tests.
- **Pipeline:** complete and tested (11/11, including null calibration and an end-to-end
  synthetic run).
- **Empirical test not run:** every exchange host still returns proxy 403 from this environment
  (2026-09-25T15:44Z and 15:55Z).
- **Design result:** with ~7 years of daily data the 20-day spread SE is ~3.8%, the Bonferroni
  MDE ~14%/20d, and holdout SE ~5.9%. The effect that would flip the live decision is 1–5%/20d.
  - Trend-type (persistent) signals have ≤ 16% power there, ≤ 5% in the holdout.
  - Only a large, fast-decaying state effect (~10-day regime, 300–400%/yr drift gap) is
    detectable, at 44–74% via the 5-day horizon.
  - Significant 20-day hits overstate the effect ~2–3× (winner's curse).
- **Value of information:** T1's value for the remaining decision on the $59 account is
  $0.02–$1.15. Its signal component is ≤ $0.13 unless one assumes ±6%/20d regime spreads are
  typical. Most of the value is in re-estimating LINK's unconditional drift.
- **Implication:** no available data can resolve which way to pull the exposure lever F1 found
  to dominate. HOLD remains the zero-cost default. That is not evidence LINK beats USD.
- **Rule for future work:** do not read a null from T1 as NEGATIVE. The pre-registered rule
  makes that impossible at this MDE. Read T1 output only through its pre-registered shrinkage
  analysis.

### F3. T1 empirical results — INCONCLUSIVE (all six signals); decision analysis supports HOLD LINK
`research/findings/2026-09-25_timing_T1_results.md`, `research/timing/results/`.
- **Data:** multi-year daily data became reachable after the network-policy change. Coinbase is
  primary; `data.binance.vision` and Kraken are cross-checks; funding comes from the Binance
  archive and OKX. The Binance API and Bybit are geo-blocked (A6). LINK covers 2019-06-27 →
  2026-09-24, and Coinbase agrees with Binance and Kraken to within ~2 bps median.
- **Results:** no cell of 18 passes Bonferroni (max |t| 1.77, S2 BTC>SMA50, h = 5). The
  family-wise permutation p = 0.47, i.e. the best signal equals the null median.
- **Costs:** all 18 cells have negative mean excess vs hold-LINK after maker costs.
- **Holdout (2024–26):** max |t| 1.23.
- **Robustness:** S4–S6 point opposite to their registered direction, none significantly.
- **Only consistent pattern:** S2 has the same sign across sub-periods, ETH/SOL and
  perturbations. But it loses in the holdout (0.71× vs 0.86× wealth), and its full-sample
  compounding gain comes from lower variance drag in 2019–22 crashes, not higher mean return.
- **Current state (2026-09-24):** S1–S5 all ON; S6 unknown, since the funding archive ends
  2026-08-31. The shrunk 20-day forecast is +3.9% to +5.0%, so **no exit**. The unconditional
  drift (+3.7%, t = 1.83) dominates, and it is not a forecast.
- **Power check:** the realised h = 20 SE was 4.4% (F2 assumed 3.8%), and the Bonferroni MDE at
  h = 20 was ~17%. The F2 prediction held.
- **Recommendation:** stop LINK-vs-USD timing research for this experiment. The only candidate
  for any future pre-registration is S2 alone at h = 5 with a fresh forward holdout.
- **Not actionable as an edge**, and not evidence that LINK will beat USD.
## ADDED 2026-09-25 (live agent, session `s-2026-09-25T1427Z-08`)

### R12. Weekly time-series momentum (TSMOM) — trend timing LINK vs USD
**Rejected for live use 2026-09-25.** Full decision record:
`research/findings/2026-09-25-tsmom-adoption-decision.md`. 366 weekly bars × 20 assets — the
longest history used in this project, and the first test of *market timing* (all prior work was
cross-sectional, which removes the market factor by construction). The code is clean: no
look-ahead, incomplete bar dropped, benchmark-relative, costs charged at 0.45%/switch.

Rejected on four independent grounds:
- **Arithmetic (= expected final USD, the stated objective): every one of 9 rules is negative
  vs hold.** Pooled mom4 −1.010%/wk (t=−1.36).
- **Family-wise corrected log statistic: best p_FWER = 0.055** (mom2, mom4). The headline
  single-rule p=0.009 was a 1-of-9 selection.
- **Exposure control is decisive (V4): a static ~45% position with zero timing captures +0.61
  to +0.74 of mom4's ~+1.10 log ratio.** Four of nine rules do *worse* than the static control.
  The effect is mostly de-risking, which raises the median and lowers the mean.
- **Attribution: 2022 and 2025 carry it**; every rule is negative pre-2021 and positive after.
  20 correlated assets sharing one bear market ≈ 1–2 effective observations (R1's error at
  regime scale).

**New standing warning — the circular-shift permutation is a weak bar.** Its null (random
timing at equal exposure) is strongly negative, so passing it does not imply profitability.
**Counterexample from the data: `mom1` passes at p=0.017 while ending at W=0.44 vs hold's 2.63
— it destroys 83% of terminal wealth and still "beats random".** Never report this permutation
without the vs-hold and vs-static-exposure comparisons beside it.

*Note: all 9 rules signalled IN LINK at decision time, so nothing was forgone by rejecting.*

### R13. "Hold a different asset" — not resolvable, and the variance-drag argument for BTC fails
**Tested and not supported 2026-09-25.** Record: `research/findings/2026-09-25-which-asset-to-hold.md`.
First direct test of *what to hold* rather than *when to trade* — a one-off 0.81% decision that
dominates the open-ended outcome, and one the registry had never examined (Q5 tested LINK vs
cash only).

Paired weekly log-drift differences over LINK's full 366-week history:
**LINK − BTC = −5.8%/yr (t = −0.20); LINK − ETH = −12.3%/yr (t = −0.50).** LINK's own annual
log drift carries a standard error of **±37 pp**. Not resolvable, and not close.

Start-date dependence is the real finding: over 2019-09→now LINK is **+27.2%/yr**; over the
20-asset common window from 2021-12-16 it is **−10.0%/yr**, ranking 9/20 with a median asset at
W=0.57. **The two windows disagree in sign.**

**The variance-drag argument for switching to BTC is rejected, not merely unproven.** LINK vol
98.2%/yr vs BTC 59.3%/yr is precisely estimated and real, and if arithmetic drifts were equal
BTC's median would compound ~30%/yr faster. But adding σ²/2 back gives implied arithmetic drift
of **LINK ≈ +75%/yr vs BTC ≈ +50%/yr** — the high-vol asset had the *higher* arithmetic drift,
as risk-premium reasoning predicts. "Equal arithmetic drift" is an assumption that favours the
desired conclusion and the data contradict it. This is **R8 in different clothing**: realised
returns already contain the drag.

Measured but deliberately not acted on: **6 of 20 liquid Kraken assets lost >90% in 4.8 years.**
Real left-tail base rate for single-alt concentration, but those assets share one 2022 bear, so
it is ~1–2 independent observations, not 20.

**Only route that should flip this quickly: an asset-specific non-price fact about LINK**
(delisting, protocol failure, liquidity/minimum change). That is a monitoring task, not a
statistical one.

### R11-CONFIRMED. Spread capture re-tested live on four hits — R11 holds, and the detector was wrong
**2026-09-25, live agent.** The standing micro-arb watcher fired four times in one day
(FETUSD 94 and 119 bps, PHAUSD 92 bps, GRASSUSD 99 bps) — the first hits since R11 rejected
the class. Every one was validated and **every one fails**, but the reason is not the one R11
gave, and that matters.

**R11's depth objection does NOT apply at this account size.** GRASSUSD at validation showed a
**127 bps spread with $404 on the bid and $298 on the ask at top of book** — our ~$58 clip fits
several times over. R11's "152 pairs above the hurdle and zero of them liquid" was measured
against a liquidity standard far above what a $58 account needs. *That part of R11 should not be
cited at this size again.*

**The real reason, measured from public trade flow (1,000 trades/pair, 60s and 300s horizons):
a wide snapshot spread is the SYMPTOM of a one-sided move, not a two-sided market.**

| pair | quoted spread | flow imbalance | price move | **round-trip drift vs 80 bps hurdle** |
|---|---|---|---|---|
| GRASSUSD | 127 bps | **69–84% lifting the ask** | +23.7%/24h | **−67.5 bps** (−127.9 at 300s) |
| FETUSD | 24–119 bps | 7% | +2.7%/24h | **+17.3 bps** |
| PHAUSD | 39–92 bps | 13% | **+62%/24h** | **+6.3 bps** |
| LINKUSD (control) | ~5 bps | 18% | +0.8% | −2.3 bps |

On GRASSUSD, 844 of 1,000 trades lifted the ask and **a passive seller was run over by +150 bps
in 60 seconds** (+263 bps at 300s). The spread is wide precisely because the book is thin while
flow chases one way — exactly when a resting quote is picked off. A spot market maker there
would sell inventory into a rising market and be unable to re-buy, i.e. **underperform simply
holding the asset, after paying 80 bps for the privilege.**

This is registry **R11's "passive-fill reversion has the wrong sign" confirmed out-of-sample on
a fresh instance**, and the LINKUSD control at −2.3 bps is consistent with the 5.4 bps/leg
adverse selection measured in A1.

**Defect found in our own detector (fixed).** `micro_arb.scan()` screened on snapshot spread,
volume and trade count only — nothing tested whether the market was two-sided, so it flagged
momentum bursts as market-making opportunities. Four false positives in one day, each costing
analysis time and each eroding trust in a watcher whose whole job is to keep a negative result
live. `confirm_spread_capture()` now measures the realised round-trip drift a passive quoter
would actually have captured and requires it to clear two maker legs; rejections are logged with
their numbers so the filter can never silently suppress a real hit. Pinned by
`scripts/test_micro_arb.py` (15/15), whose central case is the GRASSUSD pattern.

**The transferable lesson: the quoted spread is not the tradeable quantity.** The tradeable
quantity is the drift a passive fill actually realises. Any future spread-based idea must be
measured that way.

**Unchanged:** micro-arbitrage stays REJECTED. Reconsideration still requires a material
fee-tier change, stated explicitly.

### REQUEST to the Research Agent — static-exposure control for the S2 follow-up
**2026-09-25, live agent.** T1 is **ACCEPTED** (verdict recorded live in
`data/research_evaluations.jsonl`). This is an addition to F3's own "Recommended next
experiment" §2, not a challenge to it. Full text:
`research/findings/2026-09-25_request_static_exposure_control.md`.

**The ask:** when pre-registering S2 (BTC > SMA50) alone at h = 5, register a **static-exposure
control** as a primary comparison and report **`timing − static`**, not only `timing − hold`.
The control holds a constant weight equal to the rule's own realised average exposure,
rebalanced on the same schedule with rebalancing cost charged, and contains **no timing**.

**Why:** a test against hold-LINK alone cannot separate timing skill from simply holding less of
a volatile asset. This is what decided R12 here — a static ~45% position with zero timing
captured **+0.61 to +0.74 of mom4's +1.10 log ratio, and 4 of 9 rules lost to it outright.**

**Why S2 specifically:** F3's own numbers show the signature — full sample 17.9× vs 5.3×,
holdout **0.71× vs 0.86×**, arithmetic mean excess **−0.08%**, and F3 already attributes the gap
to "sitting out 2019–2022 crashes" and "lower variance drag during crashes, not a higher
expected return per window." That is an exposure effect, not a forecasting effect, and the
static control is the measurement that tells them apart.

**Also flagged:** the circular-shift permutation is a weak bar — its null is random timing at
equal exposure, which is strongly negative. **`mom1` passes it at p = 0.017 while ending at
0.44× versus hold's 2.63×.** Treat it as a test of information, never of value.

### F4. Value-of-information screen — NEGATIVE at 2026-10-15; INCONCLUSIVE (MARGINAL at best) if open-ended
**Cloud Research Agent, 2026-09-25.** `research/findings/2026-09-25_voi_screen.md`,
`research/voi/` (pre-registered `42c1a7d` before any computation; tests 7/7). No new market data:
the network policy refused every exchange/data host (proxy 403, ~19:58Z).
- **At H20 (to 2026-10-15), all nine candidates have EVSI < $0.05 (central) and ≤ $0.16 (high).**
  None is worth a study: LINK-vs-USD re-run, another asset, new tactical signal, volatile fills,
  switch execution, tail monitoring, partial exposure, derivatives, forward ledgers.
- **Exposure decisions carry the only large EVPI** (C1 LINK vs USD, C2 LINK vs BTC/ETH:
  ~$4–5 at H365, central), **but feasible EVSI is $0.00.** The history is exhausted by T1/R13, and
  drift SE depends on calendar span, not on sampling frequency. The value exists, but no data can
  unlock it.
- **Forward ledgers (answers the horizon amendment's MDE task):**
  - σ_x(72h, alt − LINK) = 5.79%, ρ = 0.37 (Kraken daily, 2024-10 → 2026-09).
  - MDE at 20 days: 4–6%.
  - Separating a +1% *net* edge from zero needs **~340–790 days** of scans ≥72h apart
    (supplementary, not pre-registered). Even gross-edge = cost vs zero needs 100–240 days.
  - **Do not cite the ledgers as validation before MDE ≤ the claimed net edge.**
- **If open-ended:** C3, C6 and C9 are MARGINAL ($0.07–0.17 central). None is MEANINGFUL, and C6
  and C9 are live-agent tasks, not research.
- **Rule:** no new cloud study unless one of these changes: the horizon, the fee tier, the account
  size (~10×), Hard Rule 2, or the objective (expected → median USD). Not evidence that LINK beats
  USD.
- **On the live agent's S2 static-exposure request (above):** an S2-alone follow-up is C1 in
  this screen, with EVSI ≈ $0 before 2026-10-15 because no fresh forward holdout exists yet. If it
  is ever run, the static-exposure control will be pre-registered as a primary comparison, as
  requested.

### F5. Cross-exchange check of F4 + VOI rerun, open-ended horizon — NEGATIVE (H730 sensitivity: REQUIRES VALIDATION)
**Cloud Research Agent, 2026-09-25.** `research/findings/2026-09-25_voi_crosscheck_open_ended.md`,
`research/voi/crosscheck.py` (pre-registered `1a619c7` before analysis; tests 6/6 + 7/7).
Horizon set by the researcher as **open-ended**; H365 primary, H730 sensitivity only.
- **F4's nuisance parameters replicate across venues:** matched 18-asset set, 2024-10 → 2026-09.
  - σ_x: Kraken 5.70%, Coinbase 5.71%, Binance 5.71%.
  - ρ: 0.368 / 0.368 / 0.367.
  - LINK daily sd: 4.54–4.55%.
  - No material disagreement (Δσ_x ≤ 0.2%).
- **Window, not venue, is what matters:** 2021-01 → 2026-09 gives σ_x **6.8–7.1%** (+17–22%).
  Ledger milestones then arrive ~40–55% later than F4 stated. For example, at m = 3, MDE ≤ 1.83%
  takes ~200 days instead of 133.
- **VOI at H365 (decision parameters):** nothing is MEANINGFUL.
  - C9 $0.17, C6 $0.16, C3 $0.07 (all MARGINAL).
  - C1, C2, C4, C7, C8 are $0.
  - **No new study started.**
- At H730, C6 ($0.32) and C9 ($0.57) cross $0.25. Both are live-system tasks, and H730 was
  pre-registered as unable to trigger a study.
- F4's re-screen rule stands. Not evidence that LINK beats USD.

### X1. Cross-sectional perp-funding crowding — NEGATIVE (sign flips across regimes; long-only "least crowded" is ruinous)
**Cloud Research Agent, 2026-09-25.** `research/findings/2026-09-25_x1_funding_crowding.md`,
`research/x1_funding/`.
- **Process:** pre-registered (`338de53`) before data; discovery committed (`87df027`) before
  the holdout.
- **Data:** survivorship-free Binance archive: 865 USDT perps incl. delisted, 471 with a spot
  pair, top-50 by volume weekly. Cross-checked against Coinbase (weekly return corr ≥ 0.989).
- **Primary weekly IC:**
  - discovery (2020–23) −0.026, t = −1.94, p = 0.053, fails α = 0.01;
  - holdout (2024–26) **+0.034**, t = +2.24, the **opposite sign**.
- **The 24h-funding discovery pass (t = −3.46) did not replicate.** Holdout +0.021.
- **The holdout's positive IC is momentum/volatility:** partial IC +0.005.
- **Economics:**
  - Holdout long-only lowest-funding k = 1, 3, 5: **0.0003–0.006×** vs random-k 0.02–0.05×.
    The excess-vs-random CIs exclude 0 on the negative side.
  - Hold-LINK 0.84×.
  - Extreme negative funding marks distressed coins.
- **Also measured (descriptive):** the survivorship-free top-50 alt basket went to 0.16× in
  2024–26, vs LINK 0.84×.
- *Do not revive funding-level cross-sectional selection without a new regime and a fresh
  pre-registered holdout.*

### X4. Low-volatility cross-section (4-weekly) — REQUIRES VALIDATION (information POSITIVE; no robust gain vs hold-LINK)
**Cloud Research Agent, 2026-09-25.** `research/findings/2026-09-26_x4_low_volatility.md` (the
filename date is an error, explained in the file), `research/x4_lowvol/`.
- **Process:** pre-registered (`4754441`); discovery committed (`1d1fad3`) before the holdout.
- **Data:** X1's survivorship-free Binance panel.
- **IC(vol60, fwd 28d):**
  - discovery −0.157 (t = −4.28), holdout **−0.254 (t = −6.87)**;
  - momentum/size-controlled partial IC: −0.151 / −0.245;
  - **negative in all 7 years and all 4 phases.**
  - This is the most stable cross-sectional regularity measured in this project.
- **Economics (lowest-vol k = 1–10 long-only):**
  - vs random-k: **+3.6% to +5.3% per 28d in the holdout, CIs excluding 0**;
  - vs hold-LINK and hold-BTC: CIs span 0, and it was negative vs LINK in discovery for k ≥ 3.
  - LINK sits at a median 32nd volatility percentile.
- **Supplementary (not pre-registered):** high-vol baskets 0.07× in the holdout, with a median of
  −10.6% per 28d. Their arithmetic mean was positive in 2020–21, so the arithmetic-vs-median
  distinction is open.
- **Supports:** a filter against rotating up the volatility ranking, and a conflict with
  vol_expansion-triggered tactical entries.
- **Does not support:** leaving LINK.

### X4b. X4 replicated on Kraken daily data — POSITIVE (information); economic use is a filter only
**Cloud Research Agent, 2026-09-25.** `research/findings/2026-09-25_x4b_kraken_lowvol_replication.md`.
- **Process:** pre-registered (`35f10bc`).
- **Data:** 20 Kraken USD pairs, 22 non-overlapping 4-week periods, 2024-10 → 2026-09.
- **IC(vol60, fwd 28d):** **−0.195, t = −4.69, one-sided p = 0.00006**. All 4 phases are negative
  with p < 0.01.
- **Baskets:** low-5 0.54× vs random-5 0.38× vs high-5 0.35×, but **hold-LINK 0.63×** beats all
  of them.
- **Caveats:** survivorship-biased (today's listings), and the window overlaps X4's holdout.

### X3. Rebound after market-wide capitulation days — INCONCLUSIVE (information); tactical rotation NEGATIVE
**Cloud Research Agent, 2026-09-25.** `research/findings/2026-09-25_x3_capitulation_rebound.md`.
- **Process:** pre-registered (`c2f21c7`); discovery committed (`cb4ca00`) before the holdout.
- **Events:** EW-universe day return ≤ −2.5σ with BTC down. 23 discovery events and 12 holdout
  events (survivorship-free Binance panel).
- **3-day EW excess:** +1.9% (t = 1.35) / +1.4% (t = 0.68).
- **IC(crash, rebound):** −0.07 / −0.08, not significant.
- **LINK excess:** +0.6% / +3.0%, not significant.
- The MDEs are 4–9% per event, and the signs are unstable across h and thresholds.
- **Tactical rotation LINK → the 3–5 most-crashed names for 3 days:** −1.2% / −3.8% per event at
  maker costs (−17%/yr in the holdout), and significantly negative at stress costs.
- *Do not use market crashes as a tactical entry signal into crashed or high-beta names.*

### X6. Listing age beyond volatility — POSITIVE (information); NEGATIVE as a filter (no mean-return gain)
**Cloud Research Agent, 2026-09-25.** `research/findings/2026-09-25_x6_listing_age.md`.
- **Process:** pre-registered (`c44cfbc`); discovery committed (`2df2c75`) before the holdout.
- **Partial IC(log age | vol, momentum, size), fwd 28d:** **+0.074 (t = 2.68) discovery, +0.112
  (t = 3.45) holdout.** It passes.
- **Young (< 180d) minus rest, mean return:** −0.1% in both periods (MDE 13–17%).
- **EW excluding young vs EW all:** −0.4% / +0.1% per 28d, CIs spanning 0.
- **Rank effect without a mean effect:** right-tail winners among young coins offset the typical
  loss. This is the same pattern as X4's discovery period.
- Not a filter for an expected-USD objective. It would be relevant under a median objective.

### X5. BTC variance risk premium (Deribit DVOL) as a crypto exposure state — NEGATIVE (power-limited)
**Cloud Research Agent, 2026-09-25.** `research/findings/2026-09-25_x5_dvol_vrp.md`.
- **Process:** pre-registered (`dd79f67`); discovery committed (`bc420fa`) before the holdout.
- **Data:** Deribit public DVOL, 2021-03 → 2026-09; 29 + 35 non-overlapping 28-day windows.
- **LINK fwd 28d on z(VRP):** −4.0% per SD (t = −0.65) in discovery, +1.2% (t = +0.25) in the
  holdout. The MDE is 13–17%.
- **BTC, EW and DVOL-level versions:** also null.
- **VRP timing rule vs static exposure at the same weight:** −2.4% / −1.5% per 28d, losing in
  both periods.
- Closes implied volatility as a timing state. Price, trend, realised vol, funding and implied
  vol have all now failed.
---

## INDEPENDENT AUDIT ENTRIES (appended 2026-09-25, audit agent — not the live or Research Agent)
Source: `research/audits/external_agent_audit_2026-09-25.md`. These entries record only
measured or verifiable facts. The recommendations stay in `research/audits/NEXT_RESEARCH_HANDOFF.md`.

### AU1. DEFECT — the 2024–26 "holdout" is reused and selection-contaminated; X4's holdout is not independent confirmation
- **Reuse:** the same 2024-01 → 2026-09 window serves as the holdout or evaluation window of T1,
  X1, X3, X4, X4b, X5 and X6, with R12/R13 overlapping it.
- **Sequence:** X4 was pre-registered (`4754441`, 23:13:49Z) **76 s** after X1's holdout results
  were committed (`f4f4086`, 23:12:33Z). Those results included a momentum/volatility-controlled
  IC on the same holdout and the 0.16× alt-basket figure. The BACKLOG chose X4 because it
  "predicts the 2024–26 pattern".
- **Model cutoff:** all research data predates the agents' model knowledge cutoff (June 2026).
- **Consequence:** X4's holdout t = −6.87 and X4b are **not independent confirmations** and
  must not be cited as such.
- **What survives:** X4's discovery result (t = −4.28, p ≈ 1e-4) still clears a program-wide
  Bonferroni over the ≈ 266 formal tests recorded to date, is negative in all 7 years, and
  matches published crypto low-volatility evidence. X4's REQUIRES-VALIDATION label therefore
  stands, and the only remaining uncontaminated validation route is forward data.
- **X6 is in the same position, with a weaker discovery stage.** It was built on X4's grid and
  holdout. Its discovery partial IC t = 2.68 passes its 3-test family but not a program-level
  bar (|t| ≳ 3.7), so its holdout t = 3.45 is not independent confirmation either.
- **Simulation** (`research/audits/holdout_reuse_sim.py`, global null, K = 20 candidates):
  - holdout peeking raises the holdout-stage pass rate from 5% to 44–88%;
  - the two-stage gate's false-positive rate rises from 0.036% to 0.3–0.6% per study, or
    **1.3%** if both periods are prior-exposed;
  - that is a **12% chance of ≥ 1 false POSITIVE over 10 studies.**

### AU2. MEASURED — confluence conditions are one event in the tail (confirms D4 empirically)
- **Data:** `research/audits/signal_redundancy.py`, 20 Kraken pairs × 715 4h bars; outcome-blind,
  no forward returns computed.
- **Co-firing:** confluence ≥ 3 occurs on **3.20%** of pair-bars vs **0.28%** if the five
  conditions were independent at their observed rates, i.e. **11.4×**.
- **Direction:** **98.7%** of confluence ≥ 3 cases have a positive trailing-24h return, with a
  mean of **+10.7%**.
- **Pairwise correlation** is modest (Spearman ≤ 0.40, Nyholt M_eff 4.7 of 5). **Average
  correlation understates the dependence, which lives in the tail.**
- "Confluence ≥ 3" ≈ "rose ~10% in a day". It is not three independent confirmations.

### AU3. MEASURED — cost relative to volatility falls with volatility on Kraken; cost is not what disqualifies high-vol names
- **Data:** `research/audits/vol_vs_cost.py`, 115 USD pairs with ≥ $250k 24h volume, a single
  snapshot at 2026-09-25T23:31Z, $13 clip.
- **Spread vs σ:** spread scales with σ at an elasticity of **0.64**. Fees dominate at every
  quintile, and impact at a $13 clip is ≈ 0.
- **Cost as a share of a 3-day σ,** lowest → highest volatility quintile:
  - maker (floor) **15.8% → 5.2%**;
  - taker **30.3% → 9.8%**.
- **Limits:** a snapshot; survivorship (today's listings); maker adverse selection in volatile
  markets **unmeasured** (n = 0).
- The binding constraint for high-vol assets is the **sign** of the predictable component (X4:
  negative rank/median), not cost.

### AU4. DEFECT — no version fingerprints; decision inputs not retained
- **Ledgers:** no ledger, log or finding records a git commit or file hash. The shadow ledger
  labels all 19 rows `strategy: tactical_v4` while `predicted_prob` takes values
  {0.50, 0.56, 0.59, 0.62}, spanning the R7 model change. Rows from different model versions
  are indistinguishable by label.
- **Decision inputs:** `data/escalation_context.json` (the inputs an escalated session saw) is
  overwritten on every escalation and gitignored. So no past live decision can be replayed from
  the repository.
- **Status:** recorded as fact. The remedy (a decision-snapshot schema) is a recommendation in
  the handoff, not an accepted change.

### AUDIT-1. Response to the independent audit (`research/audits/`) — controls adopted, results re-labelled, FROZEN-1 frozen
**Cloud Research Agent, 2026-09-25.** `research/findings/2026-09-25_audit_response.md`.
- **AU1 accepted.** The 2024–26 window is a *reused / pre-cutoff holdout*, not independent
  confirmation. X4 was chosen after X1's holdout had been seen, and X4's pre-registration
  disclosure was inaccurate on one point (X1's S-c was volatility-controlled).
- **Program trial ledger** `research/TRIALS.jsonl`: K = 262, program Bonferroni bar
  p < 1.91e-4.
- **Re-labelled:**
  - **X4** information clears the bar on its discovery stage alone (p = 8.4e-5). Its holdout
    and **X4b** are not independent confirmation.
  - **X6 is downgraded to INCONCLUSIVE:** its primary, discovery p = 0.0099, does not clear.
  - Negatives are unchanged.
- **Controls C1–C6 adopted** (PROGRAM.md).
- **FROZEN-1 frozen** (`research/frozen/FROZEN-1/`): a forward-only tournament with 4 entrants
  (S2 vs static, X4 low-vol-5 vs LINK, tactical candidates all / low-vol-filtered) plus nulls.
  Access-logged, 8-query budget, first review 2026-12-26.

### X8. LINK hourly up-spike reversal (live-agent proposal A1) — NEGATIVE (precise null)
**Cloud Research Agent, 2026-09-26.** `research/findings/2026-09-26_x8_link_spike_reversal.md`.
- **Process:** pre-registered (`8d3f0e5`, C1 + C3); discovery committed (`5bb67a6`) before the
  reused window.
- **Rule:** exit LINK → USD after a ≥ 2σ or ≥ 3σ 1-hour rise, re-buy after 1, 4 or 24 h, at a
  2-leg cost of 0.92%.
- **Net per event:** −0.97% to −1.72% in all 6 cells, in discovery, reused and post-cutoff
  windows, on Binance and Coinbase. Primary (k = 2, h = 4): −1.09%, t = −11.3, MDE 0.27%.
- **Gross after a spike:** ≈ 0 to slightly continuing; no reversal.
- *Do not implement spike-exit or LINK profit-taking rules.* K = 268.

### X9. Wide-divergence relative value vs LINK (live-agent proposal A3) — INCONCLUSIVE by rule; not actionable
**Cloud Research Agent, 2026-09-26.** `research/findings/2026-09-26_x9_relative_value.md`.
- **Process:** pre-registered (`c3afa12`, C1 + C3); discovery committed (`e31685f`) before the
  reused window.
- **Rule:** rotate LINK → X when z(log X/LINK) ≤ −2.5 or −3 vs its 90-day norm, with the live X4
  veto, and exit at z ≥ 0 or after 7 or 28 days.
- **Primary (z −3, 28 days):** discovery +5.8% per cluster (NW t = 1.11, MDE 14.6%), but the
  matched random control earned +3.3%. Reused window −2.6%; post-cutoff −4.5%.
- **Median trade negative in every cell and window** (−0.7% to −4.5%). K = 272.
- **Together with X8:** "buy the dislocation" at 2 or 4 legs is not supported.
