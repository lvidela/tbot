"""HIGH-VOLATILITY TACTICAL MODE.

Core principle, enforced in code: VOLATILITY IS NOT AN EDGE. A single detector firing
never qualifies. A tactical candidate must show a CONFLUENCE of independent conditions,
and then still clear a 3x expected-move / all-in-cost gate.

Runs alongside (does not replace) the benchmark/normal strategy.
"""
import json, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken, edge, execution_stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- confluence thresholds ---------------------------------------------------------
VOL_EXPANSION_MIN = 1.5     # 1d realised move / 30d vol
VOLUME_MIN        = 3.0     # 24h volume / 30d average
MOMENTUM_MIN      = 0.02    # 4h directional move
REL_STRENGTH_MIN  = 0.03    # excess vs universe median over same window
MAX_SPREAD_BPS    = 25
MIN_CONFLUENCE    = 3       # at least 3 independent conditions must hold

# --- EV gate -----------------------------------------------------------------------
MOVE_TO_COST_MIN  = 3.0     # expected gross move >= 3x all-in round-trip cost
# REVISED 2026-09-24 (Q3). A tactical trade is 2 legs, not 4:
#   (a) leaving LINK is a ONE-TIME campaign cost, not a per-trade cost -- charging it to
#       every trade double-counts;
#   (b) the terminal "buy back LINK" leg does not exist: the experiment is valued in USD
#       CONTINUOUSLY (open-ended horizon, 2026-09-25) and we are never required to end in
#       LINK. With no settlement date the forced-return leg does not exist at any time,
#       so the 2-leg count is if anything better founded than it was under a fixed date.
# Honest campaign arithmetic: legs = 1 + 2N, i.e. amortised 2 + 1/N per trade.
TACTICAL_LEGS = 2
CAMPAIGN_ENTRY_COST = 0.485     # % -- charged ONCE on the LINK->USD transition, not per trade
DEFAULT_HOLD_DAYS = 3           # Q3: E|move| grows ~t^0.56; 1-day holds waste the cost
# Q3: 7 of 32 eligible alts cannot take an $8 clip at all, and 5 of those are top-6 by
# volatility. Without this filter the scanner can emit QUALIFIES on an unsizable pair.
MIN_NOTIONAL_RATIO = 2.0
# --- sizing ------------------------------------------------------------------------
SIZE_MIN, SIZE_MAX = 0.15, 0.30
SIZE_STRONG        = 0.40   # only for exceptional confluence + liquidity


def analyse(pair, key, universe_median_4h=None):
    """Return the full tactical picture for one pair. No trading decision here."""
    d = kraken.public("OHLC", pair=pair, interval=1440)
    k = [x for x in d if x != "last"][0]
    rows = d[k]
    closes = [float(r[4]) for r in rows]
    vols = [float(r[6]) * float(r[4]) for r in rows]
    rets = [(closes[i]/closes[i-1]-1) for i in range(1, len(closes))]
    if len(closes) < 40:
        return None
    v30 = statistics.pstdev(rets[-30:])
    v1 = abs(rets[-1])
    vol_ratio = v1/v30 if v30 else 0

    h4 = kraken.public("OHLC", pair=pair, interval=240)
    hk = [x for x in h4 if x != "last"][0]
    h4c = [float(r[4]) for r in h4[hk]]
    mom_4h = (h4c[-1]/h4c[-2]-1) if len(h4c) > 2 else 0.0
    mom_12h = (h4c[-1]/h4c[-4]-1) if len(h4c) > 4 else 0.0

    t = kraken.public("Ticker", pair=key)[key]
    bid, ask = float(t["b"][0]), float(t["a"][0])
    spread_bps = (ask-bid)/bid*1e4
    usd_vol = float(t["v"][1]) * float(t["p"][1])
    vol30_usd = statistics.mean(vols[-30:])
    volume_ratio = usd_vol/vol30_usd if vol30_usd else 0

    w = closes[-30:]
    rng = max(w)-min(w)
    pos_in_range = (bid-min(w))/rng if rng > 0 else 0.5
    rel = (mom_12h - universe_median_4h) if universe_median_4h is not None else None

    cond = dict(
        volatility_expansion = vol_ratio >= VOL_EXPANSION_MIN,
        volume_confirmation  = volume_ratio >= VOLUME_MIN,
        momentum_continuation= mom_4h >= MOMENTUM_MIN and mom_12h > 0,
        breakout_confirmed   = pos_in_range >= 0.95 and rng/bid >= 0.03 and mom_4h > 0,
        relative_strength    = (rel is not None and rel >= REL_STRENGTH_MIN),
        spread_acceptable    = spread_bps <= MAX_SPREAD_BPS,
    )
    # spread is a veto, not a contributor
    confluence = sum(1 for k2, v in cond.items() if v and k2 != "spread_acceptable")
    return dict(pair=pair, key=key, bid=bid, ask=ask, spread_bps=spread_bps,
                vol_ratio=round(vol_ratio,2), volume_ratio=round(volume_ratio,2),
                mom_4h=round(mom_4h,4), mom_12h=round(mom_12h,4),
                pos_in_range=round(pos_in_range,3), rel_strength=round(rel,4) if rel is not None else None,
                daily_vol=round(v30,4), conditions=cond, confluence=confluence,
                usd_vol_24h=usd_vol)


def expected_move(a, hold_days=DEFAULT_HOLD_DAYS):
    """Expected gross move, scaled to the asset's own volatility.

    Deliberately NOT the naive +2.40% volatility-expansion figure (registry R1).

    REVISED 2026-09-24 (Q3): now scales with sqrt(hold_days). The previous version always
    used 1-day sigma while the exit thesis contemplated a multi-day trail -- an internal
    inconsistency that understated the move for any hold longer than a day. Measured
    E|r_h| on the 12 most volatile eligible alts: 4.52% (1d) -> 8.14% (3d) -> 12.65% (7d),
    fitted exponent 0.561, i.e. marginally faster than sqrt(t).

    REVISED 2026-09-24 after Q2 calibration. The confluence uplift term
    `(1 + 0.15*(conf-3))` was REMOVED: over 449 clustered days there is no monotone
    relationship between confluence and demeaned forward return (registry R7). The
    0.5 multiplier is RETAINED rather than cut to the fitted 0.22, because the
    production sample (62 clustered days) has a 95% CI of [-0.20, +0.65] which contains
    both -- and 0.22*sigma would sit below the round-trip cost, i.e. adopting it would be
    switching the mode off on evidence too weak to justify either number.
    """
    sigma = a["daily_vol"] * 100
    return 0.5 * sigma * (hold_days ** 0.5)


def success_probability(a):
    """MEASURED continuation probability. Flat at the coin flip.

    REVISED 2026-09-24 (Q2). The previous `0.50 + 0.03*confluence` slope is not
    supported: realized P(positive 3d demeaned return) is 0.486 / 0.488 / 0.507 at
    confluence 3 / 4 / 5 over 449 clustered days -- flat, and indistinguishable from the
    0.476 unconditional baseline. The intercept 0.50 was right; the slope was invented.

    Consequence, stated plainly: at p = 0.50 the directional EV term is exactly zero, so
    no trade clears the cost. That is the correct reading of the evidence, not excess
    caution -- a coin flip paying a 1.83% toll is a losing bet at any move size.
    """
    return 0.50


def path_ev(target_sigma, stop_sigma, hit_rate, sigma_pct, cost_pct):
    """Path-based EV from explicit exit geometry. More honest than move*(2p-1) because
    it prices what the exit plan actually does, and it is what exposed the defect below."""
    return hit_rate * (target_sigma * sigma_pct) - (1 - hit_rate) * (stop_sigma * sigma_pct) - cost_pct


def breakeven_hit_rate(target_sigma, stop_sigma, sigma_pct, cost_pct):
    num = cost_pct + stop_sigma * sigma_pct
    den = target_sigma * sigma_pct + stop_sigma * sigma_pct
    return num / den if den else 1.0


# Minimum acceptable reward:risk geometry. The original exit thesis paired a 0.5-sigma
# target with a 1.0-sigma stop (1:2) -- registry A3 records that this needs a 92.0% hit
# rate and the measured rate is 81.0%, i.e. it was EV-NEGATIVE as published.
MIN_TARGET_TO_STOP = 1.0


def evaluate(a, portfolio_usd, hold_days=DEFAULT_HOLD_DAYS, min_notional=None):
    if not a or not a["conditions"]["spread_acceptable"]:
        return dict(pair=a["pair"] if a else "?", qualifies=False,
                    reason="spread unacceptable -- execution quality vetoes the trade")
    if a["confluence"] < MIN_CONFLUENCE:
        return dict(pair=a["pair"], qualifies=False, confluence=a["confluence"],
                    reason=f"confluence {a['confluence']} < {MIN_CONFLUENCE} required "
                           f"(volatility alone is not an edge)")
    size_frac = SIZE_MIN + (SIZE_MAX-SIZE_MIN) * min(1.0, (a["confluence"]-MIN_CONFLUENCE)/2.0)
    notional = portfolio_usd * size_frac
    # Executability gate: refuse to "qualify" a pair we cannot actually size.
    mn = min_notional if min_notional is not None else a.get("min_notional")
    if mn and mn > notional / MIN_NOTIONAL_RATIO:
        return dict(pair=a["pair"], qualifies=False, confluence=a["confluence"],
                    reason=f"unsizable: min notional ${mn:.2f} vs ${notional:.2f} clip "
                           f"(needs <= ${notional/MIN_NOTIONAL_RATIO:.2f})")
    regime, _ = execution_stats.vol_regime(a["pair"])
    mv = expected_move(a, hold_days)
    p = success_probability(a)
    c = edge.costs(a["pair"], notional, sides=TACTICAL_LEGS, maker=True)
    ratio = mv / c["total_pct"] if c["total_pct"] else 0
    ev = edge.evaluate(a["pair"], notional, mv, p, sides=TACTICAL_LEGS, maker=True, regime=regime,
                       label=f"tactical {a['pair']}")
    qualifies = ratio >= MOVE_TO_COST_MIN and ev["net_pct"] > 0 and ev["passes"]
    # HONESTY GUARD (registry D1). At the measured p=0.50 the directional term is exactly
    # zero, so the gate cannot pass at ANY volatility. Say that explicitly rather than
    # letting a structurally vacuous gate be reported as "the market offered nothing".
    vacuous = abs(p - 0.50) < 1e-9
    sigma = a["daily_vol"]*100
    return dict(pair=a["pair"], qualifies=qualifies, confluence=a["confluence"],
                size_frac=round(size_frac,3), notional=round(notional,2), hold_days=hold_days,
                expected_move_pct=round(mv,3), success_prob=round(p,3),
                all_in_cost_pct=round(c["total_pct"],3), move_to_cost=round(ratio,2),
                net_pct=round(ev["net_pct"],3), fill_prob=ev["fill_prob"], regime=regime,
                exit_thesis=dict(
                    invalidation=f"close below entry - {1.0*sigma:.2f}% (1 daily sigma)",
                    max_loss_pct=round(1.0*sigma,2),
                    target_pct=round(1.5*sigma,2),
                    target_to_stop=1.5,
                    trail_activate_pct=round(1.0*sigma,2),
                    breakeven_hit_rate=round(breakeven_hit_rate(1.5,1.0,sigma,c["total_pct"]),3),
                    measured_hit_rate_note="0.5sigma/1sigma geometry measured at 0.810; "
                                           "1.5sigma target hit rate is NOT measured and will be lower",
                    exhaustion="4h momentum turns negative or volume falls below 30d average",
                    hard_exit="thesis invalidation -> exit immediately; never average down"),
                gate_vacuous=vacuous,
                reason=("QUALIFIES" if qualifies else
                        "NO MEASURED EDGE (p=0.50): gate is structurally vacuous, not a market finding"
                        if vacuous else
                        f"move/cost {ratio:.2f}x < {MOVE_TO_COST_MIN}x required" if ratio < MOVE_TO_COST_MIN
                        else f"net {ev['net_pct']:.2f}% insufficient"))


def scan(portfolio_usd, verbose=True):
    u = json.load(open(os.path.join(ROOT, "data", "universe.json")))
    cands = [c for c in u["eligible"] if not c["is_stable"]
             and c["pair"] not in ("EURUSD","GBPUSD","PAXGUSD")]
    med = None
    analyses, errors = [], []
    for c in cands:
        try:
            a = analyse(c["pair"], c["key"])
            if a:
                a["min_notional"] = c.get("min_notional")
                analyses.append(a)
            else:
                errors.append((c["pair"], "insufficient history"))
        except Exception as ex:
            # D6: never silently swallow -- an errored asset must not be indistinguishable
            # from one that simply did not qualify, or "N of M qualify" is unreliable.
            errors.append((c["pair"], repr(ex)[:80]))
    if analyses:
        med = statistics.median(a["mom_12h"] for a in analyses)
        for a in analyses:
            a["rel_strength"] = round(a["mom_12h"] - med, 4)
            a["conditions"]["relative_strength"] = a["rel_strength"] >= REL_STRENGTH_MIN
            a["confluence"] = sum(1 for k, v in a["conditions"].items()
                                  if v and k != "spread_acceptable")
    results = [(a, evaluate(a, portfolio_usd)) for a in analyses]
    if errors:
        print(f"  [{len(errors)} assets could not be analysed: " +
              ", ".join(f"{p}({e[:28]})" for p, e in errors[:4]) + ("..." if len(errors) > 4 else "") + "]")
    results.sort(key=lambda r: (-r[1].get("net_pct", -99), -r[0]["confluence"]))
    if verbose:
        print(f"universe median 12h momentum: {med:+.2%}" if med is not None else "")
        print(f"{'pair':<12}{'conf':>5}{'vol_x':>7}{'volu_x':>8}{'mom4h':>8}{'rel':>8}{'E[move]':>9}{'cost':>7}{'m/c':>6}{'net':>8}  verdict")
        for a, e in results[:14]:
            print(f"{a['pair']:<12}{a['confluence']:>5}{a['vol_ratio']:>7.2f}{a['volume_ratio']:>8.2f}"
                  f"{a['mom_4h']:>+8.2%}{(a['rel_strength'] or 0):>+8.2%}"
                  f"{e.get('expected_move_pct',0):>8.2f}%{e.get('all_in_cost_pct',0):>6.2f}%"
                  f"{e.get('move_to_cost',0):>6.2f}{e.get('net_pct',0):>+7.2f}%  "
                  f"{'*** QUALIFIES ***' if e['qualifies'] else e['reason'][:40]}")
    return results


if __name__ == "__main__":
    import account
    pv = account.value()["total_usd"]
    print(f"portfolio ${pv:.2f} | confluence>={MIN_CONFLUENCE} | move/cost>={MOVE_TO_COST_MIN}x\n")
    r = scan(pv)
    q = [x for x in r if x[1]["qualifies"]]
    print(f"\n{len(q)} qualifying tactical opportunit{'y' if len(q)==1 else 'ies'}")
    for a, e in q: print(json.dumps(e, indent=2))
