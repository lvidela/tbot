"""Session identity derived from the real clock -- never invented.

Session-id labels written before 2026-09-25 were typed by hand and drifted from actual
event times by up to 7.4 hours (label `s-2026-09-24T15:40Z-07` carries events at
23:02:45Z). The `ts` fields were always correct; only the labels were wrong. Anything that
labels a record with a time must read the clock.
"""
import datetime, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "logs", "activity.jsonl")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_session_id(seq=None):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    if seq is None:
        seq = 0
        if os.path.exists(LOG):
            with open(LOG) as fh:
                for line in fh:
                    if '"session_start"' in line:
                        seq += 1
        seq += 1
    return f"s-{stamp}-{seq:02d}"


def log(session_id, **kw):
    kw = {"ts": now_iso(), "session_id": session_id, **kw}
    with open(LOG, "a") as fh:
        fh.write(json.dumps(kw) + "\n")
    return kw


if __name__ == "__main__":
    print(new_session_id())
