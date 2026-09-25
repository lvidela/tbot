"""Tests for the shadow ledger, focused on defect D8.

D8: the ledger recorded only ABSOLUTE return. Every shadow entry is funded by selling
LINK, so the alternative is holding LINK -- not holding cash. In a market-wide rally an
entry can show a healthy absolute profit while losing badly to the asset it was funded
by. Measuring absolute return reproduces exactly the non-demeaned error already rejected
as R1/R6, inside the one dataset that is genuinely forward out-of-sample.
"""
import json, os, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shadow

PASS = FAIL = 0


def check(name, cond, note=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}" + (f": {note}" if note else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {name}" + (f": {note}" if note else ""))


print("=== shadow ledger (D8 regression) ===")

# --- isolate the ledger so tests never touch real records -------------------
tmpdir = tempfile.mkdtemp()
shadow.SHADOW = os.path.join(tmpdir, "shadow_trades.json")
shadow.SLOCK = os.path.join(tmpdir, "shadow.lock")

PRICES = {"TESTUSD": 100.0, "LINKUSD": 10.0}
shadow.kraken.best_bid = lambda p: PRICES[p]

rid = shadow.open_shadow(
    pair="TESTUSD", strategy="unit", predicted_move_pct=5.0, predicted_prob=0.5,
    confluence=4, signals=["x"], entry_price=100.0,
    exit_thesis={"max_loss_pct": 50.0}, horizon_hours=72, notional=10.0)

rows = json.load(open(shadow.SHADOW))
r = rows[0]
check("entry records the benchmark it is funded by",
      r.get("benchmark_pair") == "LINKUSD" and r.get("benchmark_entry_bid") == 10.0,
      f"{r.get('benchmark_pair')} @ {r.get('benchmark_entry_bid')}")

# --- the rally case: both rise, the trade still loses to the benchmark ------
PRICES["TESTUSD"] = 104.0   # +4%
PRICES["LINKUSD"] = 11.0    # +10%
shadow.mark_to_market()
r = json.load(open(shadow.SHADOW))[0]

check("absolute return still recorded", abs(r["current_pct"] - 4.0) < 1e-6, f"{r['current_pct']:+.2f}%")
check("benchmark return recorded", abs(r["benchmark_pct"] - 10.0) < 1e-6, f"{r['benchmark_pct']:+.2f}%")
check("D8: excess is return MINUS benchmark, and is negative in a rally",
      abs(r["excess_pct"] - (-6.0)) < 1e-6,
      f"absolute {r['current_pct']:+.2f}% looks like a win; excess {r['excess_pct']:+.2f}% is the truth")

# --- closing must carry the excess through, charging full rotation cost -----
PRICES["TESTUSD"] = 104.0
PRICES["LINKUSD"] = 11.0
rows = json.load(open(shadow.SHADOW))
rows[0]["opened_ts"] = time.time() - 73 * 3600      # force horizon close
json.dump(rows, open(shadow.SHADOW, "w"))
closed = shadow.mark_to_market()
r = json.load(open(shadow.SHADOW))[0]

check("horizon close fires", r["status"] == "closed" and len(closed) == 1, r.get("close_reason", ""))
check("realized excess gross = trade - benchmark",
      abs(r["realized_excess_gross_pct"] - (-6.0)) < 1e-6, f"{r['realized_excess_gross_pct']:+.2f}%")
check("holding the benchmark is free, so the rotation pays FULL cost against it",
      abs(r["realized_excess_net_pct"] - (-6.0 - r["assumed_cost_pct"])) < 1e-6,
      f"{r['realized_excess_net_pct']:+.2f}% after {r['assumed_cost_pct']}%")
check("a trade that beat the benchmark in ABSOLUTE terms is not recorded as a win",
      r["realized_net_pct"] > 0 > r["realized_excess_net_pct"],
      f"absolute net {r['realized_net_pct']:+.2f}% vs excess net {r['realized_excess_net_pct']:+.2f}%")

# --- the ledger must never be able to trade --------------------------------
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shadow.py")).read()
check("shadow.py never imports the execution path", "import execute" not in src)
check("shadow.py never calls AddOrder", "AddOrder" not in src)

print(f"\n{PASS}/{PASS + FAIL} shadow tests passed")
sys.exit(1 if FAIL else 0)
