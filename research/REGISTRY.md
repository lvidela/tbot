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
