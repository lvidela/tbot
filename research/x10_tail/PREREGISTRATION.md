# Pre-registration — X10: independent out-of-sample check of the live agent's ARMED LINK tail-reversal bet

**Date:** 2026-09-26 · **Author:** Research Agent (cloud)
**Subject:** `research/findings/2026-09-26_prereg_link_tail_reversal.md` (live agent, `6b686f2`).
- **Its rule:** a daily move ≥ 2.5σ (σ from the trailing 720 days); trade against it; exit at +1
  day; cost 0.92%.
- **Its evidence:** 17 events in 2024-10 → 2026-09, net +1.94%, median +1.41%, t = 2.08. It
  fails a 9-cell Bonferroni.
- **Why check it now:** the exploration capital means this bet can actually be funded.

## C1 disclosure
- **Seen:** the live agent's result (its window only); X8 (hourly up-spikes: no reversal); X3
  (daily market capitulation: inconclusive); T1 S4 (LINK crash state: inconclusive).
- **Not seen:** I have not computed this rule on any data.
- **Knowledge cutoff:** 2026-06. The test data (pre-2024-10) is pre-cutoff, but it is
  **disjoint from the live agent's sample**.

## C3
`evaluate.py` sha256 `ff7c158cafa8e678ef91cb62d66c4c2118da3e48a312f6363d4aebe1bb7aa31a`.

## Test
- **Rule:** copied exactly, including non-overlapping triggers.
- **Sample:** every trigger whose bar and exit fall before 2024-10-06, the start of the live
  agent's sample.
  - Primary venue: Binance LINKUSDT daily (from 2019-01; the 720-day σ warm-up starts triggers
    around 2021-01).
  - Cross-check: Coinbase LINK-USD.
- **Primary:** h = 1 (the armed cell). One test: mean net > 0, one-sided α = 0.05. This is a
  replication of a single pre-specified cell, so there is no search.
- **Reported:**
  - h = 2 and 3;
  - a 365-day σ sensitivity (declared now), which uses more history;
  - median, hit rate, MDE.
- **Decision relevance:**
  - **Replicated** (p < 0.05 and median > 0): the armed bet has independent support. It still
    needs a forward sample to confirm.
  - **Mean ≤ 0 or median ≤ 0:** evidence against arming it with capital. The live agent decides.
- **Expected power:** n is probably only 5–20. An INCONCLUSIVE result is likely, and it will be
  reported with its MDE.
