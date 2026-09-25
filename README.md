# tbot — autonomous cryptocurrency trading agent (research experiment)

Source and research state of a university experiment in which an AI agent is given real
capital, direct access to a Kraken Spot account, broad strategic autonomy, and no routine
human guidance. The experiment values honest record-keeping and adaptation at least as much
as the financial result.

**This repository is a published snapshot. The live system runs on a separate VM, and the
credentials exist only there.** Nothing here can place an order on its own.

---

## The objective, and the benchmark

Maximise the final USD value of the account by **2026-10-15**.

The account started in **LINK**, not cash, so its USD value moves with LINK whether or not the
agent does anything. Performance is therefore measured against a passive benchmark: *hold the
starting quantity to the end date.*

| | |
|---|---|
| Benchmark basis | **4.1944857200 LINK + 0.0000365 USDT = $51.3087** at 2026-09-24T12:36:22Z |
| Benchmark rule | hold those exact quantities to 2026-10-15; **never re-baselined** |
| Stored in | `data/benchmark.json` (immutable on the VM via `chattr +i`) |

Beating it is a meaningful result. So is failing to, provided the record says so plainly.

## Current state (as of the last commit)

Holdings **4.19657014 LINK**, `total_usd` **$58.94** against a **$58.90** benchmark. The +$0.04
of excess is a small LINK gain from one exploratory round trip, already recorded as luck rather
than skill. **2 lifetime trades.** The standing decision is HOLD, and the reason is not caution
— it is that no measured directional edge has survived scrutiny.

Read `STATE.md` for the live picture and `logs/journal.md` for the reasoning, in the agent's own
words, session by session.

---

## How the system is built

```
Kraken market data
      |
scripts/monitor.py ......... deterministic, always-on, NEVER places an order
      |  signal detected
      v
classify_signal() .......... state-transition dedup (below)
      |  carries new information
      v
Claude session ............. investigates, decides, records, exits
      |  explicit decision
      v
scripts/execute.py ......... the ONLY order path; full pre/post-flight
      |
Kraken reconciliation
```

Two invariants hold the whole design together: **the monitor never trades**, and **every order
goes through `execute.py` behind an explicit decision**. A monitor bug or a confused session
therefore cannot produce uncontrolled trading.

### Signal deduplication

A persistent condition used to re-escalate on elapsed time alone, which burned whole sessions
re-deriving answers that already existed. Signals now resolve to one of seven transitions:

| escalates | suppresses (always logged) |
|---|---|
| `NEW` — unseen asset, or new event type | `UNCHANGED` — materially identical |
| `STRENGTHENED` — ≥40% over the last **escalated** magnitude | `WEAKENED` — same sign, materially weaker |
| `REVERSED` — sign flip | `ALREADY_EVALUATED` — a session answered at this magnitude |
| `RECURRED` — ended, stayed clear ≥60 min, returned | |

There is no global cooldown and no daily cap. Assets and event types are fully independent.

---

## Layout

| path | what it is |
|---|---|
| `CLAUDE.md` | the operating prompt — objective, hard rules, regime directives. **Researcher-owned** |
| `STATE.md` | current holdings, architecture, gate status, next-session checklist |
| `STRATEGY.md` | active strategy, hypotheses, entry/exit rules, known weaknesses |
| `RECONNAISSANCE.md` | first-session survey of VM, repo and Kraken API |
| `scripts/` | monitor, execution, edge model, ledgers, safety guards, tests |
| `research/REGISTRY.md` | **the most important file here** — every rejected hypothesis and defect |
| `research/` | Q1–Q4 studies, micro-arbitrage findings, methodology notes |
| `backtests/` | the studies themselves, runnable against a cached dataset |
| `data/` | benchmark, shadow ledger, counterfactual ledger, experiment metadata |
| `logs/activity.jsonl` | append-only audit log — every event, order, error and decision |
| `logs/journal.md` | candid per-session narrative, including mistakes |

## Safety model

Immutable constraints, in force regardless of strategy:

- **Spot only.** No margin, leverage, futures, shorts, options, borrowing or staking.
- **No withdrawals, transfers or deposits** — the funding endpoints are never called, *not even
  to test access*.
- **`STOP` kill switch.** A file named `STOP` in the repo root halts every order path.
- **Append-only records.** Losses, bugs and failed strategies are logged as they happened.

Enforced in three independent layers: `scripts/kraken.py` refuses funding endpoints before
signing; `scripts/execute.py` checks `STOP` before every order and requires an exchange-side
protective exit; `scripts/guard_bash.py` blocks the same classes at the shell layer, matching
the command string so it still applies to `python3 -c` and heredocs.

## Tests

```bash
for t in tactical aggressive counterfactual shadow dedup permissions; do
    python3 scripts/test_$t.py
done
```

**166 assertions**, covering the trade gate, kill-switch behaviour, funding-endpoint refusal,
signal deduplication in both directions, and the permission configuration.

---

## If you are an agent working on this repository

Four things worth knowing before you propose anything:

**1. Read `research/REGISTRY.md` first.** Eleven hypotheses (R1–R11) have been tested and
rejected, and eight defects (D1–D8) were found in the agent's *own* work. Reviving a rejected
idea requires stating what new evidence justifies it. Several look attractive and are not.

**2. Nearly every apparent edge here died of the same three causes.** Overlapping forward
windows, treating correlated assets as independent observations, and measuring absolute return
instead of return relative to the asset that funds the trade. A study reporting `h > 1` must
report a non-overlapping or phase-averaged `t` alongside the clustered one.

**3. Cost dominates at this account size.** Measured: **0.831%/leg taker, 0.400%/leg maker**.
A one-way re-allocation is 2 legs. Gross-return results are not evidence — report everything net
of fees, spread, slippage and realistic fill assumptions.

**4. The binding constraint is not cost — it is `p = 0.50`.** Halving execution cost removed the
cost constraint and did not create an edge. A permutation test on signal combinations returned
family-wise **p = 0.971**: randomly selecting assets typically produced a better-looking best
result than the real signals did. The open question is whether `p` is genuinely 0.50, and the
shadow and counterfactual ledgers are accumulating the only forward, uncontaminated evidence
that can answer it.

Null results carry their minimum detectable effect. "I cannot detect an edge below 3–7%" is the
defensible claim; "there is no edge" is not.

## Running it

Requires Python 3.12 (standard library only — no third-party dependencies) and a Kraken Spot
API key with **no** withdrawal permission. Copy `.env.example` to `.env` and fill it in; see
`systemd/trading-monitor.service` for the supervised monitor.

Live trading is gated by `data/live_trading.json` and falls back to simulation whenever `STOP`
exists.
