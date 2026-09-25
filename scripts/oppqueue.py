"""Persistent opportunity queue.

Opportunities that arrive while a Claude session is running used to be DISCARDED.
They are now retained here and presented to the next session, which revalidates each
one against FRESH market data before acting. Stale opportunities are dropped.

Order execution stays serialized elsewhere (the session flock), so two sessions can
never independently place conflicting orders. This queue only preserves information.
"""
import fcntl, json, os, sys, time, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "data", "opportunity_queue.json")
QLOCK = os.path.join(ROOT, "data", "opportunity_queue.lock")
MAX_AGE_SEC = 3600          # older than this is stale by definition
MAX_QUEUE = 200


def _with_lock(fn):
    os.makedirs(os.path.dirname(QLOCK), exist_ok=True)
    with open(QLOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            rows = []
            if os.path.exists(QUEUE):
                try: rows = json.load(open(QUEUE))
                except Exception: rows = []
            out, rows = fn(rows)
            tmp = QUEUE + ".tmp"
            json.dump(rows[-MAX_QUEUE:], open(tmp, "w"), indent=2)
            os.replace(tmp, QUEUE)
            return out
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def enqueue(asset, event_type, detail, signals=None, snapshot=None, magnitude=0.0):
    def fn(rows):
        now = time.time()
        # collapse an existing pending entry for the same asset+event_type, keeping the
        # STRONGER magnitude and the newer snapshot -- never silently drop the opportunity
        for r in rows:
            if r["status"] == "pending" and r["asset"] == asset and r["event_type"] == event_type:
                if magnitude >= r.get("magnitude", 0):
                    r.update(detail=detail, magnitude=magnitude, snapshot=snapshot,
                             signals=signals or r.get("signals"), updated=now,
                             ts=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
                r["seen_count"] = r.get("seen_count", 1) + 1
                return ("merged", rows)
        rows.append(dict(
            id=f"{asset}:{event_type}:{int(now)}", asset=asset, event_type=event_type,
            ts=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            created=now, updated=now, detail=detail, signals=signals or [],
            snapshot=snapshot or {}, magnitude=magnitude, status="pending", seen_count=1))
        return ("queued", rows)
    return _with_lock(fn)


def pending(max_age=MAX_AGE_SEC):
    def fn(rows):
        now = time.time()
        live = []
        for r in rows:
            if r["status"] == "pending" and now - r["created"] > max_age:
                r["status"] = "expired"
                r["expired_reason"] = f"older than {max_age/60:.0f}m without being evaluated"
            elif r["status"] == "pending":
                live.append(r)
        live.sort(key=lambda r: -r.get("magnitude", 0))
        return (live, rows)
    return _with_lock(fn)


def resolve(opp_id, status, note=""):
    """status: actioned | rejected | stale"""
    def fn(rows):
        for r in rows:
            if r["id"] == opp_id:
                r["status"] = status
                r["resolution_note"] = note
                r["resolved_ts"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return (True, rows)
    return _with_lock(fn)


def stats():
    rows = []
    if os.path.exists(QUEUE):
        try: rows = json.load(open(QUEUE))
        except Exception: pass
    from collections import Counter
    return Counter(r["status"] for r in rows), len(rows)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        p = pending()
        print(f"{len(p)} pending opportunities")
        for r in p:
            age = (time.time()-r["created"])/60
            print(f"  [{r['magnitude']:6.2f}] {r['asset']:<12} {r['event_type']:<40} {age:5.1f}m  seen x{r['seen_count']}")
    else:
        c, n = stats()
        print(f"queue: {n} rows  {dict(c)}")
