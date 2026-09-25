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

## ⚠ GitHub transport is DOWN — this repo is local-only right now

`origin` is `git@github.com:lvidela/tbot.git` (SSH). **Authentication fails: `Permission
denied (publickey)`.** `origin/main` is stuck at `7114f9e`, several commits behind local.

This does **not** break the loop, because both agents run on this same machine and share this
working tree, so handoff happens through the local repository. It does mean:

- **Nothing either agent commits is reaching GitHub.** There is no off-machine backup.
- The live agent will **not** attempt to fix this. Installing a deploy key or credential is a
  credential operation and an explicit researcher decision; `git push` is also denied in the
  live workspace's permission settings. `research_watch.fetch()` retries harmlessly every
  cycle and records the outcome, so **the moment access is restored it starts working with no
  code change.**

### Coordination hazard, please read

We share one working tree. On 2026-09-25 the live agent committed `research/tsmom/` while you
may still have been iterating on it. That was appropriate — the study was complete and being
adopted or rejected — but the general case is a real risk: **either agent can commit the
other's half-finished work, and `git checkout`/`reset`/`pull` could destroy uncommitted work.**

The live agent's watcher is therefore strictly read-only against this repo: it runs `git fetch`
and `git log` only, **never** pull, merge, checkout or reset.
