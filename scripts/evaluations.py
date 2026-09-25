"""Evaluation outcomes: the feedback channel from a Claude session back to the monitor.

Without this the monitor can distinguish a new signal from an unchanged one, but it cannot
know that a session already LOOKED at a signal and rejected it -- case (E). It would then
re-escalate the moment the detector re-armed, which is how AAVEUSD produced two identical
sessions 74 minutes apart on 2026-09-25.

Semantics: an evaluation is recorded against (asset, event_type) together with the signal
MAGNITUDE that was evaluated. Once a signal has been evaluated, recurrence alone no longer
justifies a new session -- only a materially stronger or reversed signal does. The bar goes
up because the question has already been answered at that magnitude.

This is a dedup input only. It has no influence whatsoever on any trading gate, threshold or
sizing rule, and it can never cause an order to be placed.
"""
import fcntl, json, os, sys, time, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVALS = os.path.join(ROOT, "data", "evaluations.json")
ELOCK = os.path.join(ROOT, "data", "evaluations.lock")
# Module-level so tests can redirect it. Writing test fixtures into the real append-only
# audit record would falsify it, and it cannot be cleaned up afterwards without falsifying
# it further -- so the seam has to exist before the test runs, not after.
ACTIVITY = os.path.join(ROOT, "logs", "activity.jsonl")
# Prune verdicts after a week. Originally incidental ("the experiment ends 2026-10-15
# anyway"); with an OPEN-ENDED horizon (2026-09-25) it is a deliberate choice, so state the
# reason: a week-old verdict on a market signal is stale evidence about a current signal, and
# letting ALREADY_EVALUATED persist forever would permanently mute an asset after one look.
# Expiry is the safer failure mode -- it costs a re-evaluation, not a missed opportunity.
KEEP_SEC = 7 * 86400

PENDING = "pending"            # escalated, session not yet reported back
REJECTED = "rejected"          # session evaluated it and declined to trade
TRADED = "traded"              # session acted on it
INCONCLUSIVE = "inconclusive"  # session could not complete (e.g. blocked or timed out)


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def key(asset, event_type):
    return f"{asset}:{event_type}"


def _rw(fn):
    os.makedirs(os.path.dirname(EVALS), exist_ok=True)
    with open(ELOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        rows = {}
        if os.path.exists(EVALS):
            try: rows = json.load(open(EVALS))
            except Exception: rows = {}
        out, rows = fn(rows)
        cutoff = time.time() - KEEP_SEC
        rows = {k: v for k, v in rows.items() if v.get("ts", 0) >= cutoff}
        tmp = EVALS + ".tmp"
        json.dump(rows, open(tmp, "w"), indent=2)
        os.replace(tmp, EVALS)
        return out


def record(asset, event_type, magnitude, outcome, note="", session_id=""):
    """Record what a session concluded about a signal. Appends to the audit log too."""
    def fn(rows):
        k = key(asset, event_type)
        rows[k] = dict(asset=asset, event_type=event_type, magnitude=float(magnitude),
                       outcome=outcome, note=note, session_id=session_id,
                       ts=time.time(), ts_iso=_now_iso())
        return (rows[k], rows)
    rec = _rw(fn)
    try:
        with open(ACTIVITY, "a") as fh:
            fh.write(json.dumps({
                "ts": rec["ts_iso"], "session_id": session_id or "bot:monitor",
                "event": "analysis",
                "summary": f"EVALUATION {outcome}: {asset} [{event_type}] at magnitude "
                           f"{float(magnitude):.4f}. {note}".strip(),
            }) + "\n")
    except Exception:
        pass
    return rec


def last_for(asset, event_type):
    """The most recent evaluation of this signal, or None."""
    if not os.path.exists(EVALS):
        return None
    try:
        return json.load(open(EVALS)).get(key(asset, event_type))
    except Exception:
        return None


def all_records():
    if not os.path.exists(EVALS):
        return {}
    try: return json.load(open(EVALS))
    except Exception: return {}


if __name__ == "__main__":
    if len(sys.argv) >= 5 and sys.argv[1] == "record":
        _, _, asset, event_type, magnitude, outcome = (sys.argv + [""] * 6)[:6]
        note = " ".join(sys.argv[6:])
        print(json.dumps(record(asset, event_type, float(magnitude), outcome, note), indent=2))
    else:
        for k, v in sorted(all_records().items()):
            print(f"{v['ts_iso']}  {k:<40} {v['outcome']:<13} mag {v['magnitude']:.4f}  {v.get('note','')[:60]}")
