"""Run the live tactical scan and log EVERY economically meaningful rejection.

Selection rule is fixed in advance and applied without exception (requirement 7 --
no cherry-picking): any asset reaching confluence >= MIN_CONF_TO_LOG is recorded,
whatever its rejection reason and whatever it later does. Losers included.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tactical, counterfactual, account, execution_stats

MIN_CONF_TO_LOG = 2          # deliberately BELOW the live gate's minimum of 3


def main(session_id="bot:counterfactual"):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.exists(os.path.join(root, "STOP")):
        print("STOP present; ledger is read-only anyway, halting.")
        return 0
    counterfactual.resolve_due(verbose=True)
    pv = account.value()["total_usd"]
    results = tactical.scan(pv, verbose=False)
    logged = 0
    for a, e in results:
        if e.get("qualifies"):
            continue                                   # not a rejection
        if (a.get("confluence") or 0) < MIN_CONF_TO_LOG:
            continue
        try:
            regime, _ = execution_stats.vol_regime(a["pair"])
        except Exception:
            regime = "unknown"
        notional = e.get("notional") or round(pv * 0.20, 2)
        counterfactual.record_rejection(
            pair=a["pair"], session_id=session_id, event_type="+".join(
                k for k, v in a["conditions"].items() if v and k != "spread_acceptable") or "none",
            rejection_reason=e.get("reason", "unspecified")[:80],
            confluence=a.get("confluence"),
            signals=[k for k, v in a["conditions"].items() if v],
            notional=notional, regime=regime,
            exit_rule=(e.get("exit_thesis") or {}).get("invalidation",
                       "mark-to-market at horizon, exit crosses to bid"),
            expected_move_pct=e.get("expected_move_pct"), net_pct=e.get("net_pct"),
            extra=dict(vol_ratio=a.get("vol_ratio"), volume_ratio=a.get("volume_ratio"),
                       mom_4h=a.get("mom_4h"), rel_strength=a.get("rel_strength"),
                       daily_vol=a.get("daily_vol"), move_to_cost=e.get("move_to_cost")))
        logged += 1
        print(f"  logged rejection: {a['pair']:<12} conf{a.get('confluence')} "
              f"-> {e.get('reason','')[:52]}")
    print(f"{logged} rejected opportunities recorded")
    return logged


if __name__ == "__main__":
    main()
