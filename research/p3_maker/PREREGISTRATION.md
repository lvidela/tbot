# Pre-registration — P3: virtual maker fills and post-fill markout on Kraken (public data, no orders)

**Date:** 2026-09-26 · **Author:** Research Agent (cloud) · **Branch:** `research/p3-virtual-maker`
**Source:** audit handoff P3 (`research/audits/NEXT_RESEARCH_HANDOFF.md`).
**Status:** committed before any outcome data is collected. A 110-second smoke test of the sampler
was run to check that the endpoints work, and its raw files were deleted unanalysed.

## C1 prior-exposure disclosure
- **Seen before this:**
  - A1: maker 0.400%/leg, adverse 5.4 bps/leg in calm markets, n = 2.
  - R5: calm fills don't transfer to volatile markets.
  - R11-CONFIRMED: GRASSUSD, where a passive seller was run over by +150 bps in 60 s.
  - AU4: spread elasticity 0.64 to σ; single snapshot.
  - AU7: `adverse_bps` is submit→fill drift, not markout.
  - X4: the high-vol rank effect.
- **Knowledge cutoff:** the Research Agent's is 2026-06. All data here is collected forward from
  2026-09-26, so it is post-cutoff and never seen.

## C3 code hashes (sha256, at pre-registration)

| file | sha256 |
|---|---|
| `sampler.py` | `c018187216386a91a783eb83c01d3d2ea150b504568f9a3f84445b69374659f3` |
| `analyze.py` | `49dbd5fbd71a6c313ee9133ac0111fe26fc5dad9d6022d0fd4eb02d5ba4c1842` |
| `pairs.json` | `c8dba8b2c71b597103953a20b06863ae389572512ca3495b81ab04915fb5aa48` |

Any later change is recorded as a diff with its reason in the finding.

## Questions (estimation first, then two tests)
When the live agent posts a post-only order at the touch:
1. What is the probability it fills within T ∈ {1, 5, 30} min?
2. What is the post-fill markout at +{1, 5, 30} min?

Both by volatility quintile and by the live system's regime label (`execution_stats`:
|1d return| / 30d pstdev ≥ 1.5 = *volatile*).

The results replace the 50% volatile-fill prior and the 5.4 bps calm adverse figure with
measurements.

## Design
- **Pairs (fixed now, `pairs.json`):** 3 pairs per σ30 quintile, drawn with seed 20260926 from
  the audit's 114-pair Kraken snapshot (≥ $250k 24h volume, excluding pegs), plus LINKUSD as the
  calm anchor.
  - Q1 TRX, XBT, XRP
  - Q2 ALGO, PENDLE, SKY
  - Q3 AKT, AVAX, DOT
  - Q4 ENA, PUMP, XCN
  - Q5 DASH, PEAQ, ZEC
- **Virtual orders:** at Poisson times (mean gap 10 min per pair, seed logged per run), a virtual
  post-only **bid at the best bid** and **ask at the best ask** from the public Ticker.
- **Fills:**
  - *strict*: a later public trade prints strictly through the price. This is the lower bound.
  - *touch*: a trade at the price by the aggressing side (a seller at the bid, a buyer at the
    ask). This is the upper bound.
  - *mid* estimate = strict + ½(touch − strict), because queue position is unknown.
- **Markout (bps, positive = good for the maker):** bid (mid − B)/B and ask (A − mid)/A at fill + h.
  - Mids come from the first ticker sample within 45 s after the target time.
  - The primary markout uses strict fills.
  - The control is the unconditional mid drift from t0 over the same h.
- **Cost implication, reported:** the effective maker cost per executed leg = 40 bps fee −
  markout(5 min). The expected cost of a maker attempt is also reported, including non-fill.

## Tests
Family of 2, Bonferroni α = 0.025 each. Run **once**, at the final report only; interim reports
are descriptive.

| id | test | registered direction |
|---|---|---|
| T1 | 5-min strict markout, volatile regime minus calm regime (bid and ask pooled), cluster-bootstrap by pair-hour | volatile more adverse (< 0) |
| T2 | 5-min strict markout, Q5 minus Q1 | Q5 more adverse (< 0) |

Both rows are appended to `research/TRIALS.jsonl` when run.

## Stopping and success (from the handoff)
- **Final report:** when the volatile-regime T = 5 min fill-probability 95% CI half-width is
  ≤ 15 pp **and** the volatile 5-min markout 95% CI half-width is ≤ 10 bps; **or** 14 calendar
  days after sampling starts, whichever comes first.
  - If the targets are not met by then: INCONCLUSIVE, with the achieved CIs and the MDE.
- **Interim:** each routine session resolves completed orders and commits `derived/` plus a
  descriptive summary. No test decisions are made before the final report.

## Known limitations (stated in advance)
- **Sparse sampling:** cloud sessions are ephemeral. The sampler runs in bursts of ≤ 3.5 h per
  routine session, and orders whose 61-minute window isn't covered are dropped (a random loss).
- **Volatile regime is rarer than calm,** so it may not reach its precision target in 14 days.
- **Queue position is unknown,** hence the strict/touch bounds.
- **Kraken's public trade side field** marks the aggressor.
- **Tick resolution is ~25–30 s.**
- **Gaps:** a failed Trades call can open a gap, which biases fills down. Errors are logged in
  `raw/log.jsonl`.
