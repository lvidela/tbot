# Finding: Research Agent response to the independent audit — verdicts, re-labelled results, and FROZEN-1

**Date:** 2026-09-25 · **Author:** Research Agent (cloud) · **Branch:** `research/audit-response`
**Label: REQUIRES VALIDATION** for FROZEN-1: it is frozen, and nothing is evaluable until its first
review (2026-12-26). This finding **re-labels** earlier results under the audit's program-level
standard. The original findings are not edited; this note supersedes their evidential weight.
**Input:** `research/audits/NEXT_RESEARCH_HANDOFF.md` and
`research/audits/external_agent_audit_2026-09-25.md` (commit `f77c85b`).

## 1. Verdicts on the audit's findings

| id | verdict | notes |
|---|---|---|
| AU1 holdout reuse / adaptive selection | **ACCEPT** | Correct and material. I chose X4 after reading X1's holdout. The BACKLOG says so: X4 "predicts the 2024–26 pattern ex ante". X4's pre-registration said "nothing was computed conditional on volatility", which was **inaccurate**: X1's S-c partial IC was volatility-controlled on that holdout. Recorded here as a correction. |
| AU1 correction to the audit | — | "All research data predates the model's knowledge cutoff (June 2026)" is not quite right. Bars from 2026-07-01 to 2026-09-24 (~12 weeks) post-date my cutoff. That is far too little to carry a confirmation alone, so the audit's conclusion stands. |
| AU2 simulation | **ACCEPT** | The per-study false-positive rate rests on the discovery stage. The holdout stage adds little once it has been seen. |
| AU3 confluence tail co-firing | **ACCEPT** (confirms D4) | No research change; it bears on the live detector. |
| AU4 cost scales sub-linearly with σ | **ACCEPT** | It sharpens X4: the obstacle for high-vol names is the sign of the predictable component, not cost. Single snapshot. |
| AU5 ~12 regime episodes | **ACCEPT** | No regime-switching rules will be fitted. |
| AU6 no version join | **ACCEPT** | The research side now hashes code in pre-registrations (C3) and in FROZEN-1. The live side is P6 (live agent). |
| AU7 adverse-selection metric | **ACCEPT** as plausible | P3 will measure post-fill markout on public data. |

## 2. Re-labelled results under the program-level bar (C2, C4)
- **Program count:** `research/TRIALS.jsonl` holds K = **262** formal tests, back-filled; the audit
  estimated ≈ 266. The Bonferroni bar is **p < 1.91×10⁻⁴**.
- Run `python3 research/trials.py` to reproduce.

| result | per-study label | program-level status (new) |
|---|---|---|
| X4 information (discovery IC p = 8.4e-5; partial IC p = 3.0e-5) | REQUIRES VALIDATION | **Clears the bar on discovery alone.** The 2024–26 holdout (t = −6.87) is a *reused / pre-cutoff holdout, not independent confirmation*. It remains prior-contaminated (LLM training data). Confirmation can only come from FROZEN-1 A2. |
| X4b Kraken replication (p = 6e-5) | POSITIVE | Clears numerically, but it is on the **same reused window**. Its value is venue robustness, not confirmation. |
| X6 listing age (primary partial IC, discovery p = 0.0099) | POSITIVE (information) | **Downgraded to INCONCLUSIVE.** The primary does not clear the program bar, and its holdout used the reused grid. The raw age IC does clear, but age is confounded with volatility (ρ ≈ −0.5), which is why it was not the primary. |
| X1 S-b discovery pass (p = 6.6e-4) | (did not replicate) | Does not clear the bar. NEGATIVE stands. |
| X1, X3, X5 NEGATIVE/INCONCLUSIVE; T1; R1–R13 | unchanged | Holdout reuse inflates false *positives*, so these nulls are unaffected. |

## 3. Verdicts on the proposed experiments

| id | verdict | action |
|---|---|---|
| **P2** trial ledger | **ACCEPT, done** | `research/TRIALS.jsonl` (append-only, 32 rows / 262 tests) and `research/trials.py` (`--check p`). |
| **C1–C6** controls | **ACCEPT, done** | Appended to `research/PROGRAM.md`. |
| **P1** FROZEN-1 | **ACCEPT, done (MODIFIED)** | Frozen in `research/frozen/FROZEN-1/`; see §4. The modifications are listed there. |
| **P3** virtual maker-fill and markout | **ACCEPT, next** | Pre-registration is next in the BACKLOG. **Limitation:** cloud sessions are ephemeral (a routine every 4 h), so sampling will be sparse bursts. A continuous public-data sampler would be better placed on the live VM, which is the live agent's decision. |
| P4 forward high-vol ledger | ACCEPT (live-agent owned) | Recommended to the live agent. The pre-registered decision statistic is the **arithmetic** mean; the median is reported beside it. |
| P5 regime labels + one test | ACCEPT, deferred | Waits for forward rows. The single test (X4 ordering in alt-led episodes) will be pre-registered then. |
| P6 decision snapshot | ACCEPT (live agent + researcher) | No research-side action. |
| P7 markout metric | ACCEPT (live agent) | No research-side action. |
| §5 "do not implement" list | **ACCEPT in full** | Including: do not cite X4's holdout or X4b as independent confirmation. |

**BACKLOG consequence:**
- X2 (historical OI, pre-cutoff) is demoted below P3.
- Historical studies continue only where their *discovery* stage could clear the program bar and
  inform a FROZEN entrant.

## 4. FROZEN-1 (audit P1), as frozen
- **Files:**
  - `research/frozen/FROZEN-1/spec.json`
  - `research/frozen/FROZEN-1/entrants.py`
  - `research/frozen/evaluate.py`
  - sha256 of all three, plus `freeze_ts`, in `FREEZE.json`, committed in the same push.
- **Evaluation data:** only outcome bars that open at or after the first UTC midnight after
  `freeze_ts`. All of them are post-cutoff.
- **Access:** every evaluator call is appended to `research/frozen/ACCESS.jsonl`. There is a
  budget of 8 queries, and none are allowed before the first review date. Reviews fall on
  2026-12-26, 2027-03-26, 2027-06-26, 2027-09-26, 2027-12-26 and 2028-03-26.

| entrant | statistic | null(s) |
|---|---|---|
| A1: S2 alone at h = 5 (the live agent's request) | timing − **static exposure** at the rule's own average weight | static exposure (built in); hold-LINK |
| A2: X4 low-vol-5 on 20 frozen Kraken pairs, 28-day | excess vs hold-LINK, net | random-5 at matched times; hold-LINK |
| B1: live tactical candidate stream, all | 3-day excess vs LINK minus 1.83%, clustered by day | random entry at matched times; hold-LINK |
| B2: B1 restricted to vol60 ≤ universe median (audit P1(a)) | as B1 | as B1 |

**Modifications from the audit's P1, with reasons:**
1. **Entrant (c), "tactical_v4 gate as-is", is replaced by B1 (the candidate stream,
   ungated).** The current gate passes nothing (p = 0.50 makes it vacuous), so a gated entrant
   would have n = 0 forever.
2. **Holm across entrants instead of max-stat permutation.** The entrants have different nulls, so
   a joint max-statistic distribution isn't well defined. Holm is conservative.
3. **B entrants depend on the live agent mirroring `data/counterfactual_ledger.json` to main.**
   The mirrored copy was last synced at 14:05Z with 31 rows. Without a mirror, B stays
   INSUFFICIENT_N.
4. **Guard enforcement of the access log is not implemented.** Guards belong to the researchers
   (handoff §7.2). The evaluator enforces the log and budget itself.

**Honest expectation (F4/F5):** INSUFFICIENT_N or CONTINUE at the first reviews. A 1% net edge
needs 200–790 days. The design's value is that a positive, if it ever comes, is uncontaminated.

## 5. Items that need the researchers
1. Handoff §7.1–7.4 as written: `model_id`/`cli_version` in the launcher, a guard rule for
   ACCESS.jsonl, the transcript retention policy, and whether the program-level α is binding.
2. **The objective (expected vs median USD).** X4/X6 show rank and median effects that do not
   reach the mean. Under the stated expected-USD objective they are worth ≈ 0.

## What the Live Agent should independently validate
1. **Stop treating X4's 2024–26 holdout or X4b as independent confirmation.** X4's information
   claim rests on its pre-cutoff discovery stage.
2. **X6 is now INCONCLUSIVE at the program level.** Do not cite it.
3. **To make B1/B2 evaluable, mirror `data/counterfactual_ledger.json` to main regularly.** No
   other change is needed. Please don't alter its schema without appending a note, because the
   frozen code reads `decision_ts_epoch` and `pair`.
4. **Consider P4 and P6–P7** (the live agent owns them).
