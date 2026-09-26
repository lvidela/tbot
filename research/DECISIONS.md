# Research decisions (append-only)

**Directive (researcher, 2026-09-26):** "you should do all decisions."

From now on the Research Agent decides every research-side question itself and records the
decision here, instead of escalating it.

**What this does not change:** the hard constraints stay absolute.
- Research never places live trades.
- The cloud guard is never modified.
- Protected files (CLAUDE.md, `researcher/`, the launcher) and live-owned records
  (`data/benchmark.json`) are never edited by research.

Where a decision needs one of those, research decides its position, and the owner executes it.

---

## D-1 Objective: expected final USD is the decision criterion
- **Decision:** research labels and recommendations use the **arithmetic expected value** of
  final net USD. Median, drawdown and hit rate are reported as diagnostics. They never override
  a sign or a significance result on the mean.
- **Reason:** CLAUDE.md §1 says "maximize the final USD value" and explicitly accepts losing
  capital. That is an expected-value objective, not a median or risk-adjusted one.
- **Consequences:**
  - X4/X6-style filters (rank and median effects without a mean effect) carry no expected-USD
    value. They are kept only where they cost nothing, like the live X4 veto, which forgoes
    nothing we have evidence for.
  - FROZEN-2's primary statistic (the arithmetic mean) is the right one.
  - F4's "objective change" trigger is closed.

## D-2 The program-level α is binding for POSITIVE
- **Decision:** a result may be labelled **POSITIVE** only if both hold:
  - (a) its discovery test clears the program-level Bonferroni bar (`research/trials.py`, today
    p < 0.05/273 ≈ 1.83e-4);
  - (b) it is confirmed on locked forward data (FROZEN-*) or live execution data.
- A per-study pass without these is **REQUIRES VALIDATION**.
- **Reason:** audit AU1/AU2 (reused, pre-cutoff holdouts).

## D-3 Deposit accounting (the 41 USDT, 2026-09-26)
- **Decision:** research comparisons use a **benchmark-plus-deposit** series:
  - 4.1944857200 LINK (the immutable passive benchmark, valued at the LINKUSD best bid);
  - plus each deposit, held in the asset in which it arrived: 41 USDT, valued at the USDTUSD best
    bid, per CLAUDE.md's valuation rule.
  - **Excess = portfolio `total_usd` − that series.**
- **Reason:** a deposit is capital, not performance. Holding it in the asset it arrived in is the
  zero-decision counterfactual.
- **Scope:** `data/benchmark.json` is immutable and live-owned, so it is not touched. The live
  agent should report the same series in STATE.md; research uses it in every comparison from now
  on.

## D-4 Live exploration: E1 GO, E2 minimum clip only, nothing else
- **E1 (maker-execution calibration): GO.**
  - Frozen evaluation spec: `research/e1_calibration/SPEC.md`.
  - **Pairs changed to LINKUSD/XBTUSD/XRPUSD,** the same books as P3, for exact calibration.
  - Hard stop −$5.
- **E2 (the armed LINK tail-reversal bet):** minimum clip (0.55 LINK) only, counted as a
  volatile-regime execution sample. It is not sized by conviction (X10: not replicated).
- **No alpha-seeking exploration trade:** nothing has a demonstrated positive net edge (D-2).
- **Execution belongs to the live agent** (hard constraint). This is research's decision on what
  is worth running.

## D-5 Audit §7 items
1. **`model_id` / `cli_version` in the launcher:** not needed for research validity. The launcher
   is protected, so research takes no action and does not request it.
2. **A guard rule for the frozen access log:** **declined.** Guards are the safety boundary, and
   each evaluator already self-enforces its log and budget. Research never modifies the guard.
3. **Session transcripts:** **not committed.** Findings, pre-registrations and the trial ledger
   are the research record; transcripts add size and privacy exposure without evidential value.
4. **A binding program α budget:** yes; see D-2.

## D-6 Standing research priorities (until superseded here)
1. **Execution evidence:** P3 (virtual, continuous) and E1 (live, once the live agent runs it).
   This is the only area where new data resolves open cost questions.
2. **Forward frozen ledgers:** FROZEN-1 and FROZEN-2. Evaluate only on their review dates.
3. **New historical studies:** only if their discovery stage could clear the program bar **and**
   they feed a frozen or live entrant.
4. **The live agent's proposals:** answered as they arrive (A1 → X8, A3 → X9, the armed bet →
   X10).

## D-7 P3 collection cannot be sustained in the cloud container (2026-09-26, 16:47Z session)
- **Evidence:** `research/p3_maker/raw/log.jsonl`.
  - Runs 1–2 completed their full 3.5 h (00:51–04:22Z, 04:46–08:16Z).
  - All later starts (08:46, 10:32, 12:46Z) died without a stop event, killed by container
    restarts or reclaims minutes to hours after a session goes idle.
  - Only 11 of the 93 orders resolved after that passed the gap filter.
- **Decision:**
  1. **P3's pre-registered final report stays on 2026-10-10.**
     - **Calm regime:** 585 usable orders; that half should reach its precision target.
     - **Volatile regime:** 0 orders so far. That half will very likely end INCONCLUSIVE, as the
       pre-registration anticipated.
     - No design or analysis change.
  2. **Each research session still restarts the sampler** (best effort; costless). Orders from
     broken windows are removed by amendment 1's gap filter, so this cannot bias the results.
  3. **E1's volatile stratum becomes the primary route** to volatile-market fill and markout
     evidence (D-4).
  4. **Research position (live-owned action):** the unchanged `research/p3_maker/sampler.py`
     could run continuously on the live VM.
     - It uses only unauthenticated public Kraken endpoints, places no orders, reads no
       credentials, and writes only to `research/p3_maker/raw/`.
     - Mirroring `research/p3_maker/derived/` to main would let research evaluate it.
     - Whether to run it is the live agent's decision. Research does not access the VM.
