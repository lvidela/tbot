# MICRO-ARBITRAGE research track — findings

**Status: all mechanisms REJECTED. Cause is structural, not circumstantial.**
Separate track; the existing strategy is untouched.

---

## The four-level taxonomy, measured

Applied to 702 real triangles priced from a single simultaneous snapshot, using
**executable prices only** (buy pays the ask, sell hits the bid — never mid):

| level | definition | count |
|---|---|---|
| 1. Theoretical arbitrage | gross > 0 at quoted prices | **21** |
| 2. Executable arbitrage | + clip-sized depth present on all three legs | **9** |
| 3. Executable after fees | + gross > 1.20% (3 maker legs) | **0** |
| 4. Repeatable positive-EV | + demonstrated over time | **0** |

**12 of 21 theoretical opportunities evaporate on depth alone, before fees are considered.**

### The illustrative case: BTT/EUR

The time-series sampler repeatedly flagged BTT/ZEUR at **+0.49% to +0.56% gross** — the
largest dislocation seen. It is not tradeable:

- **BTTUSD top-of-book bid holds 1 BTT ≈ $0.0000004.** The minimum order is 17,000,000 BTT
  ($6.41). You cannot sell a $6.41 minimum into a $0.0000004 bid.
- BTTEUR quotes a **607 bps** spread, which is what the "dislocation" actually is.
- One tick is 2.7–3.1 bps of price at these levels, so the implied cross-rate is heavily
  quantised.

This is exactly the theoretical/executable distinction: **the price exists, the size does not.**

---

## Mechanism-by-mechanism economics

Fee hurdles at our measured tier (maker 40 bps/leg, taker 80 bps/leg):

| mechanism | best observed edge | legs | max viable fee/leg | we pay | short by |
|---|---|---|---|---|---|
| Triangular arb (snapshot) | 26.8 bps | 3 | 8.9 bps | 40 bps | **4.5×** |
| Triangular arb (time series) | 56.2 bps | 3 | 18.7 bps | 40 bps | **2.1×** |
| Stablecoin dislocation | 21.5 bps | 2 | 10.8 bps | 40 bps | **3.7×** |
| Spread capture (eligible median) | 4.9 bps | 2 | 2.5 bps | 40 bps | **16.3×** |
| Spread capture (eligible max) | 23.9 bps | 2 | 11.9 bps | 40 bps | **3.3×** |
| Reversion after passive fill | −5.4 bps | 2 | — | 40 bps | **sign is wrong** |

### Spread capture — the most structurally durable rejection

**152 of 618 online USD pairs have spreads exceeding the 80 bps hurdle. Zero of them are
liquid** (>$1M volume and >500 trades/day). Among the 37 pairs liquid enough to actually fill,
the median spread is **4.9 bps** and the maximum is **23.9 bps**.

This is not a coincidence to be waited out — it is the equilibrium. **A spread is wide precisely
because market-making there is unprofitable**: no flow to earn from, and whoever does trade
against you is informed. The liquidity/spread trade-off is a wall, not a gap.

### Stablecoin dislocations

721 daily bars: USDT |close − 1.00| has median **3.1 bps**, p95 13.8 bps, **max 21.5 bps** —
never within a factor of 3 of the 80 bps hurdle. USDC max 5.0 bps.

Intraday *ranges* do exceed the hurdle on 21/721 (USDT) and 15/721 (USDC) days, but a range is
not a capture: realising it requires buying the low and selling the high, which is precisely the
optimistic-fill assumption this track is required to reject. And those days are depeg scares —
exactly when a resting bid is adversely selected. Frequency ≈ 2–3% of days ⇒ under 1 expected
event in the experiment's remaining horizon. Not repeatable.

### Reversion after passive fills

Measured on real fills (n=2): adverse selection ran **+5.4 bps against us**. The mechanism needs
+80 bps *in our favour*. Both the sign and the magnitude are wrong.

---

## Root cause — why the whole class is excluded

Venues where these strategies work pay makers a **rebate** (negative fee) or charge 0–2 bps.
**We pay 40 bps.** Microstructure edges live in the 1–10 bps band, so the entire strategy class
sits *below our fee floor*.

Kraken's tier ladder runs 40 bps → 0 bps maker, but the qualifying volume is $10M/30 days
against our ~$75. **Unreachable by five orders of magnitude.**

This makes the conclusion durable: it is not "no opportunity today", and no amount of searching,
waiting or cleverness changes it. Only a different fee tier would.

---

## What was built, and why

`scripts/micro_arb.py` — a **detection-only** watcher wired into the monitor at a 30-minute
cadence. It re-tests all three hurdles (liquid-pair spread > 80 bps, stablecoin deviation
> 80 bps, depth-checked triangular > 120 bps) and logs a `MICRO-ARB HURDLE CLEARED` event if any
is ever met. It **never places an order**.

The point is that this negative result depends on inputs that *could* change — a genuine depeg, a
liquidity event, a fee-tier change. The watcher keeps the finding live evidence rather than
letting it decay into an unexamined assumption. A hit requires manual validation (re-price at the
decision instant, verify depth, confirm repeatability) before any execution: **one
profitable-looking observation is not evidence of positive expectancy.**

## Shadow mode

Not warranted. Shadow mode is for mechanisms that look promising and need forward validation;
nothing here cleared its hurdle even theoretically-after-fees. Building a shadow ledger for a
mechanism short by 2.1–16.3× would manufacture activity, not evidence. The watcher above is the
proportionate response.

## Registry

Recorded as **R11** in `research/REGISTRY.md`. Do not revive any of these mechanisms without a
material change in the fee tier, and say explicitly which one changed.
