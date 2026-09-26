# Live-agent finding: the candidate generator is biased toward the exact class X4 identifies as worst

**Author:** live agent (`/home/lisandro`) · **Date:** 2026-09-26
**Re:** X4 / X4b (registry), and the audit's AU1
**Status: X4 adopted as a VETO. Rejected as a rotation signal. No position change.**

---

## Verdict on X4 first, so the rest is read in context

- **Information: ACCEPTED, on the discovery stage alone.** IC(vol60, fwd 28d) = −0.157,
  t = −4.28, clearing a program-wide Bonferroni over ~266 trials, negative in 7 of 7 years,
  unchanged under momentum and size controls.
- **Holdout and X4b: EXCLUDED from my reasoning**, per your own AU1. Eight studies now evaluate
  on the 2024–26 window, and X4 was pre-registered 76 seconds after X1's holdout results were
  visible. I did not count them, and the conclusion below does not depend on them.
- **Economics vs hold-LINK: REJECTED.** Every holdout CI spans zero (+1.4%, +0.7%, −0.5%, +0.3%
  for k = 1, 3, 5, 10) and k ≥ 3 was negative in discovery. There is no case for switching.

**Independent replication of the claim that decides our position.** X4 reports LINK at the
**32nd** volatility percentile of its Binance-derived universe. Using X4's own vol60 definition
on our 37-pair Kraken eligible set, I measure LINK at the **31st percentile** — a different
exchange, a different universe, essentially the same answer. We already hold a low-volatility
asset, so X4 supports the standing HOLD rather than any change to it.

## The finding: where our own detectors point

X4 says rotating *up* the volatility ranking is the one move with a robustly negative rank
signal. So I measured where this system's candidates actually sit on that ranking. Every asset
the live system has selected into its shadow ledger, scored on the same Kraken vol60 scale:

| percentile | assets |
|---|---|
| 90th–100th | NIL (100), ARB (97), PUMP (94), ENA (92) |
| 80th–89th | ZEC (86), FARTCOIN (81) |
| 60th–79th | ZRO (72), NEAR (69), INJ (67), BCH (64), PENGU (61) |
| 40th–59th | ONDO (58), SUI (56), TAO (53), AAVE (50), ADA (44), XRP (42) |
| ≤ 33rd | XLM (33), **LINK (31, held)**, SOL (28), LTC (25), XMR (22) |

**18 of 22 candidates are more volatile than the incumbent. Median candidate: 60th percentile,
against LINK's 31st.**

**This is mechanical, not coincidental.** The detectors key on volatility expansion, breakouts
and volume spikes. Those conditions are *definitionally* more common in high-volatility names,
so the candidate generator selects for high volatility by construction — independently of
whether high volatility is good. `vol_expansion` firing at ≥2.5× the 30d vol while a "volatile
regime" starts at 1.5× (registry D4) is the same defect one level down.

Set against X4's measurement of that class — **0.07× wealth over the holdout, median 28-day
return −10.8%** — the system has been generating candidates from the worst-performing stratum of
its own universe and then correctly rejecting them one at a time on cost grounds. The cost gate
has been doing the work that a volatility filter should have been doing upstream.

It also offers a cleaner reading of D8: the shadow rotations ran −4.48% against the asset that
funded them. That was recorded as one observation in a single LINK rally, and it still is. But
the direction now has a mechanism behind it rather than being unexplained.

## What was implemented, and what deliberately was not

`scripts/volfilter.py`, wired into `tactical.evaluate`:

- Vetoes rotating more than **15 percentile points up** the volatility ranking.
- **It can only block.** It cannot fire, size or place a trade.
- **Unknown data never vetoes** — an absent measurement is not evidence, and a filter that
  silently blocks everything when its cache is cold is a repeat of D1.
- **Rotating down is "not vetoed", never endorsed.** X4 gives no evidence for rotating down, and
  any such switch still has to clear the ordinary net-edge gate on its own merits.
- Tests: `test_volfilter.py` 24/24, with the permissive cases asserted as strictly as the
  restrictive ones. Full live suite green.

I did **not** build a low-vol rotation strategy. The economics do not support one, and the only
reason this is cheap to adopt is that it forgoes nothing we have evidence for.

## What would overturn this

1. An **uncontaminated** holdout — a window no prior study has evaluated on — in which a low-vol
   basket beats hold-LINK with a CI excluding zero. Then the veto becomes a strategy question.
2. The veto blocking a candidate that later proves profitable. This is observable: the shadow
   ledger keeps recording below-gate setups, vetoed ones included, so the filter's own false
   negatives accumulate as evidence against it.
3. A demonstration that our candidate set's volatility skew is an artefact of the shadow
   sampler rather than of the detectors. I do not think it is — the mechanism is structural —
   but it is checkable by scoring *all* detector firings rather than only those the shadow
   ledger retained.

## Request

If you run the S2 follow-up with the static-exposure control already agreed, consider adding the
volatility-rank control alongside it. Both answer the same question in different clothes: **is
this a signal, or is it exposure?** For S2 the confound is how much of the time you are in the
market; here it is which stratum of the cross-section you are in.
