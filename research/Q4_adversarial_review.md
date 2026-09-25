# Q4 — Adversarial Review of Strategy v4.0

**Reviewer role:** hostile. The brief was to *disprove* the production strategy, not validate it.
**Date:** 2026-09-24. **Scope:** `STRATEGY.md` (all versions), `scripts/{tactical,edge,monitor,execution_stats,oppqueue,execute}.py`, `backtests/{event_study,event_study2,ic,rotation}.py`, `research/REGISTRY.md`, `logs/journal.md`, `data/{execution_log,benchmark}.json`.
**Constraints honoured:** no Kraken API calls (all numeric probes below ran against a stubbed `kraken` module), no orders, no files modified outside `research/`.

**Note on concurrency:** while this review was in progress another session added
`backtests/signal_combinations.py`, `backtests/expected_move_calibration.py`,
`backtests/execution_cost_model.py`, `scripts/shadow.py`. Those partially pre-empt findings
H-3 and H-4 and are credited where relevant. Everything else below stands against the shipped
v4.0 system.

---

## Executive summary

The headline conclusion — *hold LINK, trade almost never* — **survives**, but **not for the
reasons the strategy gives**, and the system as shipped is **broken in a way that makes the
conclusion untestable rather than proven**.

Three things are true simultaneously and the document conflates them:

1. Where the data actually has statistical power (single signals, n≈2,500 events, MDE ≈ 0.94%),
   there **is** a small real positive excess (+0.59%, t=2.18) — and it is **roughly one third of
   the 1.83% cost hurdle**. This is genuine, adequately-powered evidence for not trading.
2. Where the *production rule* operates (≥3-condition confluence, n=10–70 events, MDE 3–7%),
   there is **no power whatsoever**. "Nothing qualifies" is not a finding, it is a measurement
   failure.
3. The v4.0 tactical gate is **arithmetically unreachable**. It requires a 23–40% *daily* sigma.
   It will never fire on any asset in the eligible universe. The strategy document states the
   requirement as "~5.5% expected move"; the true requirement is ~15%.

So the system is not holding LINK *because* it tested tactical trading and found it unprofitable.
It is holding LINK because it built a gate that cannot open and then reported the gate's silence
as evidence.

---

## Findings, ranked by severity

### CRITICAL

---

#### C-1 — The v4.0 tactical gate is mathematically unreachable; the documented threshold understates the real one by ~3×

**`scripts/tactical.py:88-96, 113-117` + `scripts/edge.py:69-70, 76`**

`STRATEGY.md:269-271` states: *"Trade only when expected gross move ≥ 3× all-in cost … At current
costs that means a **~5.5% expected move** — which is the point: only genuinely large
opportunities qualify."*

That is false. I solved for the minimum daily sigma at which `tactical.evaluate()` returns
`qualifies=True`, with all inputs stubbed and maximally favourable (spread 5 bps, $2e7 depth,
zero impact):

| confluence | min daily sigma to qualify | E[move] there | move/cost | net |
|---|---|---|---|---|
| 3 | **40.4%** | 20.20% | 11.12× | +0.91% |
| 4 | **26.4%** | 15.18% | 8.36× | +0.91% |
| 5 | **23.3%** | 15.14% | 8.34× | +0.91% |

For reference, a *very* volatile liquid alt at 6% daily sigma with **perfect 5/5 confluence**
returns `move/cost 2.15×, net −0.44%`. The eligible universe (≥$3M volume, ≥1,500 trades) contains
nothing at 23% daily sigma — that is ~440% annualised.

Note the gate that actually binds is **not** the advertised 3× rule. At the qualifying point
move/cost is already 8–11×. The binding constraint is `edge.py:70`,
`net >= MIN_ABS_EDGE_PCT (0.5%)`, after two compounding haircuts the document never mentions:

- `edge.py:64`: `gross = move × (2·confidence − 1)`. With `success_probability` capped at 0.62
  (`tactical.py:96`), `(2p−1) = 0.24`, so **76% of the expected move is discarded before costs**.
- `edge.py:69`: `net = gross × fill_p − cost × fill_p`, with `fill_p = 0.5` in volatile regimes
  (`execution_stats.py:95`) — which, by the system's own R5 logic, is *always* the regime a
  tactical signal fires in.

`edge.py:76` computes and prints `required_move_pct = cost × 1.5 / (2c−1)` = **11.36%** at
confidence 0.62 — the code already knows the real number, and the strategy document quotes 5.5%
anyway.

The test suite confirms this without acknowledging it: `scripts/test_tactical.py:66` proves "the
gate can open" using a fixture with `daily_vol=0.40` — **40% daily volatility**. `:68` asserts that
5% daily vol does *not* qualify. The only evidence offered that this mode is live is a fixture no
real asset resembles.

**Consequence:** "0 of 37 qualify" (`STRATEGY.md:294`) is not market information. It is a property
of the code. The whole of v4.0 — sizing, exit theses, the opportunity queue, the confluence
machinery — is dead weight attached to a branch that cannot be reached. The claim at
`logs/journal.md:560-562` that "the system can now capture a large short-lived move that the
conservative gate structurally couldn't" is the opposite of true: v4.0's gate is *stricter* than
v3.0's 2-leg gate, not looser.

**Remedy:** (a) Correct `STRATEGY.md:271` to the true required move (~11–15%) and state plainly
that the tactical branch is currently unreachable. (b) Decide explicitly whether the
confidence haircut, the fill-probability haircut and the 3× move/cost gate are meant to stack —
they are currently three independent safety factors multiplying to ~25×. (c) Either recalibrate
`success_probability` off real data (`expected_move_calibration.py` is the right place) or drop
the `(2p−1)` term and express uncertainty once, not three times.

---

#### C-2 — The "≥3 *independent* conditions" claim is false; 4 of the 5 conditions are the same variable

**`scripts/tactical.py:62-71`; asserted at `STRATEGY.md:243, 253-256`, `REGISTRY.md:44-45`,
`logs/journal.md:528`**

The five confluence conditions:

```
volatility_expansion  = |1d return| / 30d sigma >= 1.5          # tactical.py:63
volume_confirmation   = 24h USD volume / 30d avg >= 3.0         # tactical.py:64
momentum_continuation = mom_4h >= +2% and mom_12h > 0           # tactical.py:65
breakout_confirmed    = pos_in_range >= 0.95 and rng>=3% and mom_4h > 0   # tactical.py:66
relative_strength     = mom_12h - median(mom_12h) >= 3%         # tactical.py:67
```

`momentum_continuation`, `breakout_confirmed` and `relative_strength` are all monotone functions
of *the same 4–12 hour price change*. `volatility_expansion` is a function of the 1-day absolute
move. A single event — "this asset went up a lot in the last twelve hours" — mechanically fires
four of five. The ONDO example in `STRATEGY.md:295-297` demonstrates exactly this: +20.7% in 12h
produced confluence 4/5.

So the rule that `REGISTRY.md:45` says was "derived from R1/R2: single signals carry no edge" is,
in substance, **the single momentum/volatility signal that R1 and R3 already rejected**, wearing a
4-vote disguise. Requiring 3 of 5 correlated indicators of one variable does not buy independence;
it buys a threshold on that variable.

Compounding this: `VOL_EXPANSION_MIN = 1.5` (`tactical.py:16`) is numerically identical to
`execution_stats.CALM_VOL_RATIO = 1.5` (`execution_stats.py:17`). Condition #1 is definitionally
`regime == "volatile"` — it is the regime flag, counted as a signal.

**Remedy:** Measure the empirical correlation matrix of the five condition indicators over the
cached history and report it in `STRATEGY.md`. Replace "≥3 of 5 independent conditions" with an
honest description ("a threshold on recent directional move, plus a volume confirmation").
`signal_combinations.py` now tests subsets individually — extend it to report the pairwise
co-firing rate, which will make the dependence visible.

---

#### C-3 — Volatility drag is applied selectively: by the strategy's own arithmetic, moving to USD dominates holding LINK

**`STRATEGY.md:51-54` vs `STRATEGY.md:83-84`**

Test 3 (`STRATEGY.md:52-54`) treats volatility drag as a real, costable quantity:
*"LINK 60d daily vol 3.73% → 21-day volatility drag 1.46%. An equal-weight 3-asset portfolio at
ρ=0.75 has drag 1.22%. Benefit 0.24%. Cost to implement 1.60%. Net −1.36%. Rejected."*

Thirty lines later, the same table prices the cash option:

| Move fully to USD | 0.80% | negative (forgoes LINK drift) | **< −0.80%** |
| **Hold** | **0.00%** | — | **0.00%** |

USD has **zero** volatility drag. By Test 3's own accounting the benefit of moving to cash is the
**full 1.46%**, not 0.24%, against a one-way maker cost of ~0.40–0.81%. **Net +0.65% to +1.06%.**
Under the strategy's own framework, cash strictly dominates holding — and the framework never
computes that cell. It computes the drag benefit for the option it wants to reject and omits it
for the option it wants to reject *harder*.

The escape hatch — "forgoes LINK drift" — rests on `logs/journal.md:156`: *"LINK's unconditional
daily drift is +0.117%."* That is an in-sample historical mean over the same net-bullish window the
document elsewhere warns about (`STRATEGY.md:64-65`), estimated from a single asset, with a
standard error vastly larger than the estimate. **The system rejects every other in-sample
historical mean in this repository as noise, then relies on this one to privilege the asset it
already holds.** That is the single most self-serving asymmetry in the document.

Note also that both framings are wrong for the stated objective. `CLAUDE.md` §1 says *maximize the
final USD value* — an arithmetic-expectation objective, under which volatility drag is not a cost
at all. Test 3 is therefore not merely inconsistent, it is the wrong instrument. But the strategy
cannot have it both ways: **either drag is real (cash wins) or it is not (Test 3's rejection of
diversification is void).** One of the two conclusions must fall.

**Remedy:** Pick one framework. If maximizing E[terminal USD], delete Test 3 and state that drag is
irrelevant. If maximizing median/geometric wealth, add the USD row computed consistently and
confront the result. Separately: either produce a defensible standard error on the +0.117% drift
estimate, or stop using it.

---

#### C-4 — The 4-leg cost model, which single-handedly kills every tactical trade, is an assumption that contradicts the strategy's own premise

**`scripts/tactical.py:112-113`; `STRATEGY.md:199-206, 266-268`; `logs/journal.md:316-320`**

`tactical.py:113` hardcodes `sides=4`: sell LINK → buy X → sell X → rebuy LINK. This doubles the
hurdle from ~0.92% to ~1.83% and is the proximate reason `vol_expansion` flips from **+0.94%
(passes)** to **+0.13% (fails)** (`STRATEGY.md:204-205`).

But the obligation to return to LINK is not a market constraint. It exists only if LINK is
expected to outperform X. The strategy's central finding is that **IC ≈ 0 across the universe** —
i.e. no asset has a higher expected return than any other. If that is true, there is no reason to
round-trip, and the correct model is **2 legs**. v3.0 identified this correctly ("the only
surviving configuration is a one-way re-allocation", `logs/journal.md:318`), declined it on
adverse-selection grounds, and then v4.0 **silently reinstated the 4-leg framing** without
re-arguing it.

The result is a hidden circularity: *LINK is privileged → therefore 4 legs → therefore nothing
clears cost → therefore stay in LINK.* The premise that LINK is worth returning to is the
conclusion.

**Remedy:** Make leg count a decision variable, not a constant. `tactical.evaluate()` should price
both the 2-leg (re-allocate and stay) and 4-leg (round trip) routes and report both. If the
2-leg route is chosen, the exit thesis becomes "sell to cash or re-evaluate", not "rebuy LINK".
Justify the 4-leg default with something other than incumbency.

---

#### C-5 — The production confluence rule shipped with zero backtest; the thresholds differ from every threshold that was ever tested

**`scripts/tactical.py:16-21` vs `backtests/event_study2.py:55-58`; `REGISTRY.md:44-45`**

| condition | tested in `event_study2.py` | shipped in `tactical.py` |
|---|---|---|
| vol expansion | `v1/v30 >= 2.5` (line 57) | `>= 1.5` (line 16) |
| breakout | `pos >= 1.0` (line 55) | `pos >= 0.95` (line 66) |
| volume | `>= 3.0` (line 58) | `>= 3.0` (line 18) ✓ |
| momentum 4h/12h | **never tested** | `>= 2%` / `> 0` (line 19, 65) |
| relative strength | **never tested** | `>= 3%` (line 19) |
| confluence ≥ 3 of 5 | **never tested** | line 21 |
| expected move = 0.5σ | **never tested** | line 88 |
| uplift 1.15/point | **never tested** | line 89 |
| p = 0.50 + 0.03·conf, cap 0.62 | **never tested** | line 96 |

`REGISTRY.md:44-45` claims A2 (the confluence requirement) is "Derived from R1/R2: single signals
carry no edge." R1/R2 are *single-trigger* results at *different thresholds*. They cannot support a
multi-condition rule, cannot support `1.5` when `2.5` was tested, and say nothing at all about
momentum, relative strength, or the expected-move model. This is precisely the "disproven result
quietly reused as evidence" that `REGISTRY.md:3-5` forbids — inverted: a *rejection* is being
reused as *construction guidance* for an untested rule.

Six of the nine numbers that determine whether v4.0 ever trades were chosen by the same model that
declared the system sound, with no data behind them at all.

**Credit where due:** the concurrent `backtests/signal_combinations.py` (added 23:31, after v4.0
shipped) is exactly the missing test. It evaluates 31 subsets × 3 horizons with Bonferroni and a
schedule-preserving permutation family-wise test, and finds **0 survivors, family-wise p = 0.971**.
That closes this finding *retroactively* — the rule is now tested and shows nothing — but it does
not change the fact that v4.0 went to production, was described as "armed", and had its silence
reported as evidence, before any of it existed.

**Remedy:** Fold `signal_combinations.py`'s result into `STRATEGY.md` §v4.0 explicitly, and add a
standing rule: no threshold reaches `tactical.py` before it appears in a committed backtest with a
stated multiple-testing correction.

---

#### C-6 — Absence of evidence is reported as evidence of absence; the tests lack the power to detect an edge 2–3× the cost hurdle

**`backtests/ic.py:54-57`; `STRATEGY.md:37`; `backtests/q1_output.txt` MDE column**

`STRATEGY.md:37` states: *"All 12 cells: |t| < 1.1. **There is no cross-sectional momentum signal
in this universe.**"* That is a Type II error stated as a discovery.

`ic.py:56` deflates the sample to `neff = len(ics) // fw`, yielding n_eff of 7–34. I reconstructed
the standard errors from the published (IC, t) pairs:

| lb | fw | IC | t | se | 95% CI | edge implied by CI upper bound* |
|---|---|---|---|---|---|---|
| 7 | 14 | +0.002 | +0.04 | 0.050 | [−0.096, **+0.100**] | **+2.04%** |
| 7 | 21 | −0.026 | −0.39 | 0.067 | [−0.157, **+0.105**] | **+2.62%** |
| 14 | 21 | −0.044 | −0.63 | 0.070 | [−0.181, **+0.093**] | **+2.32%** |
| 60 | 21 | −0.083 | −0.96 | 0.086 | [−0.252, **+0.086**] | **+2.16%** |

\* IC_upper × cross-sectional dispersion of forward returns (≈25% at 21d, scaled by √(fw/21)).

**Every long-horizon cell's confidence interval comfortably contains an edge larger than the
1.60–1.83% cost hurdle the strategy says nothing can clear.** The honest statement is "this test
cannot distinguish zero from a comfortably profitable signal", not "there is no signal".

The same defect, quantified by the system's own newest code: `q1_output.txt` reports a **MDE**
(minimum detectable effect) column. For the confluence subsets that define v4.0, MDE runs
**+3.31% to +7.51%** — the study is structurally incapable of detecting an edge three to four times
the cost hurdle. `vol_exp+vol_conf+momentum+rel_str` shows **net +4.03%** at h=3 with t=1.27 over
**23 clustered days**. That is not evidence of no edge; it is no evidence.

**Remedy:** Report a CI or MDE next to every null result in `STRATEGY.md`, and replace "there is no
signal" with "we can rule out an edge larger than X". Where MDE exceeds the cost hurdle, say so
explicitly — the result is uninformative, not negative.

---

### HIGH

---

#### H-1 — The IC test points at reversal, and reversal was never tested

**`backtests/ic.py:42-58`; `backtests/rotation.py:41`; `STRATEGY.md:32-38`**

Eleven of the twelve IC cells are negative, and the pattern is **monotone in both lookback and
horizon** (lb=7/fw=7: −0.035 → lb=60/fw=21: −0.083). That is the textbook signature of a long-horizon
reversal effect, not a random scatter. `STRATEGY.md:38` dismisses it in half a sentence
("slightly negative if anything, i.e. mild reversal, and not significant either") and moves on.

Then `rotation.py:41` backtests **only the momentum direction**:

```python
target = sorted(scores, key=lambda p: -scores[p])[:topk]
```

Descending sort, top-k. The bottom-k (buy the 60-day losers) strategy — the one the IC table
actually points at — was never run, in a 36-cell grid where flipping one minus sign would have
produced 36 more cells for free. The CI lower bounds reach −0.252, implying a reversal edge of up
to ~6% per reallocation could not be ruled out.

**Remedy:** Run `rotation.py` with `key=lambda p: scores[p]` and report the mirror grid. If the
reversal grid also loses to hold-LINK, that is a much stronger statement than the current one-sided
test, and it costs nothing to produce.

---

#### H-2 — `rotation.py` charges roughly double the correct fees on two thirds of the grid

**`backtests/rotation.py:46-55`**

Two defects in the same block. First, dead code that does nothing:

```python
for p in holding:
    c = TAKER + spreads.get(p, 0.0005)
    cash *= (1 - c/len(holding))*0 + 1     # <- multiplies by exactly 1.0
```

Second, and consequential, the turnover calculation:

```python
turn = len(set(target) ^ set(holding or []))/max(len(target) or 1,1)
```

The **symmetric** difference divided by `len(target)` double-counts every swap. Measured:

| holding | target | as coded | true turnover | overstated |
|---|---|---|---|---|
| [A] | [B] | 1.00 | 1.00 | 1.0× |
| [A,B] | [B,C] | 1.00 | 0.50 | **2.0×** |
| [A,B,C] | [B,C,D] | 0.67 | 0.33 | **2.0×** |
| [A,B] | [A,C] | 1.00 | 0.50 | **2.0×** |

`topk=1` is correct (clipped at 1.0). **`topk ∈ {2,3}` — 24 of the 36 cells — pays double fees.**

The headline results built on this grid (`STRATEGY.md:43-46`: "grid median final multiple 1.081 vs
hold-LINK 1.456", "only 11 of 36 cells beat hold-LINK", "fees consumed 13%–97% of capital") are
therefore **biased in favour of the conclusion the strategy reached**. This is the one place where
a coding error and the desired answer point the same way, which is the configuration that most
warrants suspicion.

Minor, same file: `equity.append(cash)` fires once per `hold_days` block (`:62`), so the max
drawdowns at `:64-66` are computed on a coarse grid and **understate** true drawdown — a bias in the
opposite direction, which does not cancel the fee bias.

**Remedy:** `turn = len(set(target) - set(holding)) / max(len(target),1)`; delete the dead loop;
append equity per bar. Re-run and update `STRATEGY.md:43-46` and `REGISTRY.md:R3` with the corrected
numbers.

---

#### H-3 — Cross-sectional excess return is compared against a long-only absolute cost

**`backtests/event_study2.py:36-40, 62`; `STRATEGY.md:183-188, 204-205`; `scripts/edge.py:118-120`**

`event_study2.py:62` produces `r − mkt[i]`: the asset's forward return **minus the equal-weight
universe forward return**. This is a long/short, market-neutral quantity. It is then compared
directly against an absolute transaction cost (`COST = 1.69`, line 16) and used throughout the EV
chain — `edge.py:118-120` hardcodes `("vol_expansion", 1.75, 1.19)` etc. and prints
`net taker = exc − tk`.

**You cannot capture a cross-sectional excess with a long-only spot account.** Harvesting
`r_X − r_universe` requires shorting the universe, which Hard Rule 2 forbids. What the account
actually earns by rotating out of LINK into X is `r_X − r_LINK`.

The demeaning is defensible as a *statistical* control for beta, but the resulting number is then
treated as a *tradeable* return. The correct counterfactual for this account — excess versus the
**funding asset**, LINK — is never computed anywhere in the repository.

This cuts both ways and that is the point: it is not conservative, it is simply the wrong quantity.
On days when LINK underperforms the universe, the true tradeable excess is *larger* than the
reported figure; on days when LINK outperforms, smaller.

**Remedy:** Add a `r_X − r_LINK` variant to `event_study2.py` and `signal_combinations.py` and report
it alongside the universe-demeaned figure. That is the number the EV gate should consume.

---

#### H-4 — Calm-market fill data is used to price volatile-market trades, contradicting the system's own R5

**`scripts/edge.py:44-46`; `scripts/execution_stats.py:90-95`; `REGISTRY.md:30-34`; `data/execution_log.json`**

`REGISTRY.md:R5` states the principle correctly: *"Calm-market fill data can never apply to it."*
The code then does exactly what R5 forbids:

```python
# edge.py:44-46
st = execution_stats.summary(verbose=False)
obs = [v["mean_adverse_bps"] for v in st.values() if v.get("mean_adverse_bps") is not None]
adverse_pct = (sum(obs)/len(obs)/100.0) * sides if obs else 0.05 * sides
```

`st` is keyed by regime. Only `"calm"` exists (n=2). So `adverse_pct` is **the calm-regime number,
5.4 bps**, applied unconditionally to every trade including volatile-regime tactical rotations.
`edge.costs()` takes no `regime` argument at all.

The fill-probability path is handled correctly (`execution_stats.py:95` falls back to a 0.5 prior
for volatile) but the adverse-selection path is not. The system caught half of its own bug.

The evidence base is also thinner than presented. `data/execution_log.json` contains **two** fills,
placed within one second of each other on one pair in one market state. `STATE.md`'s execution
table reports "fill rate 100%, median latency 27.5s, adverse selection 5.4 bps/leg" from n=2 —
a fill *rate* from two observations carries essentially no information (95% CI on a 2/2 binomial
is roughly [16%, 100%]).

**Remedy:** Give `edge.costs()` a `regime` parameter; when no observations exist for that regime,
use an explicit conservative prior (e.g. 20 bps) and label it as assumed, exactly as
`maker_fill_prob` already does. Report n and a CI beside every measured execution statistic in
`STATE.md`.

---

#### H-5 — Survivorship and selection bias are never mentioned anywhere in the repository

**`scripts/universe.py:27-30, 88-98`; `STRATEGY.md:22-24, 64-65`**

I grepped the full repository for `surviv|delist|look-ahead|leakage|out-of-sample|walk-forward|holdout`.
Before the concurrent session added `shadow.py`, **not one of these words appeared in any strategy
document or backtest.**

The universe is built from assets that are listed **today**, with **today's** liquidity:

```python
MIN_USD_VOL_24H = 3_000_000      # universe.py:27
MIN_TRADES_24H  = 1_500          # universe.py:28
MAX_MIN_NOTIONAL_FRAC = 0.35     # universe.py:30 — gate depends on TODAY'S portfolio size
```

240 bars of history are then pulled for exactly that survivor set. Three distinct problems:

1. **Delisted / collapsed assets are absent.** Any asset that died or lost liquidity in the window
   is invisible. The universe's realised return is biased upward.
2. **The demeaning baseline inherits the bias.** `event_study2.py:40` demeans against this inflated
   universe mean, which **understates** every measured excess return — a bias toward the hold
   conclusion.
3. **The universe is a function of the current portfolio.** `universe.py:97` excludes pairs whose
   minimum order exceeds 35% of *today's* $51. A historical study over 240 bars is being run on a
   universe that is defined by a number that did not exist for 239 of those bars.

`STRATEGY.md:64-65` handles the *bull-market* half of this correctly ("the window is net bullish …
which if anything **favours** momentum strategies — and they still failed"). That is a good
argument. It does not cover survivorship, and survivorship pushes measured excess returns the other
way.

There is a further constraint the concurrent Q1 output exposes: any subset involving `momentum` or
`rel_str` — i.e. **every rule v4.0 actually uses** — is computable only from **2026-05-28, 120 days**
(`q1_output.txt`, sample-windows block), not 240 and not 691. The production rule's history is four
months in one regime.

**Remedy:** Add an explicit "Selection and survivorship" subsection to `STRATEGY.md` §3. Where
possible, reconstruct a point-in-time universe from historical `AssetPairs` snapshots; where not,
state the direction and rough magnitude of the bias. Start snapshotting `universe.json` on every
refresh so future backtests have point-in-time data.

---

#### H-6 — `tactical.scan()` swallows all exceptions silently; "0 of 37 qualify" may be "0 of far fewer"

**`scripts/tactical.py:141-152`**

```python
for c in cands:
    try:
        a = analyse(c["pair"], c["key"])
        if a: analyse... 
    except Exception: pass          # line 145
```

`analyse()` makes three sequential public API calls per pair (OHLC 1440, OHLC 240, Ticker), and
`evaluate()` triggers two more via `edge.costs()` plus another via `vol_regime()` — with
`edge.costs()` called **twice** per candidate (once at `:113`, again inside `edge.evaluate()` at
`:115`). That is roughly 200+ sequential rate-limited calls per scan. A single timeout drops a pair
from the scan **and** from the relative-strength median (`:147`) with no record anywhere.

The reported "**0 qualify.** … 37 eligible assets" (`STRATEGY.md:294`) therefore cannot be trusted
to have examined 37 assets. There is no count of successes, no count of failures, and no log line.

`analyse()` also returns `None` for any pair with <40 daily bars (`:38`) — newly-listed assets, the
most volatile cohort and the most likely to produce a qualifying move, are silently excluded.

**Remedy:** Log every exception with the pair name; report `analysed N / eligible M / errored K` in
the scan header and in `STRATEGY.md`; cache the `costs()` result instead of computing it twice.

---

### MEDIUM

---

#### M-1 — Holding 100% LINK is framed as a neutral default; it is a ±17% directional bet

**`STRATEGY.md:84, 132-137`**

`STRATEGY.md:84` prices Hold at **"Cost 0.00%"**. With 60d daily vol of 3.73% (`STRATEGY.md:52`), a
21-day horizon carries σ ≈ 3.73 × √21 ≈ **17.1%** — a one-sigma swing of roughly ±$9 on a $51
account, concentrated in a single mid-cap altcoin with its own protocol, exchange and regulatory
tail risks.

The document is not dishonest about this — `STRATEGY.md:132-134` says "Fully exposed to LINK … a
−42.7% 21-day outcome exists in LINK's history. Accepted." But the *table* that drives the decision
assigns that exposure a cost of zero, while crediting a diversified alternative with a 0.24% drag
benefit. The same table cannot treat volatility as a priced benefit in one row and a free good in
another.

The framing "matching the benchmark" is also doing quiet work. LINK is the benchmark because the
researchers happened to endow the account in LINK. That makes it the *scoring* baseline; it does
not make it a risk-neutral position.

**Remedy:** Add a "risk" column to the §5 table and populate the Hold row with the 21-day sigma.
Let the reader see that the zero-cost option is the highest-variance one.

---

#### M-2 — `STATE.md` presents a lucky coin flip as excess return; the journal is honest and the state file is not

**`STATE.md:20-21`; `data/execution_log.json`; `logs/journal.md:376-383`**

`STATE.md:20` header table: *"Excess vs benchmark **+$0.026** — from +0.00208442 LINK gained on the
exploratory round trip."*

The journal is exemplary about this (`logs/journal.md:376-383`): *"That was a coin flip that landed
well, not skill … Ex ante the expected value was roughly minus the fees … I will not cite it later
as evidence the approach works."* Good. But `STATE.md` — the file the session routine says to read
first for context — cites it in a headline metric with no caveat. The document that carries the
caveat is not the document that gets read for numbers.

Two arithmetic discrepancies in the same record:

- `logs/journal.md:379` says *"LINK fell 85bps within four minutes."* From `execution_log.json`:
  sell `6.932882 / 0.55 = 12.6052`, buy `6.870674 / 0.55208442 = 12.4450`. That is a **−1.27%**
  move, not 85 bps — off by 50%. Latencies recorded are 30s and 25s, not four minutes.
- `logs/journal.md:369` says *"No adverse selection on either fill"*, contradicted by the same
  file's own `adverse_bps: 4.7` and `6.1`. This one **was** caught and corrected at
  `logs/journal.md:452-458`, to the model's credit.

**Remedy:** Rewrite the `STATE.md:20` row as "Excess vs benchmark +$0.026 — **luck, not edge**; a
single unhedged round trip whose ex-ante EV was ≈ −$0.055 (see journal S5)". Correct the 85 bps
figure with an appended note (Hard Rule 6: append, do not edit).

---

#### M-3 — `edge.py`'s documented gate, its implemented gate, and its reported "required move" are three different things

**`scripts/edge.py:14, 70, 76`**

```python
EDGE_MARGIN = 1.5    # docstring line 14: "expected net gain must be >= 1.5x total cost"
...
passes = net >= c["total_pct"] * (EDGE_MARGIN - 1) and net >= MIN_ABS_EDGE_PCT   # line 70 -> 0.5x cost
...
required_move_pct = (c["total_pct"] * EDGE_MARGIN) / max(2*confidence - 1, 1e-9) # line 76 -> 1.5x cost
```

The comment says 1.5×, the gate enforces 0.5×, and the diagnostic prints the move needed for 1.5×.
A reader of the printed `required_move_pct` will conclude the system is three times stricter than
it is. `STATE.md:45` and `STRATEGY.md:269` each quote a different one of these.

Additionally, `net` on line 69 is scaled by `fill_p` but the right-hand side of the `passes` test on
line 70 is not — so the comparison is between a fill-discounted quantity and an undiscounted one.
Defensible as a deliberate safety margin, but it is neither documented nor intended as far as I can
tell.

**Remedy:** Rename `EDGE_MARGIN` to what it is, or change line 70 to `EDGE_MARGIN`. Make line 76
consistent with line 70. One number, one meaning.

---

#### M-4 — Live detector and backtested detector compute the same statistic differently

**`scripts/tactical.py:40-42` vs `backtests/event_study2.py:52-53`; `scripts/monitor.py:43-50`**

`event_study2.py:52-53` excludes the signal bar from the volatility baseline:
```python
rets=[(cl[j]/cl[j-1]-1) for j in range(i-30,i)]   # excludes bar i
v30=statistics.pstdev(rets); v1=abs(cl[i]/cl[i-1]-1)
```

`tactical.py:40-42` includes it:
```python
v30 = statistics.pstdev(rets[-30:])   # rets[-1] IS the current bar
v1 = abs(rets[-1])                    # v1 is inside v30's sample
```

The live `vol_ratio` therefore has its numerator inside its denominator's sample, which compresses
the ratio precisely when the move is large — the detector fires *less* readily than the version
that was studied. Same defect in `monitor.py:129-130`. Also, `tactical.py:57-59` builds the 30-day
range from `closes[-30:]`, which includes the current **incomplete** bar, and compares it to the
live `bid` — so `pos_in_range` is partly self-referential.

`monitor.py:43-50` uses `vol_expansion fire=2.5` while `tactical.py:16` uses `1.5`. The two
components of the same system disagree about what a volatility expansion is, and neither matches
the other's validation.

This is not look-ahead (no future data is used), but it means **no backtest in the repository
describes the behaviour of the code that is actually running.**

**Remedy:** Extract one `features(pair)` function used by `monitor.py`, `tactical.py` and every
backtest. `signal_combinations.py`'s decision-timestamp discipline (its docstring, lines 10-12) is
the right model — make it the shared implementation, not a parallel one.

---

#### M-5 — Multiple-testing correction is applied only to results the model wants to reject

**`REGISTRY.md:26-28`; `STRATEGY.md:56-58`; counted across all backtests**

Hypotheses tested across the program, before the concurrent session's additions:

| source | grid | tests |
|---|---|---|
| `ic.py:42-43` | 4 lookbacks × 3 horizons | 12 |
| `rotation.py:92` | 4 lb × 3 hold × 3 topk | 36 |
| `event_study.py:36-44` | 4 triggers × 2 horizons + 2 baselines | 10 |
| `event_study2.py:34-44` | 4 triggers × 2 horizons | 8 |
| autocorrelation (R4) | daily / 4h / 1h | 3 |
| `monitor.py:43-50` | 7 detector thresholds chosen | 7 |
| `tactical.py:16-24` | 5 conditions + confluence cut + gate | 7 |
| Test 3 drag | ρ scenarios | 1 |
| **total** | | **84** |

Bonferroni at α=0.05 over 84 tests → per-test α = 0.0006 → |t| ≳ 3.0. The largest |t| anywhere in
the corrected results is **1.85** (breakout). Nothing survives.

Correction is invoked exactly **once** in the entire repository — `REGISTRY.md:27-28`, to kill the
4h autocorrelation result (t=−2.31) against a family of 3. It is never applied to the 36-cell
rotation grid, the 12-cell IC grid, or the 8-cell event study. The direction of this inconsistency
happens to be conservative (correction only removes findings), but the selective application means
the document's statistical standard is "whatever kills the result in front of me".

**Credit:** the concurrent `signal_combinations.py` does this properly — 93 tests, Bonferroni
|t| ≥ 3.461, plus a 2,000-draw schedule-preserving permutation family-wise test giving observed
max|t| = 2.404 against a null median of 3.329, **family-wise p = 0.971**. This is the best piece of
statistics in the repository and should be the template for everything else.

**Remedy:** State a family-wise correction policy in `REGISTRY.md` and apply it uniformly, including
retroactively to R3 and R4.

---

#### M-6 — `event_study.py` and `event_study2.py` assume costless execution at the exact signal bar close

**`backtests/event_study.py:59-63`; `backtests/event_study2.py:55-60`**

The trigger is evaluated from bar `i`'s close, volume and range, and the forward return is measured
as `closes[i+h] / closes[i]`. Entry at `closes[i]` is the earliest instant the signal is knowable,
so this is **not** strictly look-ahead — but it is an idealisation that is unattainable in practice.
On a daily-bar strategy the monitor polls every 60s and a session takes minutes to launch and
decide; realistic entry is somewhere in bar `i+1`. No slippage-to-entry term appears anywhere.

`event_study.py:40` also iterates to `len(rows)-horizon` over a `rows` array whose final element is
the **incomplete current bar**, so the last few observations use a partial close.

Both studies are gross-of-cost at the measurement stage and costs are subtracted afterwards as a
flat constant (`COST = 1.69`, line 11/16) with no per-pair spread, no impact, and no adverse
selection — even though `edge.costs()` computes all three.

**Remedy:** Shift entry to `closes[i+1]` (or bar `i+1` open) and report the delta; that single
change measures the cost of the idealisation. Use per-pair measured spreads rather than a scalar.

---

### LOW

---

#### L-1 — `edge.costs()` overstates available depth by counting both sides of the book
`scripts/edge.py:34` sums bid-side and ask-side depth within 0.5% of mid into a single `near`
figure, then divides notional by it. A buy order can only consume the ask side, so `impact_pct` is
understated by roughly 2×. Negligible at $8–16 notional (impact computes to 0.0008%), but the
formula is wrong and will matter if the account grows.
**Remedy:** use the side actually being consumed.

#### L-2 — `rotation.py` computes drawdown on a coarse grid
`backtests/rotation.py:62-66` appends equity once per `hold_days` block, so intra-period drawdowns
are invisible. The reported "max drawdowns −24% to −81%" (`STRATEGY.md:46`) are **understatements**
— which, unusually, cuts against the document's argument.
**Remedy:** append equity per bar.

#### L-3 — `data/universe.json` is a frozen snapshot presented as dynamic
`STRATEGY.md:21` claims the universe is *"Built dynamically from Kraken's live markets … never
hardcoded."* True at build time; `tactical.py:136` and `monitor.py` read a JSON file written at
12:37 and used at 23:00+ with no staleness check. `monitor.py:28` has a 6h refresh but `tactical.py`
has none.
**Remedy:** add an age check and warn (or refuse) past `UNIVERSE_REFRESH_SEC`.

#### L-4 — Parameter naming that invites error
`tactical.py:30` names the parameter `universe_median_4h`; `tactical.py:147` passes it the median of
`mom_12h`. Functionally consistent, but one future edit away from a silent mismatch.
Also `tactical.py:142` calls `analyse()` without the parameter, so `rel` is always `None` on the
first pass and is patched at `:149-151` — two code paths computing `confluence`.
**Remedy:** rename to `universe_median_mom12h`; compute confluence in exactly one place.

#### L-5 — `success_probability` is capped at 0.62 but never floored against evidence
`tactical.py:96`: `min(0.50 + 0.03 * confluence, 0.62)`. At confluence 3 this is 0.59. The event
study found **no** reliable continuation edge, and the cross-sectional medians were all *negative*
(`STRATEGY.md:186-188`). A defensible reading of that evidence puts p at or **below** 0.50, which
would make `(2p−1) ≤ 0` and every tactical trade negative-EV by construction. The chosen anchor is
more generous than the evidence, in the one place where generosity is harmless because C-1 blocks
everything anyway.
**Remedy:** calibrate from `shadow.py` forward records; until then state that 0.50–0.62 is assumed,
not measured.

---

## Parameter sensitivity: would small threshold changes flip the conclusion?

Mostly **no — and that is itself the problem.** The system is not sitting near a knife edge; it is
sitting a very long way from one.

| perturbation | effect |
|---|---|
| `MIN_CONFLUENCE` 3 → 2 | none. Gate still requires σ ≈ 40%+ |
| `MOVE_TO_COST_MIN` 3.0 → 1.5 | none. `net ≥ 0.5%` binds first, not move/cost |
| `VOL_EXPANSION_MIN` 1.5 → 2.5 | changes which assets are *considered*; none qualify either way |
| `MIN_ABS_EDGE_PCT` 0.5% → 0.25% | still requires σ ≈ 18% |
| `success_probability` cap 0.62 → 0.75 | `(2p−1)` 0.24 → 0.50; **required move halves to ~7%** |
| `sides` 4 → 2 | cost 1.83% → 0.92%; **required move halves again** |
| cap 0.75 **and** 2 legs | required move ≈ **3.5%** — now genuinely reachable |

The conclusion is therefore **not** sensitive to the confluence thresholds that the review brief
worried about. It is entirely determined by three numbers that were never measured: the 0.62
probability cap, the 4-leg assumption, and the 0.5 volatile-regime fill prior. Change those three
and the system trades regularly. Leave them and it never trades. **The confluence rule is
decorative; the EV constants are the strategy.**

---

## Regime dependence: what breaks in a bear or chop market

1. **Every condition is long-biased.** `momentum_continuation` requires `mom_4h ≥ +2%`;
   `breakout_confirmed` requires `pos_in_range ≥ 0.95` **and** `mom_4h > 0`; `relative_strength`
   requires positive excess. In a sustained bear market, confluence ≥3 is nearly unattainable, so
   the tactical mode goes to zero exactly when the core position is losing most.
2. **The only defensive action is forbidden by C-3's arithmetic.** Hard Rule 2 bars shorting, so the
   sole bear-market response available is rotating to USD — which `STRATEGY.md:83` prices as
   negative EV on the strength of the unvalidated +0.117%/day drift estimate. **The system has no
   defensive branch at all**, and the reason it has none is an assumption, not a measurement.
3. **`breakdown` was measured at −0.41% (t=−1.28) and then discarded.** For a long-only account a
   negative post-breakdown drift is not a non-signal; it is a *reduce-exposure* signal. It was
   evaluated only as a buy candidate and rejected for not being one.
4. **The window is one regime.** 240 bars net bullish, and the conditions v4.0 actually uses have
   only **120 days** of history (`q1_output.txt` sample windows: `momentum`, `rel_str` and every
   subset containing them start 2026-05-28). Nothing in this repository has observed a bear market.
5. **Chop is the worst case and is untested.** Range-bound markets generate frequent breakout and
   vol-expansion fires that immediately mean-revert — precisely the "positive mean, negative median"
   profile the event study already found (`STRATEGY.md:186-188`). A gate keyed on the *mean* would
   bleed; the current gate is saved from this only by being unreachable.

---

## Is "hold the benchmark and almost never trade" defensible? Both cases, fairly.

### The strongest case that this system is far too conservative

**1. The gate is not a judgement, it is a bug.** C-1 is the whole argument. A system whose trading
branch requires a 23% daily sigma has not decided not to trade — it has failed to build a
functioning decision rule. The five sessions of prose about discipline describe a gate that was
never open. The researchers are being shown restraint; what exists is an arithmetic error.

**2. Three independent safety factors are multiplied where one was warranted.** The expected move is
already conservative (0.5σ, chosen explicitly to avoid the discredited +2.40%). It is then
multiplied by `(2p−1) = 0.24`, then by `fill_p = 0.5`, then required to clear `3 ×` cost, then
required to clear `0.5 ×` cost again, then required to exceed 0.5% absolute. Each step is
individually defensible; **compounded, they impose a ~25× hurdle that no defensible single
assumption would produce.** Conservatism applied at five independent stages is not conservatism, it
is innumeracy.

**3. The objective is being quietly substituted.** `CLAUDE.md` §1: *maximize the final USD value*,
with *"losing some or all of the capital is an accepted outcome"* and *"capital preservation is not
the goal."* The strategy optimizes something else — expected value **net of a self-imposed
requirement never to be wrong**. Under the stated objective, with the account explicitly scored
*against hold-LINK*, a position with zero expected alpha but meaningful variance gives roughly a 45%
chance of beating the benchmark. The current position gives a **structurally guaranteed $0.00**
(`STRATEGY.md:135`: *"Matching the benchmark means never beating it"*). The document states this
outcome and accepts it without ever asking whether ~1.8% of EV is a fair price for converting a
certain tie into a coin flip on a 21-day horizon. That trade-off is never analysed. It should be.

**4. The tests cannot support the conclusion they carry.** C-6: MDEs of 3–7% against a 1.83% hurdle.
Confidence intervals spanning +2.6% per reallocation. The honest statement is "I cannot find an
edge with these tools", and the tools are 240 daily bars of stdlib Python. The system has escalated
that to "there is no edge", and then to "therefore the machinery is correct to be silent".

**5. Reversal was never tested** (H-1). Eleven of twelve IC cells negative, monotone in lookback,
and the 36-cell grid ran only the momentum direction. Flipping a sort key would have doubled the
search for free. That is not thoroughness.

**6. Cost reduction was abandoned rather than attacked.** Cost is correctly identified as the
binding constraint (`REGISTRY.md:Q3`) and then treated as a constant. The 4-leg assumption (C-4) is
the single largest term and is self-imposed. A 2-leg re-allocation at 0.92% was found to pass
(`STRATEGY.md:204`, *"+0.94% — passes gate"*) and was declined on an **argued, unmeasured**
adverse-selection concern — the same concern the model elsewhere insists on measuring rather than
arguing. It then spent a session building the tactical machinery instead of placing the one small
order that would have measured it.

**7. Five sessions, two trades, both in the first hour of live trading.** The falsification criteria
(`STRATEGY.md:104-114`) are all *external* triggers — the market must change for the strategy to
change. There is no trigger of the form "if I have taken zero positions in N days, my gate is
probably miscalibrated; measure it." A strategy with no self-directed failure mode is not being
tested.

### The strongest case that it is not conservative enough

**1. 100% of capital in one mid-cap altcoin, priced at zero risk.** M-1: σ ≈ 17% over the horizon,
a −42.7% 21-day precedent in LINK's own history, and `STRATEGY.md:84` records the cost of this
position as **0.00%**. Every "we cannot afford to pay 1.83%" argument is made while carrying a ±17%
uncompensated exposure. If 1.83% is material enough to block all action, 17% of variance is
material enough to require a decision, and the document treats it as the absence of one.

**2. Live trading is armed and the only thing preventing trades is a bug.** Fix C-1 — which any
future session might reasonably do, believing it is repairing a miscalibration — and the system
immediately begins taking 15–30% positions on a rule with **no validated edge** (C-5), sized by an
uncalibrated expected-move model (`tactical.py:88`), with probability assumptions more generous than
the evidence (L-5), executing on a cost model that uses calm-market fills to price volatile-market
trades (H-4), on an asset set chosen by four correlated momentum proxies (C-2). The safety margin
between this system and a reckless one is an arithmetic error, not a control.

**3. `SIZE_STRONG = 0.40`** (`tactical.py:27`) authorises 40% of the account into a single
short-horizon momentum position. On a $55 account, four legs at ~$8–16 notional each, against a
predicted move whose model has never been calibrated forward, with `MAX_QUEUE = 200` pending
opportunities and **multiple simultaneous positions permitted** (`STRATEGY.md:276-277`). There is no
portfolio-level exposure cap anywhere in the code — only per-position sizing. Three simultaneous
30% positions would be 90% of the account in tactical alt momentum.

**4. Exit discipline is prose, not code.** `tactical.py:124-129` returns an `exit_thesis` **dict**.
Nothing consumes it. No process monitors an open tactical position, no stop is placed on the
exchange, no invalidation check runs between sessions. `monitor.py` explicitly never places orders
(`monitor.py:17`). So "invalidation at 1 daily sigma, exit immediately" depends on a Claude session
happening to run within the next three hours and happening to act. A 1-sigma stop on a 6%-daily-vol
asset can be blown through several times over in a 3-hour gap. **The system can enter a position it
has no mechanism to exit.**

**5. Two fills is not an execution model.** H-4. `STATE.md` reports a 100% fill rate from n=2 and
`edge.py` consumes a 5.4 bps adverse-selection constant from the same two observations, in
violation of the repository's own R5.

---

## Verdict

**The core conclusion — hold LINK, trade rarely — survives adversarial review. The reasoning
offered for it does not.**

What genuinely survives, and it is a real result: where the data has adequate power, the measured
edge is smaller than the cost. `vol_exp` alone, n=2,583 events over 502 clustered days with an MDE
of 0.94%, shows **+0.59% mean excess (t=2.18)** against a **1.83%** four-leg hurdle, or ~0.92%
two-leg. That is a properly-powered measurement of a real but insufficient edge, and it is the
single best argument in the repository. The concurrent `signal_combinations.py` — Bonferroni over 93
tests, permutation family-wise p = 0.971 — independently confirms that no *combination* rescues it.
On the evidence, a $51 account paying 0.40–0.83% per leg over 21 days is a genuinely hard place to
find edge, and the model is right about that.

What does **not** survive:

- The claim that v4.0's tactical mode is "armed" and "will execute the moment something clears"
  (`STRATEGY.md:224-226`). It cannot clear. The gate needs a 23–40% daily sigma (C-1).
- The claim that "0 of 37 qualify" is market evidence. It is a code property, from a scan that
  silently swallows errors (C-1, H-6).
- The claim that confluence requires "≥3 **independent** conditions" (C-2).
- The claim that the confluence rule was "derived from R1/R2" (C-5).
- "There is no cross-sectional momentum signal in this universe" — the tests cannot rule out an edge
  larger than the hurdle (C-6).
- Test 3's rejection of diversification, which applies volatility drag in one row and ignores it in
  the row that would overturn the whole conclusion (C-3).
- The rotation grid's headline numbers, inflated by a 2× turnover bug on 24 of 36 cells (H-2).
- Any claim of *performance*. The account is up because LINK is up. The journal says this plainly
  (`logs/journal.md:568-570`, "that spread is LINK appreciating … not strategy") and `STATE.md:20`
  does not (M-2).

So: **right answer, unearned.** The system reached a defensible position through a chain containing
a fatal arithmetic error, an untested production rule, a selectively-applied statistical standard,
and one genuine coding bug that happened to push toward the answer it chose. A conclusion that would
be correct anyway is not validated by arriving at it this way — and the same chain, pointed at a
market where an edge *did* exist, would have missed it and reported the miss as rigour.

On the conservatism question specifically: this system is **too conservative in the branch it can
control and not conservative enough in the branch it cannot.** It refuses a 2-leg re-allocation with
a measured +0.94% point estimate on an argued, unmeasured fill concern, while holding ±17% of
undiversified directional exposure it prices at zero and has no mechanism to exit. That is not a
risk posture; it is the absence of one.

---

## The single most important thing that should change

**Fix the EV gate so that it expresses uncertainty exactly once, then re-derive the hold decision
from a gate that can actually open.**

Concretely, before anything else:

1. Correct `STRATEGY.md:271` — the documented "~5.5% expected move" is false; the implemented
   requirement is ~11–15%, reachable only at 23–40% daily sigma. State this as a defect, not a
   design choice.
2. Stop multiplying safety factors. Choose **one** place to express uncertainty — the
   probability-weighted net EV is the right one — and remove the redundant `3× move/cost` gate, the
   `0.5× cost` margin and the `0.5%` absolute floor, or justify each as a distinct, named risk.
3. Make `sides` a decision variable, not the constant `4` (`tactical.py:113`). Price the 2-leg
   re-allocation the system's own premise (IC ≈ 0) implies, and make the case for returning to LINK
   on evidence rather than incumbency.
4. Then re-run the decision. If it still says hold — and given `vol_exp`'s +0.59% against a 0.92%
   two-leg hurdle it very plausibly will — **that** is a conclusion worth reporting, because it will
   be the output of a rule that could have said otherwise.

Second priority, because it is the difference between a defensible hold and a lucky one: put a
**minimum detectable effect** next to every null result in `STRATEGY.md`, and stop writing "there is
no signal" where the data only supports "I cannot detect one smaller than 3–7%".

---

## Addendum — `REGISTRY.md` R6, published during this review

`REGISTRY.md` gained entry **R6** (Q1 signal combinations) after this review was drafted. It
materially changes two findings and confirms a third. Recorded here rather than by editing the
findings above, so the sequence stays honest.

**C-5 (confluence rule shipped untested) — now closed, retroactively.** R6 is the missing test:
93 tests, 0 surviving Bonferroni, permutation family-wise p = 0.971, with the observed max |t| of
2.404 falling *below* the null **median** max |t| of 3.329. Randomly-selected assets typically
produce a better-looking best result than the real signals do. That is a stronger and more damning
result than anything I found, and it is correctly self-reported as such. The criticism that remains
is only about ordering: the rule went to production, was described as "armed", and had its silence
reported as evidence, before this existed.

**M-5 (selective multiple-testing correction) — substantially remedied.** R6 applies a uniform,
pre-stated correction and reports it against a result the model would have preferred to keep. It
should now be applied retroactively to R3 (36-cell grid) and R4.

**C-6 (power) — confirmed and sharpened by the authors themselves.** R6 finds every top combination
is driven by **one asset-day** (NILUSD, 2026-09-20, +104% in three days); removing it takes the best
combination from +5.86% to +1.72%, i.e. **net −0.11%**. A "result" that rests on a single
observation out of 10–26 clustered days is exactly the MDE problem in C-6, made concrete.

**A2's qualification is the right call and should propagate.** The registry now states that
confluence "buys lottery tickets, not edge" and is retained as a **risk filter**, not a source of
expected return. `STRATEGY.md` §v4.0 still describes it the old way — `STRATEGY.md:243, 253-256`
("only when several independent conditions coincide") should be brought into line, and C-2 still
applies: the conditions are not independent, so even as a *filter* its selectivity is overstated.

**Q1 closed, Q3 (cost) promoted to the binding constraint.** This is the correct prioritisation and
it converges with this review's top recommendation. One caution: Q3 is framed as *"Can execution
cost be structurally reduced below 4 legs?"* — which still treats 4 legs as the baseline to be
argued down from. **C-4 stands:** under the system's own IC ≈ 0 premise there is no justification
for returning to LINK at all, so 2 legs is the correct *default* and 4 legs is the claim requiring
evidence. Reframing Q3 that way roughly halves the hurdle before any cleverness is applied.

**Net effect on the verdict:** the hold conclusion is now better supported than it was when this
review began — but by R6, not by anything in v4.0. C-1 (the unreachable gate) is untouched by R6 and
remains the top finding: the system still cannot trade even if a qualifying opportunity appeared,
and still documents its own threshold at roughly one third of its true value.
