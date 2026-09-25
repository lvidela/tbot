# Independent audit: research methodology and agent architecture vs external AI-trading-agent work

**Date:** 2026-09-25 (~23:00–00:30Z) · **Author:** independent audit agent (cloud), not the live
agent and not the Research Agent · **Status:** evidence and recommendations only. Nothing here
changes live trading, a gate, a threshold, execution code, the monitor, `CLAUDE.md` or
`researcher/`.

**How to read this.** Every section separates three things:
- **[FACT-EXT]** documented by an external source (linked);
- **[FACT-REPO]** verifiable in this repository (file/commit cited) or measured by this audit
  (script cited, reproducible);
- **[INTERP]** my interpretation; **[REC]** a recommendation for this repository.

Measurements run for this audit are all **outcome-blind** or pure simulation. None computes a
forward return on any asset, so none adds a researcher degree of freedom to the project's data.

| script (`research/audits/`) | what it measures | output |
|---|---|---|
| `signal_redundancy.py` | joint firing of the 5 tactical confluence conditions, 20 Kraken pairs × 715 4h bars | `results/signal_redundancy.json` |
| `vol_vs_cost.py` | spread, depth, impact and cost/σ across 115 Kraken USD pairs by volatility quintile | `results/vol_vs_cost.json` |
| `holdout_reuse_sim.py` | false-positive rate of the X1/X4 two-stage gate when the holdout is reused or peeked at | `results/holdout_reuse_sim.json` |
| `regime_episodes.py` | number of independent regime episodes in Kraken weekly history | `results/regime_episodes.json` |

Data snapshots used are committed under `research/audits/data/` (Kraken public API, fetched
2026-09-25T23:26–23:31Z).

---

## A. Executive assessment

1. **This repository's methodology is already better than every external LLM-trading system I
   reviewed on the dimensions that matter most for finding real edge**: benchmark-relative
   measurement, cost realism, overlap/clustering corrections, pre-registration, controls, and
   honest recording of nulls with MDEs. None of the public arenas or benchmarks model costs as
   carefully (TradeRank: 0.1% fee, *no slippage*; AI-Trader: no explicit costs; TradingAgents:
   none; DXAP paper engine: zero slippage, zero funding). Most of what those projects offer is
   **not** worth importing.

2. **The largest unaddressed weakness is holdout contamination, and it is now measurable.**
   - [FACT-REPO] The 2024-01 → 2026-09 "holdout" window is the evaluation window of **eight
     studies** (T1, X1, X4, X4b, X3, X5, X6, plus the R12/R13 exposure work). X3, X5 and X6 were
     all pre-registered, run and merged within ~8 minutes (23:21–23:29Z) while this audit was in
     progress.
   - [FACT-REPO] X4 was pre-registered **76 seconds** after X1's holdout results were committed
     (`f4f4086` 23:12:33Z → `4754441` 23:13:49Z). Those results included a
     momentum/**volatility**-controlled partial IC and the survivorship-free alt basket falling to
     0.16× in 2024–26. The BACKLOG explicitly chose X4 because its "mechanism predicts the
     2024–26 pattern (high-vol alts bleeding)".
   - [FACT-EXT] Research on LLM backtesting shows that model knowledge of the evaluation period
     inflates apparent predictability. This project's agents have a stated knowledge cutoff of
     June 2026, so the **entire 2019–2026 history, discovery and holdout alike, predates it**.
   - [FACT-REPO, simulation] Under a global null, peeking at the holdout raises the holdout-stage
     pass rate from 5% to **44–88%**. The two-stage gate still holds its false-positive rate
     near 0.3–0.6% because the discovery stage stays independent. If the agent can also "see" the
     discovery period (LLM priors), the rate rises to **1.3% per study, 12% over 10 studies**.
   - [INTERP] X4's *information* result probably survives. Its discovery t = −4.28 passes a
     project-wide Bonferroni over ≈ 266 tests, it is negative in all seven years, and external
     literature documents a crypto low-volatility premium. But **X4's holdout t = −6.87 and the
     X4b "replication" are not independent confirmations** and should not be cited as such.
   - [INTERP] **X6 is the live example of the risk.** It is pre-registered as "beyond
     volatility (X4)" on X4's grid and the same holdout, and its pre-registration anticipates the
     "2024–26 memecoin/AI listing wave". Its discovery partial IC (t = 2.68) passes its 3-test
     family but **not** a program-level bar (|t| ≳ 3.7). Its holdout t = 3.45 comes from the
     reused, prior-exposed window. By the standard proposed here, X6's information label should
     read "exploratory (pre-cutoff, prior-exposed)".

3. **Confluence is one event counted several times, and this is now measured, not only argued.**
   [FACT-REPO] Three or more of the five conditions fire together **11.4×** as often as they
   would if the conditions were independent (3.2% vs 0.28% of pair-bars). In **98.7%** of
   confluence ≥ 3 cases the asset's trailing 24h return is positive, with a mean of **+10.7%**.
   Pairwise correlations are modest (Spearman ≤ 0.40; Nyholt M_eff 4.7 of 5), so **average
   correlation understates the dependence, which lives in the tail**. This confirms registry D4
   empirically: "confluence ≥ 3" ≈ "rose ~10% in a day".

4. **Higher volatility does lower cost *relative to the move*, so cost is not what rules
   memecoins out.** [FACT-REPO] Spread scales with σ at an elasticity of **0.64**, fee-dominated.
   Measured at a $13 clip, the round-trip cost as a fraction of a 3-day σ falls from **15.8% to
   5.2% (maker)** and from **30% to 9.8% (taker)** between the lowest and highest volatility
   quintiles. **The binding question is the sign of the predictable component, and the
   project's best-established regularity (X4) says it is negative for high-vol names.** The
   maker-cost side in fast markets is unmeasured: n = 0 volatile fills.

5. **Cheap, high-value gaps:**
   - (i) no code, strategy, prompt or model **version fingerprint** on any record. The shadow
     ledger labels every row `tactical_v4` although `predicted_prob` spans 0.50–0.62 across a
     model change (R7);
   - (ii) **no replayable decision snapshot**: `data/escalation_context.json` is overwritten and
     gitignored, and session transcripts are gitignored;
   - (iii) **no project-wide trial ledger**: multiple testing is controlled per study, never
     across the program;
   - (iv) the maker "adverse selection" metric measures submit→fill drift, not post-fill markout.

6. **Things that should not be built:** multi-agent bull/bear debate, LLM-in-the-loop return
   prediction, leaderboard-style arenas, live regime switching, live memecoin expansion, a formal
   differential-privacy Thresholdout, and PBO/CSCV re-analysis of already-rejected grids.
   Reasons are in §J.

**Bottom line.** The research engine's per-study discipline is strong. What it lacks is
*program-level* discipline: one shared, reused, pre-cutoff holdout; no cumulative test count; no
version join between a decision and the code that produced it. The one route to *uncontaminated*
confirmation is forward-only evaluation of frozen specifications. The shadow and counterfactual
ledgers already started that route, but they are not frozen, versioned or tamper-evident.

---

## B. Existing capability map (20 audit questions)

Classification legend: **STRONG / PARTIAL / MISSING / N/A**. Machine-readable version with
evidence paths: `research/audits/external_agent_capability_matrix.json`.

| # | capability | class | evidence (repo) | concrete weakness |
|---|---|---|---|---|
| 1 | Point-in-time data / look-ahead | **PARTIAL** | Price-data look-ahead is tested (`research/x4_lowvol/test_x4.py`, `timing/test_timing.py`). The counterfactual ledger freezes the entry at the decision instant (`scripts/counterfactual.py` docstring) | **Hypothesis-selection look-ahead is unaddressed:** LLM training data covers all history, and prior holdout results inform the next hypothesis (§F). No research file mentions the model's knowledge cutoff |
| 2 | Immutable decision snapshots | **PARTIAL** | Counterfactual rows store decision-time bid/ask/spread/signals | Ledgers are JSON files rewritten wholesale (`_rw` in shadow.py/counterfactual.py), with no hash chain. Shadow rows were backfilled after the fact (flagged honestly). Escalated sessions write no structured snapshot. `escalation_context.json` is overwritten and gitignored |
| 3 | Experiment/version fingerprints | **MISSING** | none: no git hash or file hash in any ledger, log or finding | Shadow `strategy: tactical_v4` spans predicted_prob {0.50, 0.56, 0.59, 0.62} |
| 4 | Locked out-of-sample holdout | **PARTIAL** | Chronological split per study. Discovery results are committed before the holdout (X1, X4, T1) | The same 2024–26 holdout is reused by 8 studies (T1, X1, X3, X4, X4b, X5, X6, R12/R13). Hypothesis choice saw prior holdout tables (X1→X4, 76 s). The holdout predates the LLM cutoff. Access control is procedural only |
| 5 | Ablation testing | **PARTIAL** | Q1 enumerated 31 subsets. R10 C1/C2 controls. R12 static-exposure control | No leave-one-out incremental contribution. Redundancy was argued (D4), never measured until this audit |
| 6 | Market-regime detection | **PARTIAL** | `execution_stats.vol_regime` (calm/volatile). Monitor detectors | Regime is per-asset only. No market-wide state (BTC trend, correlation, dispersion, liquidity stress) is recorded in any decision record |
| 7 | Regime-conditioned selection | **MISSING** | — | Appropriately missing: history holds ~12 independent vol/trend episodes (§G), too few to fit |
| 8 | Strategy tournaments | **MISSING** | Shadow ledger holds one strategy (`tactical_v4`) | Every study evaluates one candidate against its own controls. No common frozen contract across candidates |
| 9 | Independent adversarial falsification | **PARTIAL** | Q4 adversarial review. The live agent re-validates cloud findings (ACCEPT/REJECT/DEFER). Controls routinely kill results (R10, R12) | Both sides are the same model family with the same priors and the same data. The adversary has no information the author lacks |
| 10 | Multiple-testing / RDoF control | **PARTIAL** | Per-study Bonferroni, permutation FWER (Q1 p = 0.971, R12), MDEs on nulls | No program-level count. ≈ 266 formal tests to date (§E4). No experiment budget |
| 11 | Execution-aware attribution | **PARTIAL** | `execution_stats.py` records fill fraction, latency, fee rate, regime and "adverse_bps". Costs are charged in every study | The adverse-selection metric is submit→fill mid drift, not post-fill markout. n = 2 fills, both calm |
| 12 | Decision replay | **MISSING** | — | The inputs an escalated session saw are not retained. Session transcripts (`logs/claude_sessions/`) are gitignored |
| 13 | Prompt/model/tool version tracking | **PARTIAL** | `CLAUDE.md`, the launcher prompt and `.claude/settings.json` are versioned in git | No per-decision join to the revision in force (the DXRG discipline). No model id or CLI version is recorded |
| 14 | Capital allocation methodology | **PARTIAL** | Edge gate (`edge.py`), size 15–30% (`tactical.py`), HOLD as the zero-cost maximum | Sizing is ad hoc, not uncertainty-aware. This is moot while p = 0.50 |
| 15 | Automatic strategy retirement | **PARTIAL** | The registry records rejects with reopen criteria (hypothesis retirement is strong) | No pre-declared kill rule for a *live* strategy. N/A today, since only HOLD is live |
| 16 | Novel strategy discovery | **PARTIAL** | Mechanism-first backlog (X1–X12), survivorship-free data | Serial, one hypothesis at a time. Candidates are LLM-generated (prior-contaminated). No systematic generation |
| 17 | Counterfactual evaluation | **PARTIAL** | Well designed (`counterfactual.py`, benchmark-demeaned, clustering, horizons) | 31 rows / 16 opportunities from **2 decision hours**. Shadow and counterfactual are not frozen specs |
| 18 | Benchmark-relative performance | **STRONG** | Immutable benchmark (`data/benchmark.json`), D8 fix, excess vs LINK everywhere, static-exposure control (R12) | — |
| 19 | Agent-behaviour telemetry | **PARTIAL** | Activity log with `reasoning`, dedup transitions, evaluation verdicts (`evaluations.py`) | No session duration, tools used, model id, hypotheses considered/rejected, or data cutoff per decision |
| 20 | Research reproducibility | **PARTIAL** | Scripts, tests, pre-registration commits, results JSON for X1/X4/T1 | Q1–Q4 backtests read `data/cache/`, which is gitignored and not reproducible from the repo. Fetched data carries no content hash. Silent 0-byte output incident (HANDOFF) |

Score: 1 STRONG, 15 PARTIAL, 4 MISSING (fingerprints, replay, tournaments, and
regime-conditioned selection, which is missing by design).

---

## C. External systems reviewed

| system | type | what was examined |
|---|---|---|
| **Agent Market Arena (AMA)** — "When Agents Trade", arXiv 2510.11695, WWW 2026 | live multi-market LLM benchmark (the "AI trader arena" research line) | live-only evaluation, point-in-time news verification, buy-and-hold baselines, backbone-vs-architecture comparison |
| **AI-Trader** (HKUDS), arXiv 2512.10971 | live, "data-uncontaminated" benchmark, 6 LLMs × US / A-shares / crypto | time-gated tools, minimal-information paradigm, benchmark indices, cost treatment |
| **DXRG continuous record** — arXiv 2609.05663, DX Terminal Pro + DXAP fleets | production telemetry: 7.5M invocations, 231,638 turns, 14,596 fills | decision-provenance ledger, template/config revision join, evidence tiers, behavioural failure modes |
| **TradingAgents** (Tauric Research), arXiv 2412.20138 | multi-agent LLM architecture (analysts, bull/bear debate, risk team) | architecture, evaluation window, costs, contamination |
| **Alpha Arena** (nof1, Season 1) | real-money LLM competition on Hyperliquid perps | design and what a leaderboard can and cannot show |
| **TradeRank** | public live LLM leaderboard, 28-day seasons | cadence, published prompts, cost/slippage model, rule-based churn limits |
| **ClawStreet** | paper-trading API arena for agents | documentation of fills/costs (sparse) |
| Academic: Bailey, Borwein, López de Prado & Zhu (PBO/CSCV); Bailey & López de Prado (Deflated Sharpe); Dwork et al. 2015 (reusable holdout, *Science* 349:636); LLM look-ahead papers (arXiv 2512.23847, 2608.02985, 2605.24564; MemGuard-Alpha 2603.26797); crypto low-volatility anomaly literature (*Finance Research Letters*) | methodology | overfitting control, holdout reuse, LLM temporal leakage, external corroboration of X4 |

"ClawStreet" and "AI Trader Arena" returned mostly marketing material. ClawStreet's public
documentation does not describe its fill, fee or ranking model, so I draw no methodological
conclusions from it beyond its being a $100k paper arena. "AI Trader Arena" did not resolve to
one project; I treated it as the arena class (AMA, Alpha Arena, TradeRank, BingX AI Arena).

---

## D. Evidence from external systems

### D1. Leaderboards and arenas — [FACT-EXT]
- **Alpha Arena S1:** 6 frontier models, $10k real each, 17 days (2025-10-18 → 11-03), winner
  +22.31%. That is one path per model with no replication.
- **TradeRank:** "46.2% of model-seasons profitable" across 56 models and 9 seasons. It charges
  0.1% per side and states: "No slippage — trades fill at the single price fetched at the start
  of the cycle, no matter the size." Its rule set (≥ 0.80 confidence gate, 1 new position per
  cycle, no averaging down) exists "to stop churn from masquerading as edge".
- **AI-Trader:** over 2025-10-01 → 11-14, **every agent lost in crypto** (best −12.18% vs index
  −14.30%, "via high cash positioning"). No agent beat the A-share baseline. The paper reports
  no explicit commissions or slippage.

**[INTERP]** A 17–45-day, one-path-per-model leaderboard has an MDE far larger than any
plausible edge. By this repo's own F4 arithmetic, separating a 1% net edge takes hundreds of
independent decisions. "46% profitable" is what zero skill plus market beta produces. The only
transferable lessons are negative: cash exposure dominated relative crypto results (an exposure
effect, which is exactly the static-exposure point of R12), and cost-free simulators flatter
activity. **No leaderboard result here is evidence of transferable alpha.**

### D2. AMA and AI-Trader — contamination control by construction — [FACT-EXT]
- Both evaluate **live only**, so the future does not exist at decision time.
- AI-Trader time-gates its Search/News tools to "information available up to the current
  simulated time".
- AMA verifies news point-in-time.
- Both treat live, forward evaluation as the only defence against LLM memorisation.

**[INTERP]** This is the same idea as this repo's shadow and counterfactual ledgers, and it is
the correct one. The repo applies it only to *live decisions*. It does not apply it to
*research conclusions*, which are all drawn from pre-cutoff history (§F).

### D3. DXRG continuous record — the most relevant external work — [FACT-EXT]
- **Provenance:** "every order carries the rendered state, the template revision, and the
  config revision resolved at that turn". Attribution "joins on turn id + attempt id + the
  template and config revision resolved at that turn, never the current roster template."
- **Evidence tiers:** "firm" means a registered analysis on the full window, day-clustered
  intervals, and at least one ablation or permutation check. "Provisional" means positive but
  narrow or design-sensitive.
- **Behaviour:** the operating layer (sliders, rendered candidate lists, order-path mechanics)
  "determines behaviour more than anything written in strategy text".
  - A render boundary produced a **1.75× regression discontinuity** at the top-3 cut: symbols
    just below it were statistically identical but rarely picked because they were not shown.
  - **Volatility-blind sizing:** Spearman(vol, leverage) = −0.001, while agents *sized up* in
    wilder names (+0.165). Median realised return fell from −10.6 bps in the calmest sextile to
    **−98.2 bps in the wildest**.
  - Chase states: entries after > +0.75%/1h moves had trailing-4h +136.5 bps and forward-4h
    **−6.9 bps**.
  - Prompt-stated risk limits did not restrain behaviour: agents that stated a liquidation
    distance were liquidated *more* often (5.8% vs 1.2%).
  - Memory-write frequency correlated negatively with P&L (ρ = −0.20). One agent traded 31 of
    32 positions under **deleted** strategy text, three weeks later. Agents fabricated funding
    income.
- **Memecoins (DX Terminal Pro):** 3,505 real-ETH vaults, 2.3%/swap cost, median true return
  **0.492×**, 16.2% profitable. 1,544 vaults herded into one token within an hour. The 82 still
  holding were 89% underwater.
- **Fleet (DXAP):** −$217k at 5.5 bps fees vs −$148k at zero fee, so "fees are not the
  explanation".
- **Model league:** 416 replayed scenarios, frontier models statistically indistinguishable
  (Holm min p = 0.46).
- **Limitation they state:** paper engine with zero slippage and zero funding.

**[INTERP] for this repo:**
- (a) Provenance joins are the single most transferable practice (§E2).
- (b) "The operating layer determines behaviour" maps to this repo's *monitor detectors and
  escalation prompt*. What is escalated, and how it is framed, shapes what the session considers.
  A detector set dominated by up-move conditions pre-selects chase states (§H′), and
  DXRG's chase-state result (forward −6.9 bps after +136 bps) is the external analogue of R1/R2.
- (c) Volatility-blind sizing in wild names was the costliest failure there. This repo's
  `tactical.py` sizes by confluence, not by σ, but applies σ-scaled stops. That is harmless
  while nothing qualifies.
- (d) Memory contamination by deleted text maps to `STRATEGY.md` VOID claims kept in place.
  They are kept for honesty, which is right, but a session could cite them. The VOID markers
  mitigate this.

### D4. TradingAgents — [FACT-EXT]
- Five tech stocks, 2024-01-01 → 03-29 (3 months).
- No transaction costs are mentioned.
- Reported **Sharpe 8.21** on AAPL with 0.91% max drawdown; the authors call it "exceptionally
  high".
- No discussion of whether the LLMs had seen 2024 prices.

**[INTERP]** This is not evidence for multi-agent debate. It is a 3-month, cost-free,
possibly-contaminated backtest of the kind this repo's registry exists to reject. The
architecture's one relevant idea, an adversarial bull/bear pairing, already exists here in a
stronger form: controls and live re-validation that *measure* instead of *argue*.

### D5. Methodology literature — [FACT-EXT]
- **PBO/CSCV** (Bailey et al., *J. Computational Finance* 20(4)) estimates the probability that
  the in-sample-best configuration underperforms out-of-sample. The authors note that plain
  hold-out is "unreliable" for investment backtests.
- **Deflated Sharpe** corrects for the number of trials and non-normality.
- **Reusable holdout / Thresholdout** (Dwork et al., *Science* 2015): each adaptive query leaks
  holdout information. Validity survives many queries only if access is noised or budgeted.
- **LLM look-ahead** (arXiv 2512.23847; 2608.02985; 2605.24564): memorised training-period
  outcomes produce predictability that collapses out-of-sample. Recommended practice is
  **post-cutoff evaluation windows** and documenting the model cutoff.
- **Crypto low-volatility premium:** *Finance Research Letters* work reports a statistically
  and economically meaningful low-vol premium after 2017, emerging as markets matured.
  [INTERP] This is external corroboration of X4's information result, independent of this
  repo's holdout. It also means X4's hypothesis was not novel, and was plausibly prior-known to
  the agent that proposed it.

---

## E. Gaps found (ranked by expected information value)

### E1. Holdout reuse and pre-cutoff contamination — HIGH
[FACT-REPO]
- **Holdout reuse:** T1's holdout (2024-01-01 → 2026-09-24), X1's (2024-01-01 → 2026-09-14),
  X4's (2024-01-01 → 2026-08-10) and X4b's full window (2024-10 → 2026-09) all sit in the same
  span. R12/R13 also use it. So do X3 (→ 2026-09-19), X5 (→ 2026-09-24) and X6 (X4's grid),
  merged while this audit ran.
- **Sequence:** X1's holdout tables were committed at 23:12:33Z. They included the partial IC
  "momentum/vol-controlled" and "alt basket 0.16×". X4 was pre-registered at 23:13:49Z. The
  BACKLOG log selects X4 because it "predicts the 2024–26 pattern (high-vol alts bleeding) ex
  ante".
- **Disclosure:** X4's own pre-registration discloses what X1 exposed, which is honest. But
  "nothing was computed conditional on volatility" is not quite accurate: X1's S-c *was*
  controlled for volatility on that holdout.
- **Cutoff:** no research file mentions an LLM knowledge cutoff.

[INTERP, simulation] Once hypothesis choice has seen the holdout, the holdout stage stops
testing anything (pass rate 44–88% under the null). All protection falls back on the discovery
stage, which is itself pre-cutoff.

### E2. No version join between decisions and the code, config and prompt that produced them — HIGH (cheap)
[FACT-REPO]
- No record carries a git commit or a file hash.
- R7 changed `success_probability` from `0.50 + 0.03·conf` to 0.50 mid-ledger, and the shadow
  rows show both, all labelled `tactical_v4`.
- The live agent's own "Known gap" (STATE.md) says the launcher cannot record the verdict.

[FACT-EXT] DXRG's attribution rule exists precisely to prevent "retroactive misattribution".

### E3. No replayable decision snapshot — MEDIUM-HIGH
[FACT-REPO] `data/escalation_context.json` is overwritten on each escalation and gitignored.
Session transcripts are gitignored. So for any past live decision one cannot reconstruct what
the session saw: prices, gate outputs, queue contents. The activity log keeps a free-text
`reasoning` field, which is good for honesty but not replayable.

### E4. No program-level trial ledger or DoF budget — MEDIUM
[FACT-REPO] My tally of formal tests in REGISTRY and findings is approximately:

| source | tests |
|---|---|
| R1/R2 event triggers | 4 |
| R3 | 12 IC + 36 grid |
| R4 | 3 |
| R6 | 93 |
| R7 | ~3 |
| R9 | 36 |
| R10 | 6 |
| lead/lag (Idea B) | 16 |
| R11 | 4 |
| R12 | 9 |
| R13 | 2 |
| T1 | 18 |
| X1 | 5 |
| X4 | 4 |
| X4b | 1 |
| X3 / X5 / X6 (merged during this audit) | 3 + 4 + 3 |

That is **≈ 266**, before unrecorded exploration and robustness variants. A program-wide
Bonferroni at 5% needs p < 2×10⁻⁴ (|z| ≳ 3.7). Only X4/X4b's information tests clear it. That
is a useful sanity result, but nobody is tracking it.

### E5. Maker adverse-selection metric — LOW now, MEDIUM before any volatile maker trading
[FACT-REPO] `execution_stats.record` computes `adverse_bps` from `submitted_mid → filled_mid`.

[INTERP, not verified with data — n = 2] For a resting post-only order the market must *move to*
the quote to fill it, so submit→fill drift is partly mechanical. It is not the post-fill markout
(mid at fill + Δt vs fill price) that defines adverse selection. The two can differ in sign and
size, and in volatile markets that difference matters most. The fix belongs to the live agent
(`scripts/execution_stats.py` is live code). I recommend it; I did not implement it.

### E6. Tail redundancy in escalation detectors — LOW (informational)
[FACT-REPO, measured] Confluence ≥ 3 ≈ one up-move event (§H′, §A item 3). It is harmless as a risk
filter, which is how A2 now describes it. It matters for escalation framing: sessions are
disproportionately launched into post-rally states. DXRG's chase-state and render-boundary
findings say framing shapes choice.

### E7. Reproducibility of the Q1–Q4 backtests — LOW
They depend on `data/cache/`, which is gitignored. Those results are all rejections, so the risk
is low, but they cannot be re-derived from the repo.

---

## F. Researcher-overfitting assessment (priority area)

### F1. Is there a researcher-degree-of-freedom problem?
**Yes, but not where one might expect.** Within a study the controls are excellent:
pre-registration committed before data, discovery committed before holdout, Bonferroni and
permutation FWER, non-overlap corrections, and MDEs. The loop the brief describes
(hypothesis → backtest → tweak → backtest) is visibly suppressed. Every hypothesis R1–R13 died
rather than being tuned into life. The *direction* of past defects is informative: D1, D3 and
D5 biased toward **not** trading, and D8 toward trading. That is not one-sided motivated
search.

**The DoF problem lives between studies:**

1. **Hypothesis selection is adaptive to the holdout** (§E1). The program's rule "each study
   starts from the BACKLOG, whose latest log wins" plus a shared holdout is exactly the adaptive
   setting of Dwork et al.
2. **Hypothesis generation is prior-contaminated.** An LLM proposing "low-vol beats high-vol in
   crypto" in September 2026 is not blind to 2022–2026. Pre-registration timestamps prove the
   *code* did not see the data. They cannot prove the *author* did not.
3. **Pre-registration integrity rests on commit order only.** Nothing prevents an agent from
   computing an exploratory statistic, not committing it, and then pre-registering. The ~2 min
   from X4 pre-registration to committed discovery results (`4754441` → `1d1fad3`) shows the
   cost of doing so would be negligible. I found **no evidence that this happened**, and the
   records are candid. The point is that the mechanism does not rule it out.
4. **No cumulative multiplicity budget** (§E4).

### F2. Mechanisms evaluated — incremental value given what exists

| mechanism | problem it solves | already solved? | new information | statistical value | new failure mode | cheapest validation | verdict |
|---|---|---|---|---|---|---|---|
| **Forward-only locked holdout** (post-freeze, post-cutoff data only) | contamination by prior holdout views and LLM training | **No** — every holdout is pre-cutoff and reused | the only uncontaminated confirmation available | **High** — it is the only design where the null FP rate is the nominal α | slow (months), and temptation to peek at partial results | sim: `holdout_reuse_sim.py` honest vs peek rows; operationally, one frozen spec evaluated at a fixed date | **IMPLEMENT** (§I-1) |
| Historical locked holdout (e.g. reserve 2026-Q3) | adaptive reuse | partly | little: still pre-cutoff, and ~3 months is tiny | Low | false sense of safety | — | **Do not** rely on it as confirmation |
| Preregistration | forking paths within a study | **Yes** (commit before data) | — | already captured | — | — | keep. Add a **hash of the analysis script** into the pre-registration so later edits are detectable (cheap) |
| Experiment / trial ledger + budget | cumulative multiplicity | **No** | makes the program-level threshold explicit | Medium (it changes which results are citable; today only X4/X4b clear it, and X6's discovery does not) | bureaucracy; gaming by not logging | one append-only JSONL, back-filled from REGISTRY (≈ 266 rows) | **IMPLEMENT** (light) |
| Independent validation agent | shared blind spots | partly (live agent re-validates) | only if the validator lacks the author's information | Low–Medium: same model family, same priors | theatre: two copies agreeing | give the validator only the frozen spec and forward data, no narrative | **Implement only in the forward-holdout form** (the evaluator runs the frozen spec, so no judgement is needed) |
| Multiple-testing correction per study | within-study | **Yes** | — | — | — | — | keep |
| Immutable experiment definitions | post-hoc spec drift | partly (git history) | makes drift *detectable* rather than merely visible | Medium, cheap | none material | sha256 of spec + code in the pre-registration | **IMPLEMENT** (with the forward holdout) |
| Strategy tournament | author-controlled evaluation | **No** | ranks candidates under one frozen contract; mainly a *falsification and retirement* device | Medium. Power is low: F4 says 340–790 days to detect 1% net per candidate, and more candidates dilute it | selecting the tournament winner *is* the multiple-testing problem again | shadow infra already exists; add null controls as entrants | **IMPLEMENT, small (≤ 6 entrants incl. ≥ 2 nulls), forward-only** |
| Automatic retirement | zombie strategies | hypotheses: yes (registry). Live: N/A | — | Low today | premature kill on noise | — | **Defer** until any non-HOLD strategy is live; then pre-declare the kill rule at activation |
| External validation agents (another model family) | correlated LLM priors | No | diversity of priors | Unknown, probably low. DXRG found frontier models indistinguishable on replay | cost; still pre-cutoff | — | **Do not implement** |
| Thresholdout (DP-noised holdout) | adaptive reuse with guarantees | No | formal guarantee | Real in theory. Here the holdout has ~22–35 periods, and noise at useful privacy levels would swamp it | complexity; false precision | — | **Do not implement.** A forward holdout plus a query budget achieves the goal more simply |
| PBO / CSCV / Deflated Sharpe on existing grids | selection bias on grids | superseded — every grid is already rejected | none | ~0 | — | — | **Do not implement** retroactively. Apply DSR only if a future candidate reports a Sharpe |

### F3. Quantified: what the current two-stage gate is worth under contamination
From `results/holdout_reuse_sim.json` (global null, 200k simulations per row; K = number of
candidate hypotheses the agent can choose among):

| scenario | K | P(holdout stage passes) | **P(false positive per study)** | P(≥ 1 FP in 10 studies) |
|---|---|---|---|---|
| honest choice | 20 | 0.049 | **0.00036** | 0.4% |
| sees holdout exactly | 20 | 0.878 | 0.0058 | 5.6% |
| sees holdout with noise (sd 1) | 20 | 0.439 | 0.0027 | 2.6% |
| sees both periods (LLM prior), exactly | 20 | 0.438 | **0.0128** | **12.1%** |
| sees both periods, noise sd 1 | 20 | 0.267 | 0.0081 | 7.8% |

**[INTERP]**
- The two-stage gate is robust *because* the discovery stage carries it.
- The holdout stage alone becomes almost uninformative once the holdout is peeked at.
- The residual risk is **prior contamination of the discovery period**, which only
  post-cutoff data removes.
- With ~10 studies per program cycle, a 5–12% chance that at least one "POSITIVE" is spurious is
  material. That is exactly the class of result (X4-like) that would reach the live agent.

---

## G. Regime-discovery assessment

**Question:** does regime information increase predictive edge after costs?

**What the repo already knows** [FACT-REPO]:
- **T1:** six market-state signals, 18 tests; best |t| 1.77, permutation p = 0.47; all cells
  negative vs hold-LINK after costs.
- **X1:** the funding IC flips sign between 2020–23 and 2024–26, i.e. regime-dependent, with
  2 regimes ≈ 2 observations.
- **X4:** the low-vol IC is negative in all 7 years, i.e. regime-*stable*.
- **R12:** the TSMOM gain was mostly de-risking (the static-exposure control captured most of
  it).
- **Execution:** the vol regime defines the maker fill prior (R5).

**New measurement** [FACT-REPO, `regime_episodes.py`, outcome-blind] on Kraken weekly bars,
652 weeks (BTC from 2014; alts shorter):

| regime | episodes (on/off) | median ON length |
|---|---|---|
| BTC 12w vol above expanding median | 12 / 12 | 12.5 weeks |
| BTC above 26w SMA | 12 / 12 | 23 weeks |
| alt-led (median alt 4w − BTC 4w > 0) | 28 / 28 | 4.5 weeks |
| high alt–BTC correlation | 14 / 14 | 17.5 weeks |

**[INTERP]**
- A regime-conditioned strategy is evaluated on **~12 independent episodes** for vol/trend
  regimes, over 12 years. At a typical cross-episode dispersion, that yields an MDE comparable
  to T1's (Bonferroni MDE ~14–17%/20d).
- Conditioning a *second* signal on regime halves n again.
- **The data cannot support fitting regime-switching rules.** It can support *one*
  pre-registered interaction test, and only if the prior is strong.
- The only regime question with decision value and plausible power is **whether X4's low-vol
  filter weakens in alt-led / risk-on episodes** (28 episodes). That matters because the high-vol
  arithmetic-mean tail (X4 discovery, 2020–21) is where a memecoin case would live.

**[REC] No live change.**
1. **Record regime state in every decision snapshot** (BTC vol state, BTC trend, alt-led flag,
   correlation state, spread-stress flag). This is cheap. It turns every future decision into a
   labelled forward observation, and after ~12–24 months it enables a clean post-cutoff test.
2. **Shadow experiment G-1** (§I-4): split forward counterfactual/shadow outcomes by
   pre-registered regime labels. Do not fit anything until MDE ≤ the claimed effect.

---

## H. High-volatility / memecoin research assessment

**Hypothesis under test:** does higher volatility produce a larger *predictable* excess return
relative to its additional execution costs and adverse selection?

| component | evidence | source |
|---|---|---|
| volatility | Q1 median σ30 3.3% → Q5 10.0%/day (115 USD pairs, ≥ $250k 24h vol) | [FACT-REPO] `vol_vs_cost.py` |
| spread | 3.3 → ~9.4 bps; elasticity to σ **0.64** (Spearman 0.24). Fee-dominated at every quintile | same |
| depth within 0.5% | Q1 median $152k → Q5 **$8.5k**. Impact for a $13 clip ≈ 0 bps everywhere | same |
| cost / move | round trip as a share of 3-day σ: maker 15.8% → **5.2%**; taker 30.3% → **9.8%** | same |
| maker fill probability | **unmeasured** in volatile conditions (n = 0). A 50% prior is used | STATE.md; R5 |
| adverse selection | 5.4 bps/leg calm (n = 2; metric caveat §E5). On GRASSUSD, a passive seller was run over by +150 bps in 60 s | A1; R11-CONFIRMED |
| expected (rank) return | **negative** for high vol: IC(vol60, 28d) −0.157/−0.254 (Binance), −0.195 (Kraken) | X4, X4b |
| arithmetic mean | high-vol basket mean ≈ low-vol in 2020–21 (lottery tail); holdout high-5/10 baskets 0.07×, median −10.6%/28d | X4 supplementary (not pre-registered) |
| prediction accuracy | no directional signal survives in any volatility band (R1, R2, R6, R7: p = 0.50) | registry |
| benchmark-relative | survivorship-free alt basket 0.16× vs LINK 0.84× (2024–26) | X1 (descriptive) |
| drawdown | 6 of 20 liquid Kraken assets lost > 90% in 4.8 years; DXRG memecoin vaults median 0.492× | R13; [FACT-EXT] DXRG |
| agent behaviour | agents size up in wild names; wildest sextile −98.2 bps median | [FACT-EXT] DXRG |

**[INTERP]**
- Cost is **not** the binding constraint for high-vol names at this account size. It shrinks
  relative to σ.
- The binding constraints are:
  - (a) **sign**: the best-established regularity in the project says the predictable component
    for high-vol names is *negative* in rank and median;
  - (b) the **arithmetic-mean tail**: the objective is expected USD, and the high-vol lottery
    tail can keep the mean near zero while the median is deeply negative;
  - (c) **maker execution in fast markets is unmeasured**, and the one measured fast-market
    instance was strongly adverse.
- Adding a memecoin universe to *live* trading is not supported.
- Adding it to *research* has value on one question only, (b), and on execution measurement (c),
  which can be done without trading.

**[REC] Experiment design, not a live change:** §I-5 (virtual maker-fill study) and §I-6
(forward high-vol arithmetic-vs-median ledger). Success/failure criteria are in the handoff.

---

## H′. Strategy tournament and ablation testing

**Tournament [INTERP]:**
- A tournament *under a frozen contract* removes the author's control over the evaluation after
  seeing results. That is the part of RDoF that per-study pre-registration does not cover across
  studies.
- It does **not** create power. Every entrant still needs hundreds of independent decisions for
  a 1% net edge (F4/F5).
- Picking the winner re-introduces selection, so the contract must pre-declare that the winner is
  compared against **null entrants** (random-entry, static-exposure, hold-LINK), with a
  max-statistic permutation across entrants.
- **Materially reduces overfitting: yes, for claims made from the forward ledger. It does not
  speed discovery.**

**Ablation [FACT-REPO]:**
- The components *can* be measured independently: `signal_redundancy.py` provides the
  condition-level joint distribution without outcomes.
- Measured: 11.4× tail co-firing over independence, 98.7% same-direction, mean +10.7% trailing
  24h at confluence ≥ 3.
- The confluence count is therefore **not** k independent confirmations.

[REC] Any future confluence-style signal must report:
1. its independence-null co-firing ratio;
2. a leave-one-out incremental test, where the outcome model includes a direct control for
   trailing return. This is Q1's subset enumeration with the trailing-return factor partialled
   out.

Do **not** re-run the ablation on outcomes on the historical cache: R6 already closed it (FWER
p = 0.971), and re-opening it would spend DoF for nothing.

---

## I. Recommended experiments (details and criteria in `NEXT_RESEARCH_HANDOFF.md`)

1. **I-1 Forward frozen-spec holdout (FROZEN-1).**
   - Register ≤ 3 specs whose code is hashed at freeze. Candidates: X4 low-vol filter as a
     *filter on the counterfactual ledger*; S2 alone at h = 5 with the static-exposure control
     (already requested by the live agent); the tactical_v4 gate as-is.
   - Evaluate only on data after the freeze date, at pre-declared review dates, by a script that
     prints the pre-registered statistic and nothing else.
   - Queries are budgeted.
2. **I-2 Decision snapshot + version fingerprint.** Schema in the handoff. Implemented as a
   *standalone recorder* the session calls, with no change to `execute.py`. The capture of
   model/CLI version in `launch_claude.sh` needs researcher approval (the live agent's own edit
   there was refused).
3. **I-3 Program trial ledger** (`research/TRIALS.jsonl`, append-only), back-filled from the
   registry. Program-level threshold reported next to every new POSITIVE.
4. **I-4 Regime labels on forward observations** plus one pre-registered interaction test
   (X4 × alt-led) when forward n allows.
5. **I-5 Virtual maker-fill study** (public trades only; no orders).
   - At random times, post a *virtual* bid/ask at the touch on pairs in each volatility
     quintile.
   - A fill happens when a print trades through the price within T.
   - Record fill probability, time-to-fill and **post-fill markout** at 1/5/30 min.
   - Answers R5's volatile-fill gap and E5's metric question without risking capital.
6. **I-6 Forward high-vol ledger.** Record the counterfactual for the top-volatility quintile
   at fixed times, not signal-triggered, which avoids chase selection. Measure the arithmetic
   mean, median and excess vs LINK net of measured costs. This directly tests §H(b)
   prospectively.
7. **I-7 Maker markout metric** — recommended to the live agent (execution_stats is live code).

---

## J. Changes that should NOT be made

| change | why not |
|---|---|
| Multi-agent bull/bear debate (TradingAgents) | Its evidence is a 3-month, cost-free, possibly contaminated backtest. Here, controls that *measure* already do the adversarial job. Debate adds LLM calls and narrative, not information |
| LLM-in-the-loop return prediction, or news-driven trading | Every external benchmark shows no robust edge (AI-Trader crypto: all agents lost). DXRG: prompt-stated risk and strategy text are overridden by the operating layer. Pre-cutoff backtests of LLM predictions are uninterpretable |
| Leaderboard or arena participation as validation | 17–45-day single-path results carry MDEs far above any plausible edge |
| Live regime-switching strategies | ~12 independent episodes. T1 null. R12 showed that "timing" gains were exposure |
| Live memecoin / high-vol universe expansion | X4/X4b say high-vol names have negative rank/median excess. The high-vol maker fill is unmeasured. DXRG memecoin vaults: median 0.49× |
| Lowering the trade gate or `MIN_ABS_EDGE_PCT` because more research time exists | Registry horizon amendment. Nothing in this audit is evidence of p > 0.50 |
| Adding more confluence conditions | Measured tail redundancy; more correlated up-move conditions add no independent confirmation |
| Formal Thresholdout / differential-privacy holdout | ~22–35 holdout periods; noise at useful privacy levels would swamp the signal. A forward holdout plus a query budget is simpler and stronger |
| Retroactive PBO/CSCV or Deflated Sharpe on R3/R6/R9 grids | Already rejected with stronger tests; zero new information |
| A second-model-family "external validator" | Pre-cutoff priors are shared across frontier models, and DXRG found them indistinguishable on replay. Cost without clear information |
| Treating X4's holdout t = −6.87 or X4b as independent confirmation | Selection-contaminated (§E1). Cite the discovery result, the program-level threshold, and external literature instead |

---

## K. Proposed next research architecture

```
             ┌──────────────────────── PRE-CUTOFF HISTORY (2014 → freeze date) ─────────────────┐
             │  EXPLORATION ONLY. Results labelled "exploratory (pre-cutoff, prior-exposed)".   │
             │  May generate hypotheses and kill them. May NOT confirm them.                    │
             └───────────────┬──────────────────────────────────────────────────────────────────┘
                             │ candidate survives discovery + program-level threshold
                             ▼
     FREEZE: spec.json + sha256(code, spec, data-schema) + review dates + query budget
             committed to research/frozen/<id>/ ; appended to research/TRIALS.jsonl
                             │
                             ▼
     FORWARD LOCKED HOLDOUT: only data with timestamp > freeze_ts. Evaluated by
     research/frozen/evaluate.py <id>, which prints ONLY the pre-registered statistic,
     and only on/after a review date; each call appended to research/frozen/ACCESS.jsonl.
     Entrants always include ≥2 null controls (random-entry, static-exposure / hold-LINK).
                             │
                             ▼
     VERDICT on pre-declared rule (max-statistic across entrants) → REGISTRY
                             │  (POSITIVE only)
                             ▼
     LIVE AGENT independently re-validates → its own ACCEPT/REJECT → gate unchanged unless
     the live agent decides otherwise.

     In parallel, on the live side (live agent's decision): every escalated/periodic decision
     appends a hash-chained DECISION SNAPSHOT (schema in handoff) with regime labels and
     version fingerprints, which becomes the replay + telemetry + forward-regime dataset.
```

**How the holdout is protected from the autonomous agent**, stated honestly. Public market data
cannot be hidden from an agent with internet access. The protection therefore rests on four
things:
- (1) **time**: data after freeze did not exist when the spec was frozen;
- (2) **hash-committed specs**, so any post-freeze change is detectable;
- (3) an **access log plus budget**, so peeking is recorded and scarce;
- (4) a **norm with a tripwire**: any analysis touching post-freeze outcomes outside
  `evaluate.py` must be logged in `ACCESS.jsonl`. The cloud guard *could* enforce a path-level
  block on `research/frozen/**/outcomes*`, but changing guards is a researcher decision (§L).

---

## L. Implementation roadmap

| step | owner | effort | needs human approval? |
|---|---|---|---|
| 1. Add `research/TRIALS.jsonl` (append-only) and back-fill ≈ 266 tests from the registry | Research Agent | S | no |
| 2. Add `research/frozen/` convention, the `evaluate.py` template and `ACCESS.jsonl`; freeze FROZEN-1 specs with hashes; set the freeze date to *after* the push | Research Agent | M | no |
| 3. Pre-registration template: add `sha256` of analysis code, the model knowledge-cutoff statement, and a "prior exposure" disclosure (which holdout tables the author has seen) | Research Agent | S | no |
| 4. Decision-snapshot recorder (`scripts/decision_snapshot.py`, standalone, append-only, hash-chained) + the session routine calls it | **Live agent** | M | Live agent decides. Capturing model/CLI version inside `launch_claude.sh` → **researcher approval** |
| 5. Virtual maker-fill study (I-5), public data only | Research Agent | M | no |
| 6. Maker markout metric in `execution_stats.py` | **Live agent** | S | live agent's decision (live code) |
| 7. Forward high-vol ledger (I-6) and regime labels (I-4) on counterfactual rows | Live agent (ledger lives on the VM) | S–M | live agent's decision |
| 8. Optional: cloud-guard rule blocking unlogged reads of frozen outcomes | researcher | S | **yes** — guards are part of the safety boundary |
| 9. Retire the phrase "holdout confirmed" for any pre-cutoff study in new findings | Research Agent | — | no |

**What would change these conclusions:**
- **Evidence of genuinely post-cutoff data in a past holdout** would weaken E1.
- **A measured maker markout in volatile markets that is small** would weaken H(c).
- **A frozen spec passing the forward holdout against its null entrants** would be the first
  uncontaminated positive result in the project. It would supersede everything above about
  whether an edge exists.

---

### Sources
- Agent Market Arena: https://arxiv.org/abs/2510.11695
- AI-Trader: https://arxiv.org/abs/2512.10971 · https://github.com/HKUDS/AI-Trader
- DXRG continuous record: https://arxiv.org/abs/2609.05663 · https://github.com/ProjectDXAI/continuous-record-llm-trading-agents
- TradingAgents: https://arxiv.org/abs/2412.20138
- Alpha Arena: https://nof1.ai/blog/TechPost1
- TradeRank methodology: https://www.traderank.ai/how-it-works
- ClawStreet: https://docs.clawstreet.io/
- Probability of Backtest Overfitting: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Reusable holdout: https://www.science.org/doi/10.1126/science.aaa9375
- LLM look-ahead: https://arxiv.org/abs/2512.23847 · https://arxiv.org/pdf/2608.02985 · https://arxiv.org/html/2605.24564
- Crypto low-volatility anomaly: https://www.sciencedirect.com/science/article/abs/pii/S1544612326003818 · https://www.sciencedirect.com/science/article/abs/pii/S154461232030667X
