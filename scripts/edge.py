"""Net expected-edge calculator. Every trade decision must pass through this.

Frames the question as EXPECTED NET RETURN AFTER ALL COSTS, not "is this signal
statistically perfect". Aggressive but economically rational: the bar is that the
expected move must beat the full round-trip cost by a modest margin, not by a large one.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken
import execution_stats

# NOTE ON NAMING (Q3 flagged a possible double-book; verified there is none):
# TAKER/MAKER here are the pure Kraken FEE per leg. The spread term is added separately in
# costs(). Registry A1's "0.831%/leg taker" is the ALL-IN total (0.80% fee + half spread),
# not the fee. Do not set TAKER = 0.00831 or the spread will genuinely be double-counted.
TAKER = 0.0080                # fee only, measured
MAKER = 0.0040                # measured -- HALF the taker fee
EDGE_MARGIN = 1.5             # expected net gain must be >= 1.5x total cost
MIN_ABS_EDGE_PCT = 0.5        # and at least 0.5% net, so tiny "wins" aren't chased


def costs(pair, notional_usd, sides=2, maker=False):
    """Full expected cost in % of notional: fees + spread + slippage + impact.

    maker=True prices a limit-order round trip: HALF the fee, and no spread crossing
    (we post at the touch rather than taking it). The trade-off is fill risk, which the
    caller must weigh -- an unfilled limit order means missing the move entirely."""
    t = kraken.public("Ticker", pair=pair)
    k = list(t)[0]
    bid, ask = float(t[k]["b"][0]), float(t[k]["a"][0])
    spread_pct = (ask - bid) / bid * 100

    d = kraken.public("Depth", pair=pair, count=100)
    dk = list(d)[0]
    bids = [(float(p), float(v)) for p, v, *_ in d[dk]["bids"]]
    asks = [(float(p), float(v)) for p, v, *_ in d[dk]["asks"]]
    mid = (bids[0][0] + asks[0][0]) / 2
    near = sum(p * v for p, v in bids if p >= mid * 0.995) + sum(p * v for p, v in asks if p <= mid * 1.005)
    impact_pct = (notional_usd / max(near, 1)) * 100 if near else 5.0

    fee_pct = (MAKER if maker else TAKER) * 100 * sides
    # takers cross the spread; makers post at the touch and pay none of it
    slip_pct = 0.0 if maker else (spread_pct / 2) * sides
    # MEASURED adverse selection: a resting order gets filled when the market moves
    # against it. Zero for takers (they choose the moment). Real and non-zero for makers.
    adverse_pct = 0.0
    if maker:
        st = execution_stats.summary(verbose=False)
        obs = [v["mean_adverse_bps"] for v in st.values() if v.get("mean_adverse_bps") is not None]
        adverse_pct = (sum(obs)/len(obs)/100.0) * sides if obs else 0.05 * sides
    slip_pct += adverse_pct
    total = fee_pct + slip_pct + impact_pct * sides
    return dict(fee_pct=fee_pct, spread_pct=spread_pct, slippage_pct=slip_pct,
                adverse_pct=adverse_pct if maker else 0.0,
                impact_pct=impact_pct * sides, total_pct=total,
                total_usd=notional_usd * total / 100, depth_near_usd=near)


def evaluate(pair, notional_usd, expected_move_pct, confidence, sides=2, label="", maker=False,
             regime=None):
    """NOTE: when `confidence` is 0.50 the directional term (2p-1) is exactly zero, so gross
    EV is zero for ANY move size and nothing can pass. That is the current measured state
    (registry R7). It is a consequence of having no demonstrated edge -- it is NOT a scan
    of the market finding nothing. Report it as such."""
    """When maker=True, the edge is discounted by the MEASURED probability the passive
    order actually fills. An unfilled post-only order costs nothing in fees but forfeits
    the opportunity -- and it must NEVER be auto-converted to a taker order to force entry
    (see should_cross_spread)."""
    """confidence in [0,1]: probability the expected move is realised rather than its opposite.
    Expected gross = expected_move_pct * (2*confidence - 1)  (a coin flip earns nothing)."""
    c = costs(pair, notional_usd, sides, maker=maker)
    gross = expected_move_pct * (2 * confidence - 1)
    fill_p, fill_src = (1.0, "taker fills certainly")
    if maker:
        reg = regime or execution_stats.vol_regime(pair)[0]
        fill_p, fill_src = execution_stats.maker_fill_prob(reg)
    # Q3 fix: previously net = (gross - total) * fill_p, which was then compared against an
    # ABSOLUTE per-trade floor. Scaling both sides is right for EV-per-attempt but makes the
    # number non-comparable to a per-completed-trade floor, so a genuinely good trade with a
    # 0.40 fill probability was rejected by a floor it would clear once filled.
    # Now: gate the floor on net-if-filled; use fill_p only for the sign test and ranking.
    net_if_filled = gross - c["total_pct"]
    net = net_if_filled * fill_p          # expected value per ATTEMPT (for ranking)
    passes = (net_if_filled >= MIN_ABS_EDGE_PCT
              and net_if_filled >= c["total_pct"] * (EDGE_MARGIN - 1)
              and net > 0)
    return dict(label=label, pair=pair, notional_usd=notional_usd, maker=maker,
                fill_prob=fill_p, fill_prob_source=fill_src,
                expected_move_pct=expected_move_pct, confidence=confidence,
                gross_pct=gross, **c, net_pct=net, net_if_filled_pct=net_if_filled,
                net_usd=notional_usd * net / 100,
                passes=passes,
                required_move_pct=(c["total_pct"] * EDGE_MARGIN) / max(2 * confidence - 1, 1e-9),
                verdict="TRADE" if passes else "HOLD")


def should_cross_spread(maker_result, taker_result):
    """A post-only order that does not fill must NOT automatically become a taker order.
    Crossing is justified only when the taker route is ITSELF positive-EV on its own
    merits -- never merely to force an entry that the passive route missed."""
    if not taker_result["passes"]:
        return False, ("do NOT cross: the taker route is not independently positive-EV; "
                       "a missed passive fill is a missed opportunity, not a reason to pay up")
    gain = taker_result["net_pct"] - maker_result["net_pct"] * maker_result.get("fill_prob", 1.0)
    if gain <= 0:
        return False, "do NOT cross: crossing does not improve expected net value"
    return True, f"crossing justified: taker route independently passes, +{gain:.2f}% expected"


def report(r):
    print(f"  {r['label'] or r['pair']}: move {r['expected_move_pct']:+.2f}% @ conf {r['confidence']:.0%} "
          f"-> gross {r['gross_pct']:+.2f}%")
    print(f"    costs: fees {r['fee_pct']:.2f}% + spread/slip {r['slippage_pct']:.3f}% "
          f"(adverse {r.get('adverse_pct',0):.3f}%) + impact {r['impact_pct']:.3f}% "
          f"= {r['total_pct']:.2f}% (${r['total_usd']:.2f})")
    if r.get("maker"):
        print(f"    fill probability {r['fill_prob']:.0%} [{r['fill_prob_source']}]")
    print(f"    NET {r['net_pct']:+.2f}% (${r['net_usd']:+.2f})  |  needs a {r['required_move_pct']:.2f}% "
          f"move at this confidence  ->  {r['verdict']}")


if __name__ == "__main__":
    import account
    pv = account.value()["total_usd"]
    print(f"portfolio ${pv:.2f} | taker {TAKER*100:.2f}%/side | margin {EDGE_MARGIN}x | floor {MIN_ABS_EDGE_PCT}%\n")
    print("=== TAKER (market orders) ===")
    for conf in (0.60, 0.70):
        report(evaluate("LINKUSD", pv, 5.0, conf, label=f"taker conf {conf:.0%}"))
    print("\n=== MAKER (limit orders) -- half the fee, no spread crossing ===")
    for conf in (0.60, 0.70):
        report(evaluate("LINKUSD", pv, 5.0, conf, label=f"maker conf {conf:.0%}", maker=True))
    print("\n=== measured trigger edges vs each cost basis (3d excess, clustered) ===")
    tk = costs("LINKUSD", pv, 2)["total_pct"]; mk = costs("LINKUSD", pv, 2, maker=True)["total_pct"]
    print(f"    taker round trip {tk:.2f}%   |   maker round trip {mk:.2f}%")
    for name, exc, t in (("vol_expansion", 1.75, 1.19), ("breakout", 1.22, 1.85),
                         ("volume_spike", -0.00, -0.00), ("breakdown", -0.41, -1.28)):
        print(f"    {name:<15} excess {exc:+.2f}% (t={t:+.2f})  net taker {exc-tk:+.2f}%  net maker {exc-mk:+.2f}%")
