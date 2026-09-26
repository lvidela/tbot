# Research backlog

Maintained by the Research Agent under `research/PROGRAM.md`.
- **Priority** is a judgement of three things: the plausible net edge after 0.46%/leg costs at a
  ~$58 account, how new the mechanism or data is relative to REGISTRY R1–R13, and whether it is
  feasible with public data.
- **The table is a snapshot.** The **Log** at the bottom is append-only, and its latest entry
  wins.

## Queue (snapshot 2026-09-25)

| id | hypothesis / objective | mechanism | data | why now / novelty | priority | status |
|---|---|---|---|---|---|---|
| X1 | Assets with high trailing perp funding underperform low-funding assets over the next 1–4 weeks | Funding measures leveraged-long crowding. Crowded longs pay carry and unwind | Binance archive: USDT-perp funding + spot 1d, **incl. delisted** (survivorship-free) | New dataset. Funding was only ever tested as LINK timing (T1 S6), never cross-sectionally. Weekly/monthly turnover suits 0.46% legs | 1 | **active** |
| X2 | High open-interest growth or an extreme long/short account ratio predicts cross-sectional underperformance | Positioning crowding, a second measure independent of funding | Binance archive `futures/um/daily/metrics` (from ~2021-12) | New dataset; shares X1's infrastructure | 2 | queued |
| X3 | After market-wide capitulation hours (BTC and the alt index down more than k·σ within hours), alts rebound over 1–3 days | Forced liquidations overshoot; liquidity providers are paid to absorb | Binance spot 1h archive (multi-year), Coinbase 1h cross-check | R4 tested only unconditional autocorrelation, and vol_expansion was demeaned on a short sample. A conditional, market-level event with large moves has not been tested | 3 | queued |
| X4 | A low-volatility / low-beta cross-section beats high-beta over a month (a betting-against-beta analogue) | Leverage-constrained buyers overpay for lottery-like, high-beta coins | X1 universe, monthly rebalance | A different mechanism from momentum/reversal (R3, R9); low turnover | 4 | queued |
| X5 | Deribit DVOL (BTC/ETH implied vol) level or term structure times LINK-vs-USD exposure | The volatility risk premium; implied vs realised as a regime signal | Deribit public API (reachable) | New dataset. T1 used only price- and funding-based states | 5 | queued |
| X6 | Post-listing drift: newly listed perps/spot underperform for their first N weeks | Hype decay and supply unlocks | Binance archive first-file dates | Mostly an *avoidance* rule for spot; lower value | 6 | queued |
| X7 | Stablecoin depegs (USDT/USDC vs USD) mean-revert fast enough to capture | Arbitrageurs restore the peg | Coinbase USDT-USD / USDC; Kraken 720 bars | Rare events, small n | 7 | queued |
| X8 | Day-of-week / time-of-day return effects | Flow seasonality | 1h archive | Expected magnitude is well below a 0.92% switch; kept only as an execution-timing input | 9 | parked (magnitude) |
| X9 | Cross-exchange price dislocations | Fragmented liquidity | multi-venue | **Not actionable:** the live agent trades one venue and may not transfer funds | — | closed by constraint |

## Log (append-only)

- **2026-09-25:** program started under researcher directive (`research/PROGRAM.md`). X1 chosen
  first, because it:
  - is the only candidate combining new data, a mechanism untested here, low turnover, and a
    survivorship-free universe (delisted perps are in the archive, e.g. LUNAUSDT);
  - builds the infrastructure that X2, X4 and X6 reuse.
- **2026-09-25 23:20Z — X1 closed: NEGATIVE.** Finding `2026-09-25_x1_funding_crowding.md`.
  - **Evidence:** strong against the spot-actionable form (holdout CIs exclude 0 on the harmful
    side). The information test is unstable: the IC sign flips between 2020–23 and 2024–26.
  - **Learned:**
    1. Positioning signals are regime-dependent in sign.
    2. Extreme negative funding marks distressed coins.
    3. The survivorship-free liquid-alt basket was 0.16× vs LINK 0.84× in 2024–26, so broad
       rotation priors should be pessimistic.
  - **Invalidation:** a new regime with a negative IC on a fresh holdout.
  - **Re-prioritisation:**
    - X2 (OI / long-short ratio) is demoted to priority 5. It measures the same crowding
      mechanism, and X1 shows that mechanism's sign is unstable.
    - **X4 (low-vol / low-beta cross-section, monthly) is next.** It reuses X1's survivorship-free
      panel. It is the only rotation idea whose mechanism predicts the 2024–26 pattern (high-vol
      alts bleeding) ex ante. At monthly turnover it could clear 0.92% switches. It also answers
      R13's "hold another asset" question with far more assets than a single pair.
    - X3 (capitulation rebound) follows.
- **2026-09-25 23:25Z — X4 closed: REQUIRES VALIDATION.** Finding
  `2026-09-26_x4_low_volatility.md`.
  - **Evidence:** strong for information (holdout t = −6.87, every year negative). Weak for
    economics vs the live holding (hold-LINK/BTC CIs span 0).
  - **Learned:** unlike positioning (X1), volatility ranks are regime-stable. The decision value
    is as a filter against high-vol rotation and tactical entries, not as a switch.
  - **Invalidation:** a positive IC over two consecutive quarters of fresh data.
  - **Next:** X4b, a **venue replication on Kraken's own public daily data**. It is cheap, and it
    is exactly what the live agent would need before any filter:
    - `research/tsmom/ohlc_long.json`, 20 Kraken assets, 2024-10 → 2026-09;
    - pre-registered IC(vol60, fwd 28d) < 0.
  - **Then:** X3 (capitulation rebound).
  - **New idea (priority 4):** X12, vol-managed exposure to LINK itself. Scale LINK exposure
    inversely to its trailing volatility (the time-series analogue of X4). It needs the
    static-exposure control from the live agent's S2 request.
- **2026-09-25 23:35Z — X4b closed: POSITIVE (replication).** Kraken IC −0.195 (t = −4.69). The
  low-vol effect is venue-robust. The filter recommendation stands; there is no switch
  recommendation.
  - **Next: X3,** capitulation rebound. Pre-register first. It uses daily data already in hand:
    X1's survivorship-free panel and Coinbase for BTC/LINK. An hourly version comes only if the
    daily result is promising.
- **2026-09-25 23:50Z — X3 closed.** INCONCLUSIVE for information; NEGATIVE for the tactical
  rule.
  - **Learned:** crash-day rebounds at daily resolution are below the MDE of 4–9%. The
    most-crashed tilt is directionally consistent but tiny, and 4-leg costs dominate.
  - **Follow-up, parked:** X3h, an hourly liquidation-cascade version. It needs the 1h archive
    (~1 GB), and it is worth it only if the daily version had shown signal, which it did not.
  - **Next: X12,** vol-managed LINK exposure. Scale LINK exposure by target-vol / trailing vol,
    rebalance weekly, and compare against a **static-exposure control** at the same average
    weight (the live agent's S2 request) plus hold-LINK/USD.
    - **Mechanism:** the time-series analogue of X4, with volatility clustering and a lower
      conditional Sharpe ratio in high-vol states.
    - **Data:** Coinbase and Binance LINK daily since 2019.
    - **Why:** it is the only timing idea supported by a mechanism X4 just confirmed
      cross-sectionally.
- **2026-09-25 23:55Z — X12 dropped before pre-registration.** Vol-managed LINK exposure is a
  continuous re-parameterisation of T1's S5 (LINK calm-vol state), which was INCONCLUSIVE with
  the direction mostly opposite to the registered one.
  - **Reopen only with** a materially different method (e.g. intraday realised vol, or
    implied-vol inputs via X5) or new data.
  - **Next: X6,** listing age / post-listing drift. It uses listing dates already in the
    survivorship-free panel, is decision-relevant to the live agent's dynamic universe, and
    carries a mechanism (unlock/hype decay) distinct from volatility, which it must control for.
- **2026-09-26 00:05Z — X6 closed.** POSITIVE for information (age beyond volatility, both
  periods); NEGATIVE as a filter.
  - **Cross-study lesson (X4, X6):** cross-sectional characteristics predict *ranks* and medians
    robustly, but mean-return spreads are often undetectable because of lottery right tails.
    Under the stated objective (expected final USD), such filters have ~0 value. Whether the
    objective should be expected or median is a researcher question, already flagged by F4.
  - **Next: X5,** Deribit DVOL (BTC/ETH implied vol) as a state variable for crypto exposure.
    - **Mechanism:** the variance risk premium. High implied-minus-realised vol predicts higher
      forward returns.
    - **Why:** it is the only remaining queued item with a new dataset and a mechanism not
      tested here.
    - **Must include:** T1-style power analysis and the static-exposure control.
  - **Then:** X2 (OI), demoted.
- **Correction (appended, 2026-09-25 23:40Z):** the entry above stamped "2026-09-26 00:05Z" and
  X5's pre-registration date "2026-09-26" are wrong. The system clock read 2026-09-25 ~23:25Z at
  the time. The order of events is unaffected.
- **2026-09-25 23:40Z — X5 closed: NEGATIVE** (power-limited, MDE 13–17% per 28d). The VRP timing
  rule lost to its static-exposure control in both periods.
  - **Learned:** every kind of market-timing state tried (price, trend, realised vol, funding,
    implied vol) has failed or is below the MDE at 28-day horizons. The binding constraint is
    calendar span, not signal choice.
  - **Next session:** X2, cross-sectional OI growth and the long/short ratio.
    - Use `futures/um/daily/metrics`, sampled **only on Mondays** (~20k requests), so it stays
      cheap.
    - The prior is low after X1, but it is new data. It must control for vol60, age and funding,
      because X4, X6 and X1 all found those relevant.
  - **After that,** in this order:
    - X7 (stablecoin depegs, Coinbase USDT-USD / USDC);
    - X3h (hourly liquidation cascades), only if a cheap event source exists;
    - a new-hypothesis scan: expected-vs-median, i.e. do rank effects (X4/X6) translate into
      *mean* gains at 2-leg cost under any objective the researchers endorse. This one is a
      question for the researchers, not a study.
- **2026-09-25 23:45Z — independent audit delivered** (audit agent, not the
  Research Agent): `research/audits/NEXT_RESEARCH_HANDOFF.md`. The registry gained AU1–AU4.
  - **Top items, by information value:**
    1. a program-wide trial ledger (`research/TRIALS.jsonl`) and prior-exposure controls C1–C4;
    2. a forward frozen-spec holdout (FROZEN-1), with null entrants;
    3. a decision-snapshot schema (live agent);
    4. a virtual maker-fill/markout study on public trades.
  - **For X2 (next in the queue) and later studies:** any 2024–26 window is a *reused,
    pre-cutoff* holdout (AU1; eight studies share it). Label it so, add the prior-exposure
    disclosure (C1) to the pre-registration, and report the program-level threshold (C4).
- **2026-09-25 — audit received (`research/audits/NEXT_RESEARCH_HANDOFF.md`) and applied.**
  - **Verdicts:** `findings/2026-09-25_audit_response.md`.
  - **Done:**
    - P2 trial ledger (`TRIALS.jsonl`, `trials.py`);
    - C1–C6 appended to PROGRAM.md;
    - P1 FROZEN-1 frozen, first review 2026-12-26. **Do not evaluate before then.**
  - **Re-prioritised queue:**
    1. **P3, the virtual maker-fill and markout study** on Kraken public trades and order book.
       It covers the largest unmeasured cost term and involves no orders. Pre-register it next,
       with a sampler that runs in bursts during each routine session, and state the sparseness
       limitation.
    2. **P5 regime labels,** for FROZEN-1 forward rows once they exist.
    3. **FROZEN-1 reviews,** on the scheduled dates only.
    4. **X2 (historical OI):** demoted. Pre-cutoff, so its value is discovery-stage only at the
       program bar.
    5. **X7 stablecoin depegs:** demoted likewise.
  - **Standing rule from the audit:** a historical study is worth running only if its discovery
    stage could clear p < 0.05/K and it would feed a new FROZEN entrant.
- **2026-09-26 ~01:10Z — P3 started** (pre-registration `research/p3_maker/PREREGISTRATION.md`).
  The sampler runs in ≤ 3.5 h bursts per routine session.
  - **Each session:** if the sampler isn't running, start it with
    `setsid nohup python3 research/p3_maker/sampler.py --hours 3.5 &`. Then run
    `python3 research/p3_maker/analyze.py` to resolve orders and write the descriptive
    `results.json`. Commit `derived/` and `results.json`, and push/merge.
  - **No P3 tests** before the final report (targets met, or 2026-10-10).
  - **Meanwhile:** new, genuinely different hypotheses can be pre-registered in parallel.
- **Correction:** the P3 start entry above says ~01:10Z. The pre-registration commit `199d3c5` is 2026-09-26 00:51:45Z, and the sampler started ~00:52Z.
- **2026-09-26 ~04:50Z — P3 interim 1 (descriptive only; no tests before the final report).**
  - **Run 1:** 3.5 h, 321 virtual orders, 0 errors. 234 resolved, **all calm**; no pair was in the
    volatile regime during the run.
  - **5-min fill rate (mid estimate):** bid 72% [64, 79], ask 68% [61, 75].
  - **5-min post-fill markout, strict fills:** bid −4.4 bps [−9.2, +0.2], ask −9.5 bps
    [−15.5, −3.6]. That is more adverse than A1's 5.4 bps, though the metric differs (AU7).
  - The sampler was restarted for run 2.
- **Live-agent input read** (`findings/2026-09-26_live_candidate_volatility_bias.md`,
  `2026-09-26_broadened_alpha_program.md`).
  - X4 adopted by the live agent as a veto only.
  - 18 of 22 live candidates sit above LINK's volatility rank.
  - Rejected opportunities at 6h: CI (−3.24, −0.18), so the gate is avoiding losses.
  - The live agent proposes: A1 conditional reversal in the held asset (2 legs), A2
    regime-conditional re-slices, A3 wide-divergence relative value.
  - **Taken next:** A1 as **X8**, a LINK hourly spike reversal. Pre-registered with its discovery
    stage judged at the program bar. If it passes, it becomes a FROZEN-2 forward entrant.
- **2026-09-26 ~05:05Z — X8 closed: NEGATIVE** (live-agent A1, up-spike direction).
  - **Result:** precise null, MDE 0.15–1.3%. Up-spikes show no reversal (slight continuation),
    and exiting costs about the full 0.92% or more. K = 268.
  - **Next candidates:**
    - (a) **A3 wide-divergence relative value.** Pre-register only the ≥ Xσ divergence
      conditional, with the X4 veto respected (no rotating up the vol ranking). The discovery
      stage must be able to clear the program bar.
    - (b) **A2 regime-conditional re-slices.** Low priority: the audit (AU5, ~12 episodes) and
      the trial count argue against it.
    - (c) **P3 continues;** resolve and restart the sampler each session.
- **2026-09-26 ~08:50Z — P3 interim 2 (descriptive).**
  - 575 resolved orders, **still all calm**. The volatile label (|1d return| / 30d σ ≥ 1.5) has
    not fired on any sampled pair since the start.
  - **5-min fill:** bid 67%, ask 68%.
  - **5-min strict markout:** bid −1.8 bps (n = 475), ask −10.9 bps (n = 495).
  - By quintile, fill ranges 51–82%, and the ask markout is worst in Q4 (−25.9 bps).
  - **Risk to the pre-registered target:** volatile-regime precision may not be reached by
    2026-10-10. If so, P3 reports INCONCLUSIVE for volatile regimes, as pre-registered.
  - The sampler was restarted for run 3.
- **Next:** A3, wide-divergence relative value. Pre-registration follows.
- **2026-09-26 ~09:05Z — X9 closed: INCONCLUSIVE by rule, not actionable** (live-agent A3).
  Median negative everywhere; the discovery mean is explained by the random control. K = 272.
  - **Status of the live agent's proposals:** A1 is answered by X8 (NEGATIVE) and A3 by X9. A2
    (regime re-slices) is deprioritised per AU5 and the trial count.
  - **Next, highest value: FROZEN-2,** a forward high-vol vs low-vol arithmetic-mean ledger. It
    answers the audit's open question 2, the only case left for high-vol exposure under expected
    USD. It is fully computable later from Kraken **public** daily OHLC, including volume, so no
    live recording is needed.
    - **Pre-register now:** the universe rule (Kraken USD pairs with trailing volume ≥ X) and
      Monday 4-weekly baskets of the top and bottom vol quintiles.
    - **Decision statistic:** the **arithmetic** mean excess vs LINK. The median is reported
      alongside it.
    - Frozen with hashes; first review 2026-12-26.
  - **Also next:** P3 upkeep.
- **2026-09-26 ~09:20Z — FROZEN-2 frozen** (high-vol arithmetic-mean ledger, forward).
  - **Standing session chores from now on:**
    - (1) P3: resolve orders, restart the sampler, commit `derived/`;
    - (2) run `python3 research/frozen/FROZEN-2/archive.py` and commit `closes.jsonl`.
  - **Never evaluate** FROZEN-1 or FROZEN-2 before their review dates.
  - **Open research slots:** new hypotheses only if they are genuinely different and their
    discovery stage could clear the program bar (K = 272, so p < 1.8e-4), or they feed a new
    forward entrant.
  - **Candidate ideas to screen next session** (no work yet):
    - (i) LINK-specific non-price event feasibility (F4 C6: delisting, maintenance, minimum-order
      changes via Kraken public SystemStatus and AssetPairs). This is monitoring rather than
      statistics, and would be a proposal for the live agent.
    - (ii) Fee-tier economics as a function of account size. It documents when the rejected
      classes (R11, maker strategies) reopen, per the program's "viable at larger size" directive.
- **Correction:** the FROZEN-2 entry above says ~09:20Z; FREEZE.json records 2026-09-26T08:56:05Z. From now on, log entries cite commit or freeze timestamps rather than estimated times.
- **P3 amendment 1** (analyzer gap filter; see PREREGISTRATION.md).
  - Container restart around 10:31Z; the sampler was restarted.
  - Interim 3 (descriptive): 759 resolved, 574 used after the gap filter, all calm.
  - 5-min fill: bid 72%, ask 66%.
  - 5-min strict markout: bid −5.6 bps, ask −9.0 bps.
  - **Session chore added:** check `raw/log.jsonl` for ProxyError bursts; if present, restart the
    sampler.
- **Researcher update received: exploration capital unblocked.** 41 USDT was added; the sleeve is
  ≤ 10%, about $10.
  - **Answered with:**
    - X10: an independent check of the live agent's armed tail-reversal bet — did not replicate;
    - exploration proposals E1/E2 (`findings/2026-09-26_exploration_proposals.md`).
  - **Research priorities now:**
    - (1) keep P3 running. Its calibration against E1's live fills is the key deliverable once
      the live agent runs E1.
    - (2) FROZEN-1/2 archive chores.
    - (3) Prepare the E1 analysis script, which pairs each live order with P3's virtual
      prediction, so the evaluation is fixed before live data exists.
  - No new historical studies unless they feed a live or frozen entrant (audit standing rule).
