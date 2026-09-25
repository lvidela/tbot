#!/usr/bin/env bash
# Launch a Claude reasoning session in response to a monitor escalation.
# Must never loop, never retry aggressively, and never place orders itself.
set -uo pipefail
ROOT="/home/lisandro"
REASON="${1:-unspecified}"
DETAIL="${2:-}"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LOGDIR="$ROOT/logs/claude_sessions"
mkdir -p "$LOGDIR"

if [ -e "$ROOT/STOP" ]; then
  echo "{\"ts\":\"$TS\",\"session_id\":\"bot:monitor\",\"event\":\"kill_switch\",\"summary\":\"Claude launch aborted: STOP present.\"}" >> "$ROOT/logs/activity.jsonl"
  exit 0
fi

# systemd user services get a minimal PATH that excludes nvm, so resolve explicitly.
CLAUDE_BIN=""
for cand in "/home/lisandro/.nvm/versions/node/v24.21.0/bin/claude" $(ls -d /home/lisandro/.nvm/versions/node/*/bin/claude 2>/dev/null) "$(command -v claude 2>/dev/null || true)"; do
  [ -n "$cand" ] && [ -x "$cand" ] && CLAUDE_BIN="$cand" && break
done
if [ -z "$CLAUDE_BIN" ]; then
  echo "{\"ts\":\"$TS\",\"session_id\":\"bot:monitor\",\"event\":\"error\",\"summary\":\"Claude CLI not found on PATH; escalation '$REASON' not serviced. Monitor continues; positions untouched.\"}" >> "$ROOT/logs/activity.jsonl"
  exit 0
fi

# CONCURRENCY CONTROL -- not a rate limit. Concurrent sessions would interleave writes to
# STATE.md, STRATEGY.md, the journal and the activity log and corrupt the records. One at a
# time; if a session is already reasoning, this event is logged and skipped rather than
# queued, because by the time a slot frees the market context is stale anyway. There is NO
# global cooldown and NO daily cap -- the next qualifying event escalates immediately.
exec 9>"$ROOT/data/claude_session.lock"
if ! flock -n 9; then
  # A session is already reasoning. QUEUE the opportunity rather than discarding it -- the
  # next session drains the queue and revalidates each entry against FRESH market data.
  /usr/bin/python3 - "$REASON" "$DETAIL" <<'PYQ'
import sys, os
sys.path.insert(0, "/home/lisandro/scripts")
import oppqueue
reason, detail = sys.argv[1], sys.argv[2]
asset = detail.split(":")[0].strip() if ":" in detail else reason
res = oppqueue.enqueue(asset, reason, detail)
print(res)
PYQ
  echo "{\"ts\":\"$TS\",\"session_id\":\"bot:monitor\",\"event\":\"analysis\",\"summary\":\"Escalation '$REASON' QUEUED (a Claude session is running). Retained for the next session, which revalidates against fresh data. Detail: $DETAIL\"}" >> "$ROOT/logs/activity.jsonl"
  exit 0
fi

PROMPT="A monitor escalation fired.

REASON: $REASON
DETAIL: $DETAIL

Read CLAUDE.md and follow the session routine. Context is in data/escalation_context.json.
An event is a reason to INVESTIGATE, not a reason to trade. Compare holding the current
portfolio against realistic alternatives after full transaction costs, and HOLD unless the
expected advantage clearly exceeds those costs. Complete your work, update the records, and
end the session. Do not loop or wait."

timeout 1800 "$CLAUDE_BIN" -p "$PROMPT" \
  > "$LOGDIR/$TS-$REASON.log" 2>&1
RC=$?
if [ $RC -ne 0 ]; then
  echo "{\"ts\":\"$TS\",\"session_id\":\"bot:monitor\",\"event\":\"error\",\"summary\":\"Claude session for '$REASON' exited rc=$RC (timeout is 1800s). Monitor continues; positions untouched; no orders placed.\"}" >> "$ROOT/logs/activity.jsonl"
fi
exit 0
