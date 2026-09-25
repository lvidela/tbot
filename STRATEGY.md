# STRATEGY

**Version:** 5.0 — 2026-09-24 (post research program: four agents, Q1–Q4)
**Allocation:** 100% LINK (4.1944857200). **Live trading: ENABLED** but no trade currently justified.
**Monitor:** `trading-monitor.service`, continuous. **Benchmark:** $51.3087 (immutable, `data/benchmark.json`).
**Fee tier: MEASURED — 0.80% taker / 0.40% maker.**

---

## 1. Hypothesis

> Across the eligible Kraken Spot universe, no signal I can measure produces an expected
> return large enough to overcome a 1.60% round-trip cost over a 21-day horizon. Therefore the
> allocation that maximizes expected final USD value is the one that pays no transaction costs.

This is a claim about **this account at this size on this horizon**, not a claim that markets are
efficient or that rotation never works. It is re-tested continuously (§7).

## 2. Evidence

**Universe.** Built dynamically from Kraken's live markets (`scripts/universe.py`), never hardcoded.
622 USD pairs → **37 eligible** after deterministic gates: online USD pair, ≥$3M 24h volume,
≥1,500 trades, spread ≤25 bps, book depth ≥20× trade size within 0.5% of mid, and minimum order
≤35% of portfolio. 585 rejected, each with a recorded reason.

**Test 1 — does momentum predict returns? (the decisive test)**
Spearman rank correlation between trailing return and forward return, pooled across 33 non-stable
eligible assets over 240 common daily bars. Parameter-free, so nothing can be tuned to look good:

| lookback → horizon | 7d | 14d | 21d |
|---|---|---|---|
| 7d | −0.035 (t −0.86) | +0.002 (t +0.04) | −0.026 (t −0.39) |
| 14d | −0.014 (t −0.36) | −0.003 (t −0.06) | −0.044 (t −0.63) |
| 30d | −0.025 (t −0.58) | −0.038 (t −0.65) | −0.074 (t −1.07) |
| 60d | −0.045 (t −1.06) | −0.050 (t −0.81) | −0.083 (t −0.96) |

**All 12 cells: |t| < 1.1. There is no cross-sectional momentum signal in this universe.** The ICs
are slightly negative if anything, i.e. mild reversal, and not significant either.

**Test 2 — rotation backtest (36-cell grid).** Cross-sectional momentum, top-k, with 0.80% per leg
plus measured spreads:

- **Grid median final multiple 1.081 vs hold-LINK 1.456.** The typical parameterisation *loses* to
  simply holding.
- **Only 11 of 36 cells beat hold-LINK** — worse than a coin flip.
- Fees consumed **13%–97%** of capital. Max drawdowns −24% to −81%.
- Adjacent cells disagree violently: (60,7,1)→2.005 but (60,7,2)→1.033 and (60,3,1)→1.254. **A real
  edge produces smooth parameter surfaces; this is a noise field.** The good cells are overfitting
  artefacts, consistent with Test 1 showing no underlying signal.

**Test 3 — the diversification case**, the strongest structural argument for moving:
LINK 60d daily vol 3.73% → 21-day volatility drag 1.46%. An equal-weight 3-asset portfolio at
ρ=0.75 (crypto majors are highly correlated) has drag 1.22%.
**Benefit 0.24%. Cost to implement 1.60%. Net −1.36%.** Rejected.

**Test 4 — carried forward and re-verified:** LINK lag-1 return autocorrelation remains
indistinguishable from zero (daily t −0.55, 4h t −2.31 failing Bonferroni, 1h t −1.32); implied
edge 0.079%/trade against a 1.643% round trip.

## 3. Assumptions

- Taker 0.80% / maker 0.40% — **measured** via `TradeVolume`, not assumed. Re-checked each session.
- Spreads and depth measured live per pair; slippage estimated as half-spread + book impact.
- 240 common daily bars limits history (newer listings); the window is net bullish (median eligible
  asset +39%), which if anything **favours** momentum strategies — and they still failed.
- Correlation ρ≈0.75 for the drag calculation; the conclusion holds for any ρ > 0.3.

## 4. Applicable market regime

A **normal-volatility, no-strong-trend** regime: mean |daily move| ~3%, spreads 0–25 bps, no
liquidity stress. The hypothesis is explicitly **not** claimed to hold in a volatility explosion
(where moves dwarf fixed costs) or a liquidity crisis. Those are escalation triggers, not exceptions
quietly assumed away.

## 5. Expected edge and transaction costs

**Expected edge from trading: zero, within measurement error.** That is the finding, stated plainly.

| Action | Cost | Expected gain | Net |
|---|---|---|---|
| Rotate LINK → any asset | 1.60% ($0.82) | 0.00% (IC ≈ 0) | **−1.60%** |
| Diversify into 3 assets | 1.60% ($0.82) | 0.24% (drag) | **−1.36%** |
| Move fully to USD | 0.80% ($0.41) | negative (forgoes LINK drift) | **< −0.80%** |
| **Hold** | **0.00%** | — | **0.00%** |

Holding is the only action with a non-negative expected value. It is not the passive default; it is
the maximum of the set.

## 6. Position sizing

Portfolio $51.31 materially improves granularity: LINK minimum order is now **13.1% of the
portfolio (7.6 discrete lots)**, down from 31% at $22. XRP/ETH/BTC offer 12–21 lots. Partial
allocations are now feasible, and **the strategy is authorized to use them** the moment a signal
justifies one. Capital is not required to be fully deployed, and no trade need use 100%.

Sizing rule when a trade is justified: size so that expected edge × notional > 3 × total expected
cost, never below `ordermin`, never above the book depth constraint.

## 7. What would falsify this, and how it is tested

The monitor runs continuously and escalates on any of these. **Each is a live re-test, not a
promise to reconsider someday:**

| Trigger | Threshold | Why it changes the answer |
|---|---|---|
| Momentum IC becomes real | \|IC\| > 0.15 with \|t\| > 3 | Edge = IC × dispersion; would begin to clear 1.60% |
| Autocorrelation strengthens | \|lag-1\| > 0.30, \|t\| > 3 | Direct reversal edge |
| Volatility regime break | mean \|daily move\| > 8% | Edge scales with move size; costs are fixed |
| Fee tier collapse | taker < 0.10% | Cost hurdle falls 8× |
| Breakout / breakdown | 30d range extreme, range ≥3% wide | Possible regime change |
| Volume spike | 3× 30d average | Possible information event |
| Spread blowout | > 50 bps | Liquidity stress; also raises holding risk |
| Relative strength | 14d excess > 20% vs held | Directive §9 comparison |
| Portfolio vs benchmark | −15% divergence | Something is wrong with my reasoning or execution |

**Symmetric falsification:** if a cost-covering edge appears and I keep holding anyway, that is a
failure of this strategy and must be recorded as one.

## 8. Why this is preferable to the previous strategy

v1.1 reached "hold LINK" from a **single-asset** test on LINK alone. v2.0 reaches the same allocation
from a **universe-wide** test across 37 eligible assets with three independent methods (IC, backtest
grid, drag arithmetic). The conclusion did not merely survive a broader test — it was re-derived from
scratch under the new regime, larger portfolio, and wider universe, as directed.

**The material change is not the allocation, it is the machinery.** v1.1 revisited its assumptions
every 3 hours only when a session happened to run. v2.0 watches 37 markets continuously and escalates
within a minute of a qualifying event. The allocation is the same; the *reason* it is the same is now
continuously verified rather than periodically assumed.

## 9. Risks

- **Fully exposed to LINK.** A −42.7% 21-day outcome exists in LINK's history. Accepted: the prompt
  accepts loss, and every hedge costs more than it saves at this size.
- **Matching the benchmark means never beating it.** This is the honest consequence: the benchmark is
  hold-LINK and I hold LINK, so excess return will be ~$0 minus nothing. I cannot manufacture excess
  return from a signal that does not exist without paying 1.60% to find out.
- **21 days is too short for any edge to express.** Even a real signal would get ~1–2 rebalances —
  a single draw from a wide distribution. Sample size, not just edge size, argues against trading.
- **Overfitting risk in my own tests.** Mitigated by leading with the parameter-free IC test and
  reporting the full grid rather than its best cell.
- **Monitor could miss a regime change** or escalate spuriously. Bounded: it cannot trade.

## Previous Strategies

**v1.1 (2026-09-24, session 2) — hold LINK, single-asset analysis.** Held for ~1 hour of experiment
time; **0 trades, $0 fees, 0% deviation from benchmark.** Replaced because the directive expanded the
mandate to the full Kraken Spot universe with continuous monitoring, and its evidence base (LINK
alone) was too narrow to justify an allocation across 37 eligible assets. Its conclusion was
re-derived, not carried forward.

**v1.0 (2026-09-24, session 2) — hold LINK, fee tier unknown.** Superseded within the session by
v1.1 when `TradeVolume` revealed the real tier (0.80%, double the assumption). **0 trades.** Its
method of testing the conclusion across the full plausible fee range rather than a point estimate is
why the measurement required no change of course.

**v0 (session 1, proposed, never implemented) — LINK mean reversion.** Rejected before any capital
was committed when the autocorrelation it assumed proved statistically absent. **0 trades.**

---

# v3.0 — Aggressive Opportunistic Mode

## Hypothesis under test

> The monitor's own triggers (breakout, breakdown, volatility expansion, volume spike) precede
> moves large enough to pay for the transaction costs of acting on them.

This is a different and more promising hypothesis than v2.0's cross-sectional momentum, because
it targets *event-conditional* returns rather than a persistent ranking signal.

## Evidence — event study across 32 eligible assets

**Naive measurement looked strongly tradeable:** forward 3d returns after `vol_expansion`
averaged **+2.40% (t=+4.96)** and after `volume_spike` **+1.79% (t=+3.41)**, both above the
1.69% taker hurdle.

**That result does not survive correction.** Two flaws inflated it: forward windows overlap, and
32 correlated assets firing on the same day are not 32 independent observations. Re-run with
**cross-sectional demeaning** (subtract the same-day universe return, isolating selection from
"the market rose that day") and **date clustering** (one day = one observation):

| trigger | events | days | mean excess 3d | t (clustered) | median | P(>cost) |
|---|---|---|---|---|---|---|
| breakout | 515 | 121 | +1.22% | +1.85 | −0.84% | 32.2% |
| vol_expansion | 245 | 80 | +1.75% | +1.19 | −1.29% | 33.5% |
| volume_spike | 327 | 113 | −0.00% | −0.00 | −1.97% | 34.6% |
| breakdown | 489 | 100 | −0.41% | −1.28 | −0.71% | 26.8% |

`vol_expansion` fell from **t=+4.96 to t=+1.19**. Most of the apparent edge was market-wide
moves and pseudo-replication. **Every median is negative** — the typical event loses money and
the positive means are carried by a few outliers. Only ~1 event in 3 clears costs.

## The cost insight this produced

Cost, not signal, is the binding constraint — so I added **maker (post-only limit) execution**,
which halves the fee and avoids crossing the spread: **0.400% vs 0.831% per leg, measured.**

**But legs must be counted honestly.** A round-trip tactical rotation is **4 legs**:

| | 2 legs (one-way) | 4 legs (round trip) |
|---|---|---|
| taker cost | 1.67% | 3.33% |
| maker cost | 0.81% | 1.62% |
| `vol_expansion` net (maker) | **+0.94% — passes gate** | **+0.13% — fails** |
| `breakout` net (maker) | +0.41% — fails | −0.40% — fails |

## Decision: HOLD, with the system fully armed

Only one configuration passes: a **one-way** re-allocation on `vol_expansion` at maker pricing.
I am not taking it, for three reasons I want on the record:

1. **t = 1.19.** The data is consistent with zero edge. The +0.94% is a point estimate whose
   confidence interval comfortably spans zero.
2. **The median is −1.29%.** Capturing a right-skewed mean requires many trades. With 21 days
   left I get perhaps 3–6, so I would most likely realise the median, not the mean.
3. **Adverse selection is unmodeled and points the wrong way.** A post-only order rests until
   someone crosses it — which in a fast market means you get filled precisely when price is
   moving against you. The maker saving is most reliable for patient trades and least reliable
   for volatility-chasing, which is exactly what this signal is. The +0.94% assumes a fill
   quality this strategy is least likely to get.

**This is not a preference for inactivity.** The gate is a modest 1.5x margin, the limits are
gone, and the system will execute the moment something clears. What would make me trade:
a measured excess with |t| > 2.5 **and** a positive median, or a signal ≥3% excess where the
point estimate survives a 4-leg cost, or a volatility regime where moves dwarf fixed costs.

## Known weaknesses

- 240 common bars over a net-bullish window; short history on newer listings.
- Adverse selection and fill probability are not yet empirically measured — they are argued.
  If I trade a maker order, the realised fill rate becomes the first thing to record.
- The 21-day horizon is the hardest constraint: too few trades for any edge to express.


---

# v4.0 — High-Volatility Tactical Mode (added alongside the core strategy)

## Hypothesis

> Short-lived, high-volatility dislocations occasionally produce moves large enough to clear a
> ~1.8% four-leg execution cost on a $55 account — but only when several independent conditions
> coincide. Volatility alone is not an edge and is never sufficient.

This runs **alongside** the core benchmark strategy; it does not replace it. Core exposure stays
in place unless a tactical position is actually opened.

## Why volatility alone is excluded, in code

The event study behind v3.0 is the reason. The naive volatility-expansion result (+2.40%,
t=+4.96) collapsed to **+1.75%, t=+1.19, with a negative median** once cross-sectionally
demeaned and date-clustered. So `tactical.py` requires a **confluence of ≥3 independent
conditions** from: volatility expansion (≥1.5× 30d vol), volume confirmation (≥3× 30d average),
momentum continuation (4h ≥ +2% and 12h positive), breakout confirmation (≥95% of a ≥3%-wide 30d
range *with* positive momentum), and relative strength (≥3% over the universe median).
**Spread is a veto, not a contributor** — it can only disqualify.

Expected move is deliberately **not** taken from the discredited naive figure. It is
`0.5 × daily sigma`, uplifted 15% per confluence point above the minimum. Continuation
probability is anchored at `0.50 + 0.03 × confluence`, capped at **0.62** — the event study found
no reliable continuation edge, so confluence buys a modest increment, never certainty.

## The EV gate

A tactical round trip is **4 legs** (sell core → buy tactical → sell tactical → rebuy core).
At ~$55 that is **1.83% all-in** at maker pricing, 3.26% at taker.

Trade only when **expected gross move ≥ 3× all-in cost** *and* probability-weighted net > 0
*and* the standard gate (net ≥ 0.5%, ≥ 0.5× cost) passes. At current costs that means a
**~5.5% expected move** — which is the point: only genuinely large opportunities qualify.

## Sizing and exits

15–30% of portfolio, scaling with confluence; up to 40% only for exceptional confluence with
adequate liquidity. Multiple simultaneous tactical positions are permitted, and concentration is
allowed when one opportunity is materially stronger. Core exposure is never forcibly liquidated
for diversification's sake.

Every position carries an exit thesis **before entry**, volatility-adjusted rather than fixed:
invalidation at 1 daily sigma below entry; trailing activates at +1 sigma; exhaustion exit when
4h momentum turns negative or volume falls below its 30d average; immediate exit on invalidation.
**Never average down. Never add to a loser because volatility rose.**

## Execution

Post-only preferred when the opportunity survives waiting. **A failed post-only never
auto-converts to taker** (`edge.should_cross_spread`) — crossing requires the taker route to be
independently positive-EV. Do not sacrifice a rapidly decaying high-EV opportunity purely to
capture maker fees; re-evaluate from fresh data and decide independently whether to repost,
cross, reduce size, or abandon.

## Current scan result (2026-09-24, 37 eligible assets)

**0 qualify.** Strongest candidate ONDOUSD: confluence 4/5, volatility 4.23×, volume 7.05×,
relative strength +17.75% — a genuinely strong setup. It fails on **move/cost 1.89× < 3.0×**.
It had also already run **+20.7% in 12 hours**, which is precisely the "already exhausted move"
the directive warns against buying blindly.

## Concurrency: opportunities are no longer lost

Previously a qualifying event arriving while a Claude session ran was **discarded** — 3 were
lost that way, and my stated rationale ("stale anyway") was a rationalisation. Now every
opportunity is written to a persistent queue (`oppqueue.py`) regardless of escalation state.
Duplicates merge keeping the **stronger** magnitude. The next session drains the queue ranked by
magnitude and **revalidates against fresh market data**, discarding anything older than 60
minutes or whose edge has decayed. **Order execution remains serialized** by the session flock,
so two sessions can never place conflicting orders.

## What would falsify this

Tactical trades that individually clear the 3× gate but collectively underperform the core
allocation net of fees. The learning log (`execution_stats.py`) records signal combination,
regime, expected vs realised move, MFE/MAE, slippage and net P&L per trade so the question
"which combination actually pays" is answered with data rather than argument.


---

# v5.0 — After the research program (Q1–Q4)

Four parallel research agents attacked the strategy. **Two found real defects in my own work,
one of which biased toward the conclusion I had reached.** Everything below is net of costs.

## Corrections to things I previously asserted

| Claim I made | Status |
|---|---|
| "Tactical gate requires ~5.5% expected move" | **WRONG by ~2.5×.** True requirement was 11.8–15.7%. Four haircuts stacked multiplicatively: `(2p−1)=0.24`, fill prior 0.5, the 3× rule, the 1.5× margin — uncertainty charged four times for one doubt. |
| "0 of 37 assets qualify" | **Not a market finding.** It was a property of my code. Now labelled as such in the output. |
| "A tactical round trip is 4 legs / 1.83%" | **WRONG.** Leaving LINK is a one-time campaign cost, and the terminal "buy back LINK" leg does not exist — we are valued in USD on 2026-10-15. **2 legs, 0.92%.** |
| "≥3 *independent* conditions" | **False.** Momentum, breakout and relative strength are all monotone in the same 4–12h price change. `VOL_EXPANSION_MIN=1.5` is *identical* to `CALM_VOL_RATIO=1.5`, so condition #1 is definitionally "regime == volatile". |
| "IC ≈ 0, there is no signal" | **Overstated.** MDE is +3.31% to +7.51%. The defensible claim is "I cannot detect an edge smaller than 3–7%". |
| Volatility-drag argument (Test 3) | **Void — double-counting.** Realised returns already include drag. |
| Rotation grid "median 1.081" | **Turnover bug, 2–4× fee overstatement, biased toward my conclusion.** Fixed and re-run: median **1.220** vs hold-LINK **1.571**. Conclusion held, numbers were wrong. |

## What the research established

**Q1 — no signal combination has edge.** 93 tests, **0 survive Bonferroni**. A
schedule-preserving permutation test gives **family-wise p = 0.971** — random asset selection
typically produces a *better* best-result than the real signals. Every top combination is driven
by one asset-day (NILUSD +104%, verified independently); remove it and the best goes to net
−0.11%. All top-3 medians negative. → **R6.**

**Q2 — the expected-move model cannot be calibrated on this sample** (62 clustered days, fitted
k CI [−0.20, +0.65] containing both 0.22 and 0.50). Two components had powered evidence *against*
them and were removed: the confluence uplift and the probability slope. Realised P(positive) is
**0.486 / 0.488 / 0.507** at confluence 3/4/5 over 449 clustered days — flat. → **R7.**
It also found my published exit thesis was **EV-negative as written**: a 0.5σ target against a
1.0σ stop needs **92.0%** accuracy; realised is **81.0%**.

**Q3 — cost was overstated by ~45% and is now fixed.** 1.83% → **0.92%** for a 2-leg tactical
trade. `expected_move` now scales with √(hold_days) (measured exponent 0.561); the old model used
1-day sigma while the exit plan contemplated a multi-day trail.

**Q4 — the core conclusion survives; the reasoning did not.** "Right answer, unearned."

## The decisive current result

With every cost fix applied, **ONDOUSD now clears confluence (5/5), sizing, spread, and the 3×
move/cost test at 5.90×** (E[move] 5.40% at a 3-day hold vs 0.92% cost). **The cost constraint is
genuinely cleared.** It is rejected for exactly one reason: **p = 0.50.**

That is the whole finding. Cheaper execution removed cost as the binding constraint and did not
create an edge. **After Q3, the reason not to trade is no demonstrated signal — not cost.**

## Hold LINK vs move to USD (the decision covering 100% of the portfolio)

Measured directly rather than via the void drag argument (`backtests/hold_vs_cash.py`):
LINK 21-day forward return **mean +2.23%**, median −0.75%, **bootstrap 95% CI [−3.77%, +8.48%]**.
Cash is 0% minus a 0.81% switch. The CI contains both zero and −0.81%, so **the decision is not
statistically resolvable** — but the point estimate favours LINK by +3.04% and the median
marginally favours LINK too. **Hold.** Note this no longer leans on the +0.117%/day drift figure
I was rightly criticised for using.

## Hard blocker on any loosening

**D2: there is no live exit mechanism.** `exit_thesis` is consumed only by the shadow ledger. No
exchange-side stop exists and the monitor never places orders, so a real position's "exit
immediately on invalidation" depends on a session happening to run. **Raising `success_probability`
above 0.50 without first implementing exchange-side stops would start taking 15–40% positions with
no way out.** Exit enforcement is a prerequisite, not a follow-up.

## What would unlock live tactical trading

1. A demonstrated continuation probability **> 0.50** — this is the binding constraint and Q1 says
   no tested combination provides it.
2. Exchange-side stop-loss on entry (D2).
3. Measured volatile-regime maker fill probability (currently a 0.65 model, **n=0 real fills**;
   the calm n=2 gives a binomial CI of [0.16, 1.00], which constrains nothing).

The test suite now pins this explicitly: one test asserts the gate is vacuous at p=0.50, and
another proves it **does** open at p=0.62 — so it is the probability blocking trades, not plumbing.
