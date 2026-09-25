# NEXT RESEARCH HANDOFF — from the independent audit (2026-09-25)

**For:** the Research Agent (cloud) and, where marked, the live agent.
**From:** the independent audit agent. Full report: `research/audits/external_agent_audit_2026-09-25.md`.
Machine-readable: `research/audits/external_agent_capability_matrix.json`.

This file contains **evidence and recommendations, not instructions.** Nothing here changes a
gate, a threshold, allocation, execution code, the monitor, `CLAUDE.md` or `researcher/`. Accept,
reject or modify each item on its merits, and record the verdict as usual. Per `PROGRAM.md`,
rejections are evidence.

---

## 1. Findings (measured or verifiable; each reproducible from `research/audits/`)

| id | finding | evidence | label |
|---|---|---|---|
| AU1 | The 2024-01 → 2026-09 holdout is shared by T1, X1, X3, X4, X4b, X5, X6 and R12/R13, and X4 was pre-registered 76 s after X1's holdout tables were committed, including a vol-controlled IC on that holdout. All research data also predates the model's knowledge cutoff (June 2026). **X4's holdout t = −6.87 and X4b are not independent confirmations.** X4's *discovery* result (t = −4.28, p ≈ 1e-4) still clears a program-wide Bonferroni over ≈ 266 tests and matches external literature, so the information claim likely stands. **X6** (built on X4, same grid and holdout) has a discovery t = 2.68 that does **not** clear the program-level bar, so its holdout t = 3.45 is from the reused window | commits `f4f4086` → `4754441`; BACKLOG log 23:20Z; `holdout_reuse_sim.py` | methodological defect (registry AU1) |
| AU2 | Under a global null, peeking at the holdout raises the holdout-stage pass rate from 5% to 44–88%. The per-study false-positive rate stays ~0.3–0.6% only because discovery remains independent. With prior exposure to both periods it rises to 1.3% per study (**12% chance of ≥ 1 false POSITIVE over 10 studies**, K = 20) | `results/holdout_reuse_sim.json` | simulation |
| AU3 | Confluence ≥ 3 co-fires **11.4×** more often than independence predicts (3.20% vs 0.28%). 98.7% of those cases follow a positive 24h return (mean +10.7%). Pairwise correlation is modest (M_eff 4.7/5): **the dependence is in the tail** | `results/signal_redundancy.json` (20 pairs × 715 4h bars) | measured; confirms D4 |
| AU4 | Across 115 Kraken USD pairs, spread scales with σ at an elasticity of 0.64. The round-trip cost as a share of a 3-day σ falls 15.8% → 5.2% (maker floor) and 30% → 9.8% (taker) from the lowest to the highest volatility quintile. **Cost is not what disqualifies high-vol names; the sign of the predictable component is (X4).** High-vol maker fills and markout remain unmeasured | `results/vol_vs_cost.json` (snapshot 23:31Z) | measured (single snapshot) |
| AU5 | History holds only ~12 independent BTC vol/trend regime episodes (652 weeks), 28 alt-led episodes, and 14 correlation episodes. Regime-conditioned rules cannot be fitted on this | `results/regime_episodes.json` | measured |
| AU6 | No record carries a code, strategy or prompt version. The shadow ledger labels every row `tactical_v4` while `predicted_prob` spans 0.50/0.56/0.59/0.62 across the R7 change. Decision inputs are not retained (`escalation_context.json` is overwritten and gitignored) | `data/shadow_trades.json`; `.gitignore` | verifiable |
| AU7 | `execution_stats.adverse_bps` is submit→fill mid drift, not post-fill markout. For resting orders it is partly mechanical | `scripts/execution_stats.py` `record()` | plausible, unverified (n = 2) |

External context (details in the audit, §D):
- No external LLM-trading project models costs as carefully as this repo.
- Live-only evaluation (AMA, AI-Trader) is the external standard against look-ahead.
- DXRG's per-turn provenance join is the most transferable practice.
- Leaderboards (Alpha Arena, TradeRank, ClawStreet) carry no evidence of transferable alpha.

## 2. Unresolved questions

1. **Is there any genuinely uncontaminated evidence for any edge?** Today: no. Every research
   dataset predates the model cutoff, and the forward ledgers are unfrozen and tiny
   (16 opportunities from 2 decision hours).
2. **Is the high-vol arithmetic mean (lottery tail) positive after costs, even though the median
   and rank are negative?** X4 found discovery means ≈ equal and holdout means strongly negative.
   This is the only open case for high-vol exposure under an *expected-USD* objective.
3. **What are the maker fill probability and post-fill markout in volatile regimes?** n = 0. It
   bounds every high-vol or event-driven idea.
4. **Does X4's low-vol ordering weaken in alt-led / risk-on episodes?** It is the only regime
   question with plausible power (28 episodes) and decision value.
5. **Was any past pre-registration preceded by uncommitted exploration?** Nothing suggests it,
   but the mechanism cannot show it. Future pre-registrations can close this (§4 C3).

## 3. Proposed experiments (ordered by expected information value)

### P1 — FROZEN-1: forward frozen-spec holdout and mini-tournament (HIGH)
- **What:**
  - Create `research/frozen/<id>/spec.json` with the hypothesis, universe rule, signal code
    path, cost model (A1: 0.46%/maker leg, 0.83% taker), benchmark (hold-LINK), primary
    statistic, decision rule, review dates and a query budget.
  - Add `sha256` of the spec and code.
  - Set `freeze_ts` to the push time.
  - Entrants, ≤ 6:
    - (a) X4 low-vol filter applied to the counterfactual/shadow candidate stream (does
      filtering out top-vol-quintile candidates improve excess vs LINK?);
    - (b) S2 alone at h = 5 **with the static-exposure control** (the live agent's standing
      request);
    - (c) `tactical_v4` gate as-is;
    - **null (d): random-entry at matched times;**
    - **null (e): static exposure / hold-LINK.**
- **Evaluation:** only on bars with `ts > freeze_ts`, only via `research/frozen/evaluate.py`,
  which prints only the pre-registered statistic. Log every call to
  `research/frozen/ACCESS.jsonl`. Compare entrants against the nulls by max-statistic
  permutation across entrants.
- **Controls:**
  - no edits to the spec after freeze (a hash mismatch voids the entrant);
  - non-overlapping evaluation windows;
  - report the MDE at each review date.
- **Success:** an entrant beats both nulls on the pre-registered statistic with max-stat
  permutation p < 0.05 **and** the MDE at that date ≤ the effect size claimed.
  **Failure/stop:** effect CI excludes the cost hurdle on the upside (i.e. the edge is smaller
  than cost) at MDE ≤ 1% net, or the query budget is exhausted.
- **Honest expectation:** F4/F5 imply 200–790 days before a 1% net edge is resolvable. The
  value is that the first positive, if it ever comes, will be *uncontaminated*.

### P2 — Program trial ledger `research/TRIALS.jsonl` (MEDIUM, cheap)
- **What:** an append-only row per formal test: `id`, `study`, `date`, `hypothesis`, `data
  window`, `statistic`, `p`, `family`, `pre-registered (bool)`, `holdout_window`,
  `prior_exposure` (which earlier tables covering this window the author had seen).
  - Back-fill ≈ 266 rows from REGISTRY/findings. Approximate counts are fine; mark
    `backfilled: true`.
- **Use:** every new POSITIVE reports the program-level Bonferroni/Holm threshold at that
  count, next to its per-study threshold.
- **Success:** one line per finding stating whether it clears the program-level bar.
  **Failure mode to avoid:** not logging exploratory runs. Log them, labelled `exploratory`.

### P3 — Virtual maker-fill and markout study (MEDIUM; public data, no orders)
- **What:**
  - At pre-registered random times, for pairs sampled across volatility quintiles, place a
    *virtual* post-only bid (and ask) at the touch.
  - A fill occurs when a public trade prints through the price within T ∈ {1, 5, 30} min.
  - Record fill probability, time-to-fill and **post-fill markout** (mid at fill + {1, 5, 30}
    min vs fill price), by quintile and by 1d/30d vol ratio (calm vs volatile, matching
    `execution_stats`).
- **Controls:**
  - queue position is unknown, so treat a trade *at* the price as a fill only with probability
    ½ (report the bounds);
  - separate by side;
  - LINKUSD as the calm anchor.
- **Success:** volatile-regime fill probability and markout with 95% CIs narrower than ±15 pp and
  ±10 bps. This replaces the 50% prior and the 5.4 bps calm figure with measurements.
- **Failure:** CIs still wider after 2 weeks of sampling. Report as INCONCLUSIVE with the MDE.

### P4 — Forward high-vol ledger (MEDIUM; live-agent-side data)
- **What:** at fixed times, **not** signal-triggered (avoiding chase selection, DXRG
  chase-state), record hypothetical entries in the top volatility quintile and the bottom
  quintile.
- **Measure:** the arithmetic mean, median and excess vs LINK at 72h / 7d / 28d, net of P3's
  measured costs.
- **Success:** the answer to question 2 with a clustered CI. Pre-register now that the decision
  statistic is the **arithmetic** mean (objective = expected USD) and that the median is
  reported alongside.

### P5 — Regime labels on forward rows, then one interaction test (LOW-MEDIUM)
- **What:** label forward rows (P1, P4, the counterfactual ledger) with BTC vol state, BTC
  trend, alt-led flag, correlation state and spread stress, computed with the definitions in
  `research/audits/regime_episodes.py`.
- **Test:** one test only, pre-registered: *does X4's low-vol ordering weaken in alt-led
  episodes?* Evaluate on forward data only.
- **Do not** fit regime-switching rules.

### P6 — Decision snapshot and version fingerprint (HIGH value, but live-agent / researcher owned)
Proposed schema: one JSON line per decision, append-only, in `data/decision_snapshots.jsonl` on
the VM, mirrored to the repo.

```json
{
  "snapshot_id": "ds-<utc>-<seq>", "prev_sha256": "<hash of previous line>",
  "ts": "...", "session_id": "...", "trigger": "escalation|periodic|manual",
  "experiment_id": "live-v2|FROZEN-1-...|null",
  "versions": {"git_commit": "...", "sha256": {"CLAUDE.md": "...", "STRATEGY.md": "...",
     "scripts/edge.py": "...", "scripts/tactical.py": "...", "scripts/monitor.py": "...",
     "launch_prompt": "..."},
     "model_id": "...", "cli_version": "..."},
  "data_cutoff_ts": "<latest market timestamp used>",
  "market": {"holdings": {}, "total_usd": 0, "benchmark_usd": 0,
     "quotes": {"PAIR": {"bid": 0, "ask": 0}}, "regime": {"btc_vol_high": true,
     "btc_trend_up": true, "alt_led": false, "high_corr": true, "spread_stress": false}},
  "inputs": {"escalation_context_sha256": "...", "queue_ids": [], "gate_outputs": []},
  "assumed_costs": {"taker_leg_pct": 0.83, "maker_leg_pct": 0.46, "fill_prob_source": "..."},
  "hypotheses_considered": [{"id": "...", "verdict": "rejected|deferred|accepted",
     "reason_code": "no_edge_p050|cost|spread|unsizable|..."}],
  "decision": "HOLD|TRADE|REBALANCE|STRATEGY_CHANGE", "confidence": null,
  "orders": [], "duration_sec": 0, "tools_used_counts": {"Bash": 0, "Edit": 0},
  "research_queries": 0
}
```

- **Do NOT record:** chain-of-thought or free-form reasoning beyond the existing `reasoning`
  field, credentials, balances beyond what `activity.jsonl` already holds, or anything from
  `.env`.
- **Owner:** the live agent, via a standalone `scripts/decision_snapshot.py` the session calls.
  It needs **no** `execute.py` change. Capturing `model_id` and `cli_version` inside
  `launch_claude.sh` needs **researcher approval** (the live agent's own edit there was refused).
- **Cheapest validation:** after 10 snapshots, attempt a replay of one decision from its
  snapshot alone. If it cannot be reconstructed, the schema is missing a field.

### P7 — Maker markout metric (LOW now; live agent)
Add post-fill markout (mid at fill + 1/5/30 min vs fill price) next to the existing
`adverse_bps` in `scripts/execution_stats.py`. Do not replace the old field; the record is
append-only. This is live code: the live agent's decision.

## 4. Required controls (apply to every new study)

1. **C1 Prior-exposure disclosure.** Every pre-registration states which earlier results
   covering the same window the author has seen, and the model's knowledge cutoff.
2. **C2 "Holdout" terminology.** A window that predates the cutoff, or that earlier studies have
   evaluated, is labelled *"reused / pre-cutoff holdout — not independent confirmation"*. Only
   post-freeze forward data is called a locked holdout.
3. **C3 Code hash in the pre-registration.** Commit `sha256` of the analysis script at
   pre-registration time. If the code changes before the results, record the diff and the
   reason in the finding.
4. **C4 Program-level threshold** reported beside every POSITIVE (P2).
5. **C5 Composite signals** report the independence-null co-firing ratio (as
   `signal_redundancy.py` does) and a trailing-return-controlled leave-one-out.
6. **C6 Nulls in every tournament:** random-entry at matched times and static exposure.
7. **Unchanged:** costs from A1, non-overlap, clustered CIs, MDE on nulls, benchmark = hold-LINK
   plus static exposure.

## 5. What should NOT be implemented (and why)

- **Multi-agent bull/bear debate:** no measured benefit; it argues rather than measures, and the
  controls here already do the adversarial job.
- **LLM return prediction or news trading:** externally unprofitable and uninterpretable
  pre-cutoff.
- **Leaderboard/arena participation as validation:** single-path, short-window, cost-free.
- **Live regime switching:** ~12 episodes; T1 null; R12 exposure lesson.
- **Live high-vol/memecoin expansion:** X4/X4b negative rank/median; unmeasured volatile fills.
- **Lowering any gate, or adding more confluence conditions:** AU3; horizon amendment.
- **Thresholdout / DP holdout, retroactive PBO/CSCV/DSR on rejected grids, second-model-family
  validators:** little or no incremental information here.
- **Citing X4's holdout or X4b as independent confirmation** (AU1).

## 6. Priority (expected information value per unit cost)

| rank | item | owner | why |
|---|---|---|---|
| 1 | P2 trial ledger + C1–C4 controls | Research Agent | near-zero cost; changes how every future result is read |
| 2 | P1 FROZEN-1 | Research Agent | only route to uncontaminated evidence; value accrues with time, so start now |
| 3 | P6 decision snapshot | live agent (+ researcher for the launcher) | cheap; makes every future decision replayable and regime-labelled |
| 4 | P3 virtual maker-fill study | Research Agent | closes the largest unmeasured cost term with zero capital risk |
| 5 | P4 forward high-vol ledger | live agent | answers the only open case for high-vol exposure |
| 6 | P5 regime labels + one test | both | low power; labels are cheap, the test waits for n |
| 7 | P7 markout metric | live agent | matters only before volatile maker trading |

## 7. Items requiring human (researcher) approval

1. Recording `model_id` and `cli_version` in `scripts/launch_claude.sh`. The launcher is outside
   what the live agent may self-modify.
2. Any cloud-guard rule enforcing the frozen-holdout access log. Guards are part of the safety
   boundary.
3. Whether session transcripts (currently gitignored) may be retained or committed in summarised
   form. This is a privacy and size decision.
4. Whether the program adopts a formal program-level α budget (P2's threshold as binding rather
   than advisory).
