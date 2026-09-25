"""Run the tactical scan and record EVERY confluence>=2 setup as a shadow prediction.

Deliberately records setups BELOW the live gate as well as above it. If we only ever
recorded the ones we traded, we could never learn whether the gate is rejecting good
trades -- we would only ever see the outcomes we selected for.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tactical, shadow, account, kraken

MIN_CONF_TO_RECORD = 2      # below the live gate on purpose


def main():
    if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "STOP")):
        print("STOP present; shadow scan is read-only anyway, but halting.")
        return
    shadow.mark_to_market()
    pv = account.value()["total_usd"]
    results = tactical.scan(pv, verbose=False)
    existing = json.load(open(shadow.SHADOW)) if os.path.exists(shadow.SHADOW) else []
    open_pairs = {r["pair"] for r in existing if r["status"] == "open"}
    n = 0
    for a, e in results:
        if a["confluence"] < MIN_CONF_TO_RECORD or a["pair"] in open_pairs:
            continue
        mv = tactical.expected_move(a)
        p = tactical.success_probability(a)
        ex = e.get("exit_thesis") or dict(max_loss_pct=round(a["daily_vol"]*100, 2))
        rid = shadow.open_shadow(
            a["pair"], "tactical_v4", round(mv, 3), round(p, 3), a["confluence"],
            [k for k, v in a["conditions"].items() if v and k != "spread_acceptable"],
            a["bid"], ex, horizon_hours=72,
            notional=round(pv * e.get("size_frac", 0.20), 2))
        print(f"  shadow OPEN {a['pair']:<12} conf{a['confluence']} predicted {mv:+.2f}% "
              f"p={p:.2f} {'[would trade live]' if e['qualifies'] else '[below live gate]'}")
        n += 1
    print(f"{n} new shadow predictions recorded")
    shadow.report()


if __name__ == "__main__":
    main()
