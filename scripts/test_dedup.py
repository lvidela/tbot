"""Persistent-signal deduplication tests (2026-09-25).

Regression target: on 2026-09-25 AAVEUSD was at 100% of its 30d range at 11:15:26Z and again
at 12:29:26Z -- position 1.00 both times, bid 148.12 -> 148.07 -- and the monitor launched a
second Claude session that re-derived the first one's answer. The cause was a time-based
escape hatch in should_escalate(): `age >= MIN_REFIRE_SEC` admitted an identical signal.

These tests pin BOTH directions. Suppressing noise is only safe if genuine signals still get
through, so most of what follows asserts that escalation still happens.
"""
import json, os, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monitor, evaluations

PASS = FAIL = 0


def check(name, cond, note=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  [PASS] {name}" + (f": {note}" if note else ""))
    else:
        FAIL += 1; print(f"  [FAIL] {name}" + (f": {note}" if note else ""))


# --- isolate: never touch the real audit log or the real evaluation records ---------------
tmp = tempfile.mkdtemp()
monitor.LOG = os.path.join(tmp, "activity.jsonl")
monitor.STATE = os.path.join(tmp, "monitor_state.json")
evaluations.EVALS = os.path.join(tmp, "evaluations.json")
evaluations.ELOCK = os.path.join(tmp, "evaluations.lock")
evaluations.ACTIVITY = os.path.join(tmp, "activity.jsonl")   # never write fixtures to the real log


def fresh():
    return dict(armed={}, fired={}, cleared={}, escalations=[], suppressed=0)


def seen(state, reason, asset, value, ts):
    """Mark a signal as already escalated at `value`/`ts`."""
    state.setdefault("fired", {})[f"{reason}:{asset}"] = dict(
        ts=ts, ts_iso="2026-09-25T11:15:26Z", value=value)


NOW = 1790000000.0
print("=== persistent-signal deduplication ===")

# --- (C) THE REGRESSION: the exact AAVEUSD numbers ----------------------------------------
st = fresh()
seen(st, "breakout", "AAVEUSD", 1.00, NOW)
tr, why = monitor.classify_signal("breakout", "AAVEUSD", 1.00, st, now_ts=NOW + 74 * 60)
check("AAVEUSD 74m later, position 1.00 -> 1.00, is UNCHANGED and suppressed",
      tr == monitor.UNCHANGED and tr not in monitor.ESCALATING_TRANSITIONS, why)

for mins in (15, 74, 300, 1440):
    tr, _ = monitor.classify_signal("breakout", "AAVEUSD", 1.00, st, now_ts=NOW + mins * 60)
    check(f"elapsed time alone never escalates it ({mins}m)", tr == monitor.UNCHANGED)

# --- (A) new signals ----------------------------------------------------------------------
st = fresh()
tr, why = monitor.classify_signal("breakout", "SOLUSD", 1.00, st, now_ts=NOW)
check("(A) a never-seen asset+event escalates", tr == monitor.NEW, why)

seen(st, "breakout", "AAVEUSD", 1.00, NOW)
tr, why = monitor.classify_signal("vol_expansion", "AAVEUSD", 3.10, st, now_ts=NOW + 60)
check("(A) a NEW EVENT TYPE on an already-seen asset escalates", tr == monitor.NEW, why)

# --- independence: other assets must not be collateral damage -----------------------------
tr, why = monitor.classify_signal("breakout", "XRPUSD", 1.00, st, now_ts=NOW + 60)
check("a DIFFERENT asset with an identical signal escalates independently",
      tr == monitor.NEW, why)

st2 = fresh()
fired = []
for i, a in enumerate(["SOLUSD", "XRPUSD", "ADAUSD", "NEARUSD", "INJUSD", "SUIUSD"]):
    t, _ = monitor.classify_signal("breakout", a, 1.00, st2, now_ts=NOW + i)
    st2["fired"][f"breakout:{a}"] = dict(ts=NOW + i, ts_iso="x", value=1.00)
    fired.append(t)
check("no global cooldown: 6 assets escalate within 6 seconds",
      all(t == monitor.NEW for t in fired), f"{len(fired)}/6 escalated")

# --- (B) materially changed still escalates -----------------------------------------------
st = fresh(); seen(st, "breakout", "AAVEUSD", 1.00, NOW)
tr, why = monitor.classify_signal("breakout", "AAVEUSD", 1.45, st, now_ts=NOW + 60)
check("(B) a 45% stronger signal escalates immediately", tr == monitor.STRENGTHENED, why)

tr, _ = monitor.classify_signal("breakout", "AAVEUSD", 1.39, st, now_ts=NOW + 60)
check("(B) 39% stronger stays below the 40% threshold", tr == monitor.UNCHANGED)

st = fresh(); seen(st, "rel_strength", "ZROUSD", 0.25, NOW)
tr, why = monitor.classify_signal("rel_strength", "ZROUSD", -0.25, st, now_ts=NOW + 60)
check("(B) a sign reversal escalates immediately", tr == monitor.REVERSED, why)

# --- (D) weakened, and the dip-and-recover trap -------------------------------------------
st = fresh(); seen(st, "vol_expansion", "NILUSD", 4.00, NOW)
tr, why = monitor.classify_signal("vol_expansion", "NILUSD", 2.00, st, now_ts=NOW + 600)
check("(D) a decaying signal is WEAKENED, not an opportunity", tr == monitor.WEAKENED, why)
tr, _ = monitor.classify_signal("vol_expansion", "NILUSD", 4.00, st, now_ts=NOW + 1200)
check("(D) baseline is NOT lowered by weakening, so recovery to the old level is UNCHANGED",
      tr == monitor.UNCHANGED, "a dip-and-recover must not read as a +100% change")

# --- (D) episode boundary: wobble vs genuine recurrence -----------------------------------
st = fresh(); seen(st, "breakout", "AAVEUSD", 1.00, NOW)
st["cleared"]["breakout:AAVEUSD"] = NOW + 30 * 60
tr, why = monitor.classify_signal("breakout", "AAVEUSD", 1.00, st, now_ts=NOW + 44 * 60)
check("a wobble across the hysteresis band is the SAME episode, suppressed",
      tr == monitor.UNCHANGED, why)

st = fresh(); seen(st, "breakout", "AAVEUSD", 1.00, NOW)
st["cleared"]["breakout:AAVEUSD"] = NOW + 60 * 60
tr, why = monitor.classify_signal("breakout", "AAVEUSD", 1.00, st,
                                  now_ts=NOW + 60 * 60 + monitor.EPISODE_GAP_SEC + 1)
check("a condition that ENDED and stayed clear past the gap RECURS and escalates",
      tr == monitor.RECURRED, why)

# --- (E) session feedback -----------------------------------------------------------------
st = fresh(); seen(st, "breakout", "AAVEUSD", 1.00, NOW)
st["cleared"]["breakout:AAVEUSD"] = NOW + 60
evaluations.record("AAVEUSD", "breakout", 1.00, evaluations.REJECTED, note="single signal")
tr, why = monitor.classify_signal("breakout", "AAVEUSD", 1.00, st,
                                  now_ts=NOW + 10 * monitor.EPISODE_GAP_SEC)
check("(E) a signal a session already REJECTED does not recur into a new session",
      tr == monitor.ALREADY_EVALUATED, why)

tr, why = monitor.classify_signal("breakout", "AAVEUSD", 1.80, st, now_ts=NOW + 7200)
check("(E) but an evaluated signal that strengthens 40%+ still escalates",
      tr == monitor.STRENGTHENED, why)

evaluations.record("ZROUSD", "breakout", 1.00, evaluations.PENDING, note="awaiting verdict")
st3 = fresh(); seen(st3, "breakout", "ZROUSD", 1.00, NOW)
tr, _ = monitor.classify_signal("breakout", "ZROUSD", 1.00, st3, now_ts=NOW + 60)
check("(E) a PENDING evaluation does not count as an answer", tr == monitor.UNCHANGED)

# --- Task 3: every suppression is explainable ---------------------------------------------
open(monitor.LOG, "w").close()
# A pristine asset: AAVEUSD carries a REJECTED evaluation from the (E) block above, which
# would make this an ALREADY_EVALUATED suppression instead of the UNCHANGED one under test.
st = fresh(); seen(st, "breakout", "LTCUSD", 1.00, NOW)
res = monitor.escalate("breakout", "LTCUSD: at 100% of range", st, {}, asset="LTCUSD", value=1.00)
lines = [json.loads(l) for l in open(monitor.LOG) if l.strip()]
sup = [l for l in lines if "SUPPRESSED" in l.get("summary", "")]
check("suppression returns False and launches nothing", res is False)
check("suppression writes an audit line", len(sup) == 1, sup[0]["summary"][:80] if sup else "none")
if sup:
    e = sup[0]
    check("the line names the transition", "UNCHANGED" in e["summary"])
    check("the line names the asset and event type",
          "LTCUSD" in e["summary"] and "breakout" in e["summary"])
    check("the reasoning carries both magnitudes and the prior timestamp",
          "magnitude_now" in e["reasoning"] and "first_escalated" in e["reasoning"])
    check("the record states no cooldown or cap was applied",
          "no cooldown or cap" in e["reasoning"].lower() or "No cooldown" in e["reasoning"])
check("suppression counters are kept per transition",
      st.get("suppressed") == 1 and st.get("suppressed_by", {}).get("UNCHANGED") == 1)

# --- the periodic review must not be caught by signal dedup -------------------------------
st = fresh()
st["fired"]["periodic_review:portfolio"] = dict(ts=NOW, ts_iso="x", value=NOW)
open(monitor.LOG, "w").close()
launched = []
monitor.subprocess = type("S", (), {"Popen": staticmethod(lambda *a, **k: launched.append(a)),
                                    "DEVNULL": None})
res = monitor.escalate("periodic_review", "24h review", st, {}, asset="portfolio", value=NOW + 1)
check("the ~24h strategic review bypasses signal dedup", res is True)

# --- the monitor still cannot trade -------------------------------------------------------
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitor.py")).read()
check("monitor.py never imports the execution path", "import execute" not in src)
check("monitor.py never calls AddOrder", "AddOrder" not in src)
import ast as _ast
_names = {n.id for n in _ast.walk(_ast.parse(src)) if isinstance(n, _ast.Name)}
_names |= {t.id for n in _ast.walk(_ast.parse(src)) if isinstance(n, _ast.Assign)
           for t in n.targets if isinstance(t, _ast.Name)}
check("the time-based re-fire escape hatch is gone from the CODE",
      "MIN_REFIRE_SEC" not in _names,
      "the name survives only in the comment explaining why it was removed")
check("evaluations.py cannot place orders",
      "AddOrder" not in open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "evaluations.py")).read())

print(f"\n{PASS}/{PASS + FAIL} deduplication tests passed")
sys.exit(1 if FAIL else 0)
