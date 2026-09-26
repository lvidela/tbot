# Finding X8: LINK does not reverse after hourly up-spikes; selling into a spike and buying back costs ~1% per event

**Date:** 2026-09-26 · **Author:** Research Agent (cloud) · **Branch:** `research/x8-link-spike-reversal`
**Label: NEGATIVE.**
- This is a precise null, not a power problem: MDEs are 0.15–1.3% per event.
- It holds on two venues, in discovery, in the reused window and in the post-cutoff window.
- The live agent's proposal A1 (conditional reversal in the held asset) is answered for up-spikes.

## Question
After an unusually large 1-hour rise in LINK (≥ 2σ or ≥ 3σ of the trailing week's hourly
returns), does exiting to USD for 1, 4 or 24 hours and buying back beat holding LINK after the
0.92% two-leg cost?

## Hypothesis (pre-registered)
- `research/x8_spike/PREREGISTRATION.md` (`8d3f0e5`) was committed before any hourly data was
  downloaded, with C1 disclosure and the C3 hash of `evaluate.py` (unchanged since).
- Discovery was committed (`5bb67a6`) before the reused window was run.
- **Family:** 6 cells.
- **Evidence standard:** the program-level bar p < 1.87×10⁻⁴, plus the same sign on Coinbase.

## Data sources / period / timestamps
- **Binance archive:** spot LINKUSDT 1h, 67,371 hours.
- **Coinbase:** LINK-USD 1h, 63,520 hours.
- Both fetched 2026-09-26 ~04:50Z, public and unauthenticated.
- **Windows:**
  - discovery 2019-07 → 2023-12;
  - reused / pre-cutoff 2024-01 → 2026-06 (*not independent confirmation*, C2);
  - post-cutoff 2026-07 → 2026-09-24 (descriptive).

## Methodology
- Events are non-overlapping: after an event, the next can start only at T + h.
- σ excludes the event hour.
- Entry is at the event hour's close.
- **Net:** −r(T → T+h) − 0.92%.
- **Control:** the gross reversal minus the unconditional −r over random non-overlapping h-hour
  windows.
- **Reproduce:** `python3 research/x8_spike/evaluate.py --fetch`, then `--stage discovery` and
  `--stage reused`.
- **Tests:** `test_x8.py` (3/3) covers σ excluding the event hour, non-overlap, and planted
  reversal found with a quiet null.

## Results (Binance; Coinbase in brackets)
Discovery 2019-07 → 2023-12:

| cell | events/yr | mean net per event | t | MDE | gross reversal | gross − unconditional |
|---|---|---|---|---|---|---|
| k2 h1 | 236 | −1.02% [−1.00%] | −18.9 | 0.15% | −0.10% | −0.09% |
| **k2 h4 (primary)** | 196 | **−1.09%** [−1.03%] | −11.3 | 0.27% | −0.17% | −0.13% |
| k2 h24 | 118 | −1.52% [−1.59%] | −5.6 | 0.77% | −0.60% | −0.34% |
| k3 h1 | 71 | −0.97% [−0.92%] | −9.0 | 0.30% | −0.05% | −0.04% |
| k3 h4 | 65 | −1.11% [−1.08%] | −5.7 | 0.55% | −0.19% | −0.15% |
| k3 h24 | 50 | −1.72% [−1.35%] | −3.8 | 1.27% | −0.80% | −0.53% |

- **Reused window 2024-01 → 2026-06:** the same in every cell. Net −1.00% to −1.78% per event;
  primary −1.13% (t = −10.6); Coinbase agrees.
- **Post-cutoff 2026-07 → 2026-09 (descriptive):** primary net −0.94% (n = 51); gross −0.02%.
- **No one-sided p for "net > 0" is below 0.999 in any cell or window.**
- **Gross after a spike is ≈ 0 or slightly negative.** For a seller this means LINK tends to keep
  drifting up, i.e. mild *continuation*, not reversal. Exiting therefore pays the full cost plus a
  little.

## Comparison vs hold-LINK and hold-USD
- **vs hold-LINK:** every exit rule loses about its cost or more. At the primary cell's ~196
  events per year, the per-event losses sum to about −214% of account value per year
  (196 × −1.09%). Applied literally, the rule would lose most of the account.
- **vs hold-USD:** not applicable. This is a round trip for a LINK holder.

## Limitations
- Executing at the hourly close is, if anything, generous to the exit, because a maker sell into
  a spike can fill *before* the close at a better price. P3 will measure fills in fast markets. It
  cannot rescue a gross effect that is ≈ 0.
- Up-spikes only. Down-spike rebounds are not actionable for a fully invested holder and were not
  tested.

## Conclusion
- There is no short-horizon reversal after LINK hourly up-spikes. The gross move is zero or
  slightly continuing.
- A LINK → USD → LINK round trip after a spike reliably loses about the 0.92% cost or more.
- This also bears on discretionary profit-taking: **selling LINK into a sharp rise to buy back
  later has had negative expected value** at this account's costs.
- The trial ledger gains 6 rows, and K is now 268.

## What the Live Agent should independently validate
1. **Proposal A1 (conditional reversal in the held asset, up-spikes) is answered NEGATIVE.** Do
   not implement a spike-exit or profit-taking rule on LINK.
   - Reproduce the primary cell with the script above. Expected: net −1.0% to −1.1% per event on
     both venues.
2. **Down-spike rebound (buying after a crash) is not testable as a trade while fully in LINK.**
   If the account ever holds USD, X3 (daily) and T1 S4 are the relevant evidence, and both are
   inconclusive.
3. **Invalidation:** a positive gross reversal ≥ 1% per event on a fresh post-freeze window. The
   post-cutoff window shows −0.02% gross.
