# Deep Strategy Review — 2026-09-25

**Three hypotheses tested. Three rejected. One capability unblocked.**
Net position: no validated edge exists; the live strategy stays unchanged. That is the
finding, not a failure to find one.

---

## 1. Top 3 ideas investigated

### Idea A — Asymmetric payoff via exchange-side trailing stop  *(most promising; REJECTED)*

- **Hypothesis:** with downside capped by a trailing stop and upside allowed to run, a
  position is +EV even at p = 0.50, because mean win > mean loss. **This would remove the
  need for directional edge entirely** — the constraint that blocks everything else.
- **Mechanism:** Q2 measured MFE/MAE ≈ 2.33 on confluence setups. A trailing stop is the
  instrument that monetises that asymmetry, and Kraken supports it attached at entry.
- **Data:** 1h bars, 32 eligible alts, non-overlapping entries, costs 0.92% + 0.35% stop slippage.
- **Initial result:** trail 12% / 72h → **net +3.68%, t = +3.28.**
- **Why it might be real:** payoff-shape edges do not require prediction, and the exchange-side
  mechanism is verified to exist.
- **Strongest argument against — which won:** three controls.
  - **C1 (decisive): naked buy-and-hold beat the trailing-stop version in all 6 cells, by
    0.33–4.89 pp.** The stop exits on noise before recoveries. It *destroys* return.
  - **C2: random entry days beat signal-filtered entries** (+1.43%, t=2.26 vs +0.88%, t=1.00).
    The setup filter contributes nothing.
  - **C3:** the basket had been selected using end-of-sample volatility — look-ahead.
- **Verdict: REJECTED (registry R10).** The tell was visible in the first run and I nearly
  missed it: a 12% trail *barely binds*, so "the strategy" was just holding a volatile alt in a
  30-day bullish window. **Trailing stops remain valuable as risk control, never as return.**

### Idea B — Market timing via majors lead/lag  *(REJECTED)*

- **Hypothesis:** BTC/ETH lead the alt complex, so majors' trailing return predicts the
  universe's forward return — monetisable at 2 legs as "in crypto vs in USD".
- **Why this was worth testing:** every signal tested to date is *cross-sectional*, and
  cross-sectional demeaning **removes the market factor by construction**. Market-wide
  predictability had therefore never been tested at all, despite the live decision
  (LINK vs USD) being exactly a timing decision.
- **Data:** 1h and 4h bars, leaders {XBTUSD, ETHUSD}, 16 lookback/forward combinations.
- **Result:** best conditional spread (on-signal minus off-signal) **+0.34%** against a 0.92%
  switching cost. Non-overlapping t peaked at **+1.94**; the overlap correction again cut an
  apparent t = +4.06 down to +1.77.
- **Verdict: REJECTED.** Economic magnitude is a third of the cost to act on it.

### Idea C — Exchange-side exit infrastructure  *(VALIDATED, and implemented)*

- **Hypothesis:** D2 ("no live exit mechanism") is a genuine blocker that caps position size.
- **Test:** `validate=true` against the live API — Kraken parses and checks an order without
  placing it. Zero risk, full fidelity.
- **Result: every mechanism needed is supported, and every earlier "rejection" was my own
  parameter error.**

| mechanism | status | note |
|---|---|---|
| stop-loss / stop-loss-limit | **OK** | first failure was my wrong `type`/`ordertype` split |
| take-profit / take-profit-limit | **OK** | |
| trailing-stop / trailing-stop-limit | **OK** | sign convention is `+5%`, rendered back as `-5.0000%`; `-5%` is rejected |
| **post-only BUY + `close[trailing-stop]`** | **OK** | 0.40% maker entry **with** exchange-side protection attached at entry |

- **Verdict: VALIDATED and implemented.** Protection lives on Kraken's servers, so it survives
  this VM dying. Requires no edge claim — it is pure risk infrastructure.

---

## 2. Most valuable IMPLEMENTATION change  *(done this session)*

**Exchange-side protective exits, with trailing-stop support.** `execute.py` now attaches
`close[ordertype]` at entry and **refuses any entry without one**. The exact production request
was validated against the live API. This removes the blocker that capped tactical sizing, and it
is the only change this session that rests on verified fact rather than a statistical estimate.

## 3. Most valuable RESEARCH EXPERIMENT  *(ongoing)*

**The shadow ledger.** Every backtest in this repository is contaminated — the same model chose
the thresholds it then validated, and four separate results have now collapsed under correction
(R1, R2, R6, R9, R10). Shadow predictions are the **only uncontaminated evidence available**,
because the prediction is written down before the outcome exists. It records setups *below* the
live gate deliberately, so a gate rejecting profitable setups would be detectable.

Priority is quantity: 5 open predictions is far too few. This accrues automatically.

## 4. Should the live strategy change?

**REMAIN UNCHANGED.** Not more aggressive, not more conservative, no new tactical mode.

- More aggressive would require an edge. Three more hypotheses died this session; nothing in the
  registry supports p > 0.50.
- More conservative is unwarranted: the gate already refuses everything, and the risk
  infrastructure just improved.
- A new tactical mode would be a strategy whose only evidence is a backtest generated by the same
  model that invented it — explicitly disallowed, and R10 is a fresh example of why.

## 5. Benchmark challenge (Q5)

Hold-LINK remains appropriate. The objective is **expected** final USD. Diversification does not
raise expected return (it lowers variance), costs 0.92% to implement, and the earlier drag
argument for it was void double-counting (R8). Directly measured: LINK 21-day forward mean
+2.23%, bootstrap CI **[−3.77%, +8.48%]** — contains both zero and the switch cost, so the
LINK-vs-cash decision is **not statistically resolvable**. Point estimate and median both
marginally favour LINK. No change.

## 6. Account-size constraint (Q7)

At ~$56 with 0.92% round trips, only several-percent moves matter. Every rejected idea above
failed on exactly this: Idea B's edge was 0.34% against a 0.92% cost. The constraint is doing its
job — it is why tiny statistical edges are correctly ignored rather than chased.

---

## What would change the answer

1. **A signal with a non-overlapping |t| > 3 and a positive median.** Nothing tested has both.
2. **Shadow ledger accumulating ~30+ closed predictions**, giving the first clean out-of-sample
   read on whether the gate rejects profitable setups.
3. **Measured maker fill probability in volatile conditions** (currently a 0.65 model, n=0 real
   volatile fills; the calm n=2 gives a binomial CI of [0.16, 1.00], which constrains nothing).

## Methodological note

The single most valuable practice this session was **running the control before believing the
result**. Idea A showed t = +3.28 and would have been a plausible-sounding strategy. One control —
"does it beat simply holding the same asset?" — reversed it completely. Every apparent edge this
project has produced has died to a control, a demeaning, an overlap correction, or a single
outlier day. That is now the expected outcome, and the reason to run the check first.
