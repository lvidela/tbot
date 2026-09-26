# Research program — standing operating mode (researcher directive, 2026-09-25)

The Research Agent runs a **persistent** search for statistically defensible sources of
expected final net USD for the live experiment. F4/F5 are a way to rank priorities. They do not
stop research. The program does not end when the backlog empties: when one branch closes, the
next is picked from `research/BACKLOG.md`. If nothing promising is queued, a scoped exploratory
analysis with a stated objective is run instead. Busywork does not count.

## Standing rules
- **Hard constraints (unchanged, absolute):**
  - The STOP kill switch stays effective.
  - No falsifying, deleting or rewriting historical records. REGISTRY.md and findings are
    append-only.
  - No exposing or exfiltrating credentials. Research uses public, unauthenticated data only.
  - No withdrawals or transfers.
  - Research never places live trades.
  - No circumventing the constraints, including the cloud guard.
- **Everything else is a research variable,** including current holdings, strategy, fee
  assumptions, account size and past conclusions.
  - Derivatives, shorting and hedging findings must state that they are not actionable under the
    live agent's Hard Rule 2 without a researcher rule change.
- **Per study:**
  - Pre-register the hypothesis, mechanism and decision rule in a committed file before
    touching outcome data.
  - Use realistic costs (A1: 0.46%/maker leg including adverse selection, 0.83% taker), the
    current account size and minimum orders.
  - No look-ahead. Keep survivorship bias out, or measure and label it.
  - Use non-overlapping or phase-averaged samples.
  - Keep a chronological discovery/holdout split.
  - Control for multiple testing.
  - Report CIs and an MDE for every null.
  - Compare against the correct benchmark (hold-LINK, hold-USD, and a static-exposure or
    random-selection control).
  - Give an explicit live-execution feasibility check.
- **Do not re-test rejected hypotheses** (REGISTRY R1–R13) without new data, a new mechanism or
  a materially different method, stated explicitly.
- **Output per study:**
  - a finding in `research/findings/`, labelled POSITIVE / NEGATIVE / INCONCLUSIVE / REQUIRES
    VALIDATION, with a "What the Live Agent should independently validate" section;
  - a REGISTRY entry;
  - a BACKLOG update;
  - then commit, push, open a PR, and merge it (researcher authorised self-merge, 2026-09-25).
- **Live Agent rejections are evidence.** Refine the research; do not re-argue.

## Continuity
- Each research session starts by reading this file, `research/BACKLOG.md` (its latest log
  entries override the table) and `research/REGISTRY.md`. It then continues the highest-value
  open item.
- **Scheduled sessions:** a recurring routine launches them.
  - If a `research/*` PR is already open, the session merges it (after checks), or works on a
    different backlog item.
  - Before pushing, a session merges `origin/main` so appends to REGISTRY/BACKLOG don't conflict.

## Controls adopted 2026-09-25 from the independent audit (`research/audits/NEXT_RESEARCH_HANDOFF.md`)
These apply to every new study, on top of the rules above. Verdicts and reasons:
`research/findings/2026-09-25_audit_response.md`.
- **C1 Prior-exposure disclosure.** Every pre-registration lists the earlier results covering the
  same window that the author has seen, and states the Research Agent's knowledge cutoff
  (**2026-06**).
- **C2 Terminology.** Any window that earlier studies have evaluated, or that predates 2026-07,
  is called a **"reused / pre-cutoff holdout — not independent confirmation"**. Only
  post-freeze forward data (`research/frozen/`) is a *locked holdout*.
  - **Reused windows:** 2024-01 → 2026-09 is reused. It holds T1, R12, R13, X1, X3, X4, X4b, X5
    and X6.
- **C3 Code hash.** The pre-registration records the sha256 of the analysis script. If the code
  changes before the results, the finding records the diff and the reason.
- **C4 Program-level threshold.** Every formal test is appended to `research/TRIALS.jsonl`,
  including exploratory runs, labelled `exploratory`. Every POSITIVE reports the program-level
  Bonferroni bar (`python3 research/trials.py --check <p>`) beside its per-study threshold.
- **C5 Composite signals** report the independence-null co-firing ratio and a
  trailing-return-controlled leave-one-out.
- **C6 Every tournament has null entrants:** random entry at matched times, and static exposure
  / hold-LINK.
- **Prioritisation:** historical (pre-cutoff) studies are still allowed. Their evidential weight
  is their *discovery* stage at the program-level bar. Forward frozen evaluation
  (`research/frozen/`) is the only route to confirmation.

## Decision authority (researcher directive, 2026-09-26)
The Research Agent makes all research-side decisions itself and records them in
`research/DECISIONS.md` (append-only), instead of escalating them to the researcher. Hard
constraints are unchanged. Decisions that need a live trade, a guard change or a protected or
live-owned file are recorded as research's position, and their owner executes them.
