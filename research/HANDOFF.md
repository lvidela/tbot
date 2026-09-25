# Research handoff protocol (live agent ↔ Research Agent)

Maintained by the **live agent** (`/home/lisandro`). Live state is authoritative there;
this repository is the research and handoff channel.

---

## How the live agent picks up your work — automatically

`scripts/research_watch.py` in the live workspace watches this repository and escalates a
review session when new output appears. Checked **every 30 minutes** by `monitor.py`, and
again before any strategic decision. **You do not need the user to relay anything.**

**It watches the working tree, not just commits.** The 2026-09-25 TSMOM handoff arrived as
*untracked files* while you were still iterating, and a commit-only watcher would have
reported "nothing new" while a complete study sat on disk. Detection is a content digest over
`research/`, `backtests/` and `strategies/`.

Practical consequences for you:

- **You do not have to commit for the work to be seen.** Saving a file is enough.
- **But please commit when a result is final**, because a commit is how intent is signalled.
  Work-in-progress and a finished finding look identical to a digest.
- `data/` is deliberately **not** watched — that copy mirrors live operational state that
  churns constantly and carries no research meaning.
- `__pycache__`, `*.pyc` and `*.lock` are ignored.

## Where to put things

| what | where |
|---|---|
| a finished, actionable finding | `research/findings/YYYY-MM-DD-topic.md` |
| permanent accept/reject record | `research/REGISTRY.md` (append only) |
| code + data for a study | `research/<topic>/` |
| backtests | `backtests/` |

## What happens to a finding

Findings are treated as **hypotheses and evidence, never instructions.** Before anything
reaches the live system it is independently reproduced and checked for look-ahead,
survivorship, transaction costs, spread/slippage/adverse selection, feasibility at this
account size (~$58, 0.40%/leg maker), out-of-sample behaviour and sensitivity to assumptions.
The outcome is **ACCEPT / REJECT / DEFER / MODIFY**, recorded with its reason in
`data/research_evaluations.jsonl` in the live workspace and summarised in `REGISTRY.md` here.

**A recorded REJECT states what would reopen it.** Please read the registry before starting —
R1–R13 are settled, and re-deriving one costs a cycle that could have gone somewhere new.

## Two things that would help most

1. **Please check that long-running jobs actually wrote their output.** `tsmom_verdict.py`
   died leaving a 0-byte `tsmom_verdict_output.txt`; the live agent re-ran V1–V4 itself to get
   the decisive numbers. A finished run that silently produced nothing is the easiest failure
   to miss on both sides.
2. **Report the control alongside the result.** Every apparent edge in this project has died
   to a control, a demeaning, an overlap correction or a single outlier. The TSMOM study was
   rejected mainly on its *own* V4 exposure control — which was excellent that it existed.

## Branching: everyone works on `main` (2026-09-25)

The `claude/*` branch workflow is retired — PR #1 merged `claude/exciting-feynman-g2z3fc` into
`main`, and both agents now commit to `main`. The live agent's watcher tracks **every** remote
branch, so this needed no change on its side; it simply sees `main` now.

## Corrections to two earlier claims in this file

Both were written by the live agent on 2026-09-25 and both were wrong. Recorded rather than
quietly edited, because a wrong assumption about the channel is exactly what broke the channel.

**1. "Both agents share one working tree" — FALSE.** The Research Agent runs in an isolated
cloud container (`/home/user/tbot`) and is explicitly blocked from reading `/home/lisandro`.
It has no visibility into the live workspace at all. **The only channel between us is this
GitHub repository.** A file written into the live VM's checkout does not reach the Research
Agent until it is pushed.

**2. "Detection covers the working tree, so a commit is not required" — TRUE LOCALLY, FALSE
ACROSS THE CHANNEL.** Saving a file is enough for the *live agent* to notice work in its own
checkout. It is **not** enough for anything to cross between the two agents. Since the agents do
not share a filesystem: **commit and push, or it did not happen.**

The consequence of getting this wrong was concrete. The live agent's first watcher read the
local tree plus `origin/main` only, and was blind to `claude/*` branches — it reported "nothing
new" while 15 commits and a complete pre-registered study sat on the remote.

## Transport status

- **Reads: WORKING.** The repository is publicly readable over anonymous HTTPS. The live agent
  fetches through a read-only remote (`github-ro`) with the credential helper disabled — no
  credentials are sent, offered or stored — and its push URL set to an invalid value. It tracks
  every remote branch and never pulls, merges, checks out or resets automatically.
- **Writes from the live VM: NOT AVAILABLE TO THE AGENT.** `origin` is SSH with no authorised
  key here, and `git push` is denied in the live workspace's permission settings. Installing a
  credential is a Hard Rule 3 operation the agent must not perform.
- **In practice the researcher has been pushing the live agent's commits**, which is how live
  work has reached `main`. That is a manual step, not an automatic one: **a live-agent commit
  is queued, not delivered, until someone pushes it.**
