# FROZEN-2: forward high-vol vs low-vol arithmetic-mean ledger

- **Spec:** `spec.json`. Audit open question 2: is the arithmetic mean excess of the top
  volatility quintile over LINK positive after 1.83%?
- **Frozen files** (hashes in `FREEZE.json`): `spec.json`, `entrants.py`, `evaluate2.py` and
  `universe.json`. Any edit voids the experiment.
- **`archive.py` is plumbing, not frozen.** Run it every research session to append Kraken public
  closes to `closes.jsonl`, which is append-only and committed. This keeps delisted pairs' last
  prices, so the ledger is survivorship-free.
- **Evaluate only on review dates:**
  `python3 research/frozen/FROZEN-2/evaluate2.py --reason "<review>"`. Every call is logged to
  `research/frozen/ACCESS.jsonl`, with a budget of 8 queries.
- **Tests:** `test_frozen2.py` (synthetic data; no network, no access log).
