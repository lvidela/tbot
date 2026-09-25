# research/frozen — locked forward holdouts

Each experiment directory holds:
- `spec.json`: the hypothesis, statistic, nulls, decision rule, review dates and query budget.
- `entrants.py`: the signal code.
- `FREEZE.json`: sha256 of `spec.json`, `entrants.py` and `../evaluate.py`, plus `freeze_ts`.

**Rules:**
- **Never edit** a frozen spec or its code. `evaluate.py` refuses to run on a hash mismatch, and
  the experiment is then void.
- To change anything, create a new experiment id.
- **Evaluate only** with `python3 research/frozen/evaluate.py <ID> --reason "<review>"`. The
  script:
  - appends every call to `ACCESS.jsonl` (append-only; commit it with the review's finding);
  - refuses before the first review date and after the budget is spent;
  - prints only the pre-registered statistics.
- **Only outcome bars after `freeze_ts` are used.** They are all after the Research Agent's
  knowledge cutoff (2026-06). This is the program's only *locked* holdout (PROGRAM.md, C2).

Tests: `python3 research/frozen/test_frozen.py`, on synthetic data. It writes no access log.
