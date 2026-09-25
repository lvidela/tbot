# Pre-registration — X5: implied volatility (Deribit DVOL) and the variance risk premium as a state variable for crypto exposure

**Date:** 2026-09-26 · **Author:** Research Agent (cloud) · **Branch:** `research/x5-dvol`
**Status:** committed before any DVOL values are downloaded or related to returns. The only prior
contact with the data was a row-count probe of the endpoint (1,000 rows per page, paginated).

## Hypothesis and mechanism
**H5:** when the crypto variance risk premium (VRP) is high, subsequent crypto returns are higher.
- **Registered direction:** positive slope of forward return on VRP.
- **VRP definition:** BTC 30-day implied vol (Deribit DVOL) minus BTC trailing 30-day realised vol.

**Mechanism:**
- Option sellers demand a premium for bearing crash risk.
- A high VRP marks fear, or hedging demand in excess of realised risk.
- In equities, a high VRP predicts higher index returns over the following months.

**Why it is new here:**
- T1 used price, trend, crash and funding states.
- F2's regime evidence used realised volatility (S5).
- No study here has used **option-implied** information.

## Data (fixed now)
- **Implied vol:** Deribit public `get_volatility_index_data` for BTC and ETH, daily (resolution
  1D), paginated back to the earliest available date. Stored with provenance.
- **Prices:** Coinbase BTC-USD and LINK-USD daily (`research/data/raw`, already downloaded).
- **EW universe:** from X1's panel (Binance, survivorship-free).
- **Alignment:** DVOL daily points are timestamped at the UTC day open. The value used at
  decision time t is the **last DVOL point with timestamp ≤ t − 1 day**. This is deliberately
  lagged one day so that no intraday information from day t−1 leaks forward.

## Definitions
- **VRP_t** = DVOL_BTC(t−1d)/100 − RV30_BTC(t), where RV30 is the sd of the last 30 daily log
  returns ending at close(t), × √365.
- **z-score:** VRP is z-scored on an **expanding** window of past values only, with ≥ 180 days
  required.
- **Decision times:** every 28 days from the first date with a valid z. All 4 weekly phase offsets
  are run; phase 0 is primary.
- **Forward return:** the log return close(t) → close(t+28d).

## Tests
Family of 4, Bonferroni α = 0.0125, two-sided, in discovery.

| id | test | direction |
|---|---|---|
| **P** | OLS slope of LINK fwd 28d log return on z(VRP), non-overlapping windows | > 0 |
| S1 | same for BTC fwd 28d | > 0 |
| S2 | same for the EW-universe fwd 28d simple return | > 0 |
| S3 | slope of LINK fwd 28d on z(DVOL_BTC level) instead of VRP | > 0 |

- **Sample split:** discovery covers t from the first valid date to 2023-12-31. The holdout covers
  2024-01-01 → the last t with a complete 28-day forward window (≤ 2026-09-24). The holdout runs
  once, after discovery is committed.
- **H5 is SUPPORTED** if P passes Bonferroni in discovery and has one-sided p < 0.05 in the
  holdout.
- **Otherwise:** INCONCLUSIVE, or NEGATIVE if P has the wrong sign in discovery.
- **Power, stated now:**
  - There will be roughly 30–35 windows per period.
  - LINK's 28-day return sd is ~25%, so the slope SE is ~4–5% per 1 SD of VRP, and the MDE is
    ~12–13% per 28 days per SD.
  - Only an enormous effect is detectable. A null will be INCONCLUSIVE, not evidence of absence.
  - The study is run anyway because it is cheap and the dataset is new. The economic test below
    is what decides relevance.

## Economic test (always reported)
**Rule:** hold LINK when z(VRP) ≥ 0, else hold USD, re-decided every 28 days.
- **Costs:** 0.46% per leg on each switch.

**Compared with:**
- hold-LINK;
- hold-USD;
- **static exposure** at the rule's realised average LINK weight, rebalanced every 28 days with
  costs (the live agent's S2 request);
- the difference `timing − static`, which is reported as the test of skill.

**Actionable only if:**
- H5 is supported;
- `timing − static` > 0 in the holdout with a 90% block-bootstrap CI excluding 0;
- `timing − hold-LINK` > 0 in point estimate.

## Known risks
- **Few windows,** and DVOL history begins only in ~2021.
- **One market-wide state** is being tested, so there are effectively few independent regimes.
- **ETH DVOL** is fetched for a descriptive check only, not tested.
