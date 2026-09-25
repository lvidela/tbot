"""Continuous deterministic market monitor.

Runs 24/7 under systemd, independent of Claude. Observes the eligible Kraken Spot
universe, maintains rolling metrics, and escalates to a Claude reasoning session only
when a meaningful, debounced event occurs.

DESIGN NOTES

* Data source is the Kraken public `Ticker` endpoint polled on an interval. This is a
  deliberate choice over WebSocket: one unauthenticated REST call returns bid/ask,
  24h volume, VWAP, high/low and trade count for EVERY pair at once, so covering the
  whole universe costs 1 request per cycle -- not one per pair. The strategy horizon is
  days, so sub-second streaming would add reconnect/sequence-gap complexity and a
  third-party dependency to deliver resolution we do not use. `fetch_snapshot()` is
  isolated so a WebSocket feed can replace it without touching event logic.

* THE MONITOR NEVER PLACES ORDERS. It only observes and escalates. All execution lives
  in execute.py behind an explicit decision. A monitor bug, a Claude crash, or a Claude
  timeout therefore cannot produce uncontrolled trading -- the worst case is a missed
  or a spurious escalation.

* Single instance is enforced by an exclusive flock on a pidfile.
* State is persisted every cycle and reloaded on start, so restarts do not re-fire
  events that already escalated.
"""
import fcntl, json, os, subprocess, sys, time, datetime, statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "monitor_state.json")
LOCK = os.path.join(ROOT, "data", "monitor.lock")
LOG = os.path.join(ROOT, "logs", "activity.jsonl")
UNIVERSE = os.path.join(ROOT, "data", "universe.json")

POLL_SEC = 60
UNIVERSE_REFRESH_SEC = 6 * 3600
HEARTBEAT_SEC = 3600

# --- event thresholds (with hysteresis: a fired event must RESET below the clear
# --- level before it can fire again, so one noisy move cannot storm.)
TH = {
    "breakout":      dict(fire=1.00, clear=0.90),   # position in 30d range
    "breakdown":     dict(fire=0.00, clear=0.10),
    "vol_expansion": dict(fire=2.5,  clear=1.8),    # 24h realised vol / 30d average
    "volume_spike":  dict(fire=3.0,  clear=2.0),    # 24h volume / 30d average
    "spread_blowout":dict(fire=50.0, clear=25.0),   # bps
    "drawdown":      dict(fire=-0.15, clear=-0.10), # portfolio vs benchmark
    "rel_strength":  dict(fire=0.20, clear=0.12),   # another asset's 14d excess over held
}
# Assets whose price is pegged: a "30d range breakdown" on a stablecoin is a rounding
# artefact, not a market event. Excluded from all directional detectors.
PEGGED = {"USDTUSD", "USDCUSD", "DAIUSD", "PYUSDUSD", "RLUSDUSD", "USDGUSD", "USDSUSD",
          "TUSDUSD", "EURUSD", "GBPUSD", "AUDUSD", "PAXGUSD"}
# Position-in-range is only meaningful if the range itself is wide enough to matter.
MIN_RANGE_PCT = 0.03

# --- AGGRESSIVE OPPORTUNISTIC MODE -------------------------------------------------
# There is NO global cooldown and NO daily session cap. Any asset, any event type may
# reach Claude at any time. The only suppression is per-signal deduplication, scoped to
# (asset + event type + materially unchanged condition).
MATERIAL_CHANGE = 0.40        # a >=40% stronger signal is "materially different" -> immediate
PERIODIC_REVIEW_SEC = 24 * 3600   # additional strategic review; never gates event escalation

# --- PERSISTENT-SIGNAL DEDUPLICATION (2026-09-25) -----------------------------------------
# An UNCHANGED condition no longer escalates on the passage of time. It previously did:
# should_escalate() had a `time since last fire >= MIN_REFIRE_SEC` branch that admitted an
# identical signal regardless of magnitude. On 2026-09-25 AAVEUSD sat at 100% of its 30d range
# at 11:15:26Z and again at 12:29:26Z -- position 1.00 both times, bid 148.12 -> 148.07 -- and
# the second escalation spent a whole Claude session re-deriving the first one's answer.
#
# This is NOT a global cooldown and NOT a daily cap. There is no limit on how many assets or
# event types escalate, or how often, as long as each carries new information. What is gone is
# only the case that carried none.
#
# A condition that genuinely ENDED and later returned is a new episode and does escalate --
# but the detector's hysteresis band alone is too loose to establish that, because a signal
# sitting on its threshold crosses `clear` on noise. The condition must stay cleared for
# EPISODE_GAP_SEC before its return counts as new.
EPISODE_GAP_SEC = 3600        # a cleared signal must stay cleared this long to count as a new episode

# Signal state transitions. Every escalation decision resolves to exactly one of these and is
# logged with it, so a suppressed signal is always explainable after the fact.
NEW = "NEW"                        # never seen -> escalate
STRENGTHENED = "STRENGTHENED"      # >=MATERIAL_CHANGE stronger than last escalated -> escalate
REVERSED = "REVERSED"              # sign flip -> escalate
RECURRED = "RECURRED"              # cleared, stayed cleared, came back -> escalate
UNCHANGED = "UNCHANGED"            # materially identical -> suppress
WEAKENED = "WEAKENED"              # same sign, materially weaker -> suppress
ALREADY_EVALUATED = "ALREADY_EVALUATED"   # a session answered this magnitude -> suppress
ESCALATING_TRANSITIONS = (NEW, STRENGTHENED, REVERSED, RECURRED)


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(**kw):
    kw = {"ts": now(), "session_id": "bot:monitor", **kw}
    with open(LOG, "a") as fh:
        fh.write(json.dumps(kw) + "\n")


def stop_present():
    return os.path.exists(os.path.join(ROOT, "STOP"))


def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE))
        except Exception as e:
            log(event="error", summary=f"monitor state unreadable, starting fresh: {e}")
    return dict(armed={}, fired={}, cleared={}, last_escalation=0, escalations=[],
                last_periodic=0, last_heartbeat=0, last_universe=0, cycles=0, suppressed=0)


def save_state(s):
    tmp = STATE + ".tmp"
    json.dump(s, open(tmp, "w"), indent=2)
    os.replace(tmp, STATE)     # atomic


def fetch_snapshot(pairs):
    """One REST call covering the whole universe. Swap-in point for a WS feed."""
    tk = kraken.public("Ticker")
    out = {}
    for p, key in pairs.items():
        t = tk.get(key)
        if not t:
            continue
        try:
            bid, ask = float(t["b"][0]), float(t["a"][0])
            vwap, vol = float(t["p"][1]), float(t["v"][1])
            low, high = float(t["l"][1]), float(t["h"][1])
            if bid <= 0 or ask < bid:
                continue
            out[p] = dict(bid=bid, ask=ask, spread_bps=(ask-bid)/bid*1e4, vwap=vwap,
                          usd_vol=vol*vwap, low=low, high=high, trades=int(t["t"][1]))
        except Exception:
            continue
    return out


def daily_stats(pair):
    d = kraken.public("OHLC", pair=pair, interval=1440)
    k = [x for x in d if x != "last"][0]
    rows = d[k]
    closes = [float(r[4]) for r in rows]
    vols = [float(r[6]) * float(r[5]) for r in rows]
    rets = [(closes[i]/closes[i-1]-1) for i in range(1, len(closes))]
    return dict(
        closes=closes[-60:],
        r30_low=min(closes[-30:]), r30_high=max(closes[-30:]),
        vol30=statistics.pstdev(rets[-30:]) if len(rets) >= 30 else 0.0,
        vol1=abs(rets[-1]) if rets else 0.0,
        volume30=statistics.mean(vols[-30:]) if len(vols) >= 30 else 0.0,
        volume1=vols[-1] if vols else 0.0,
        ret14=(closes[-1]/closes[-15]-1) if len(closes) > 15 else 0.0,
    )


def detect(snap, stats, holdings, bench, state):
    """Return list of (event_name, key, detail). Applies hysteresis via state['armed']."""
    events, armed = [], state["armed"]

    def edge(name, key, value, fire, clear, direction="above"):
        k = f"{name}:{key}"
        hot = value >= fire if direction == "above" else value <= fire
        cool = value < clear if direction == "above" else value > clear
        if hot and not armed.get(k):
            armed[k] = True
            return True
        if cool:
            if armed.get(k):
                # Record the moment the condition ended. A return within EPISODE_GAP_SEC is
                # the same episode wobbling across the band, not a new one.
                state.setdefault("cleared", {})[k] = time.time()
            armed[k] = False
        return False

    held = [h for h in holdings if h not in ("ZUSD", "USDT", "USDC")]
    for pair, st in stats.items():
        s = snap.get(pair)
        if not s:
            continue
        pegged = pair in PEGGED
        rng = st["r30_high"] - st["r30_low"]
        rng_pct = rng / s["bid"] if s["bid"] > 0 else 0.0
        # Directional range events only where the asset actually moves.
        if not pegged and rng_pct >= MIN_RANGE_PCT:
            pos = (s["bid"] - st["r30_low"]) / rng
            if edge("breakout", pair, pos, TH["breakout"]["fire"], TH["breakout"]["clear"]):
                events.append(("breakout", pair,
                               f"{pair} at {pos:.0%} of its 30d range ({rng_pct:.1%} wide), bid {s['bid']}", pos))
            if edge("breakdown", pair, pos, TH["breakdown"]["fire"], TH["breakdown"]["clear"], "below"):
                events.append(("breakdown", pair,
                               f"{pair} at {pos:.0%} of its 30d range ({rng_pct:.1%} wide), bid {s['bid']}", 1 - pos))
        if pegged:
            continue
        if st["vol30"] > 0:
            vr = st["vol1"] / st["vol30"]
            if edge("vol_expansion", pair, vr, TH["vol_expansion"]["fire"], TH["vol_expansion"]["clear"]):
                events.append(("vol_expansion", pair, f"{pair} 1d move {st['vol1']:.1%} = {vr:.1f}x its 30d vol", vr))
        if st["volume30"] > 0:
            qr = s["usd_vol"] / st["volume30"]
            if edge("volume_spike", pair, qr, TH["volume_spike"]["fire"], TH["volume_spike"]["clear"]):
                events.append(("volume_spike", pair, f"{pair} 24h volume {qr:.1f}x its 30d average", qr))
        if edge("spread_blowout", pair, s["spread_bps"], TH["spread_blowout"]["fire"], TH["spread_blowout"]["clear"]):
            events.append(("spread_blowout", pair, f"{pair} spread {s['spread_bps']:.0f}bps", s['spread_bps']))

    # relative strength: a non-held asset materially outpacing what we hold
    if held:
        held_pairs = [f"{h}USD" for h in held if f"{h}USD" in stats]
        if held_pairs:
            held_r14 = statistics.mean(stats[p]["ret14"] for p in held_pairs)
            for pair, st in stats.items():
                if pair in held_pairs or pair in PEGGED or stats[pair].get("ret14") is None:
                    continue
                exc = st["ret14"] - held_r14
                if edge("rel_strength", pair, exc, TH["rel_strength"]["fire"], TH["rel_strength"]["clear"]):
                    events.append(("rel_strength", pair,
                                   f"{pair} 14d return {st['ret14']:+.1%} vs held {held_r14:+.1%} (excess {exc:+.1%})", exc))
    return events


def classify_signal(reason, asset, value, state, now_ts=None):
    """Classify a detected signal as one of the transitions above. Returns (transition, why).

    The question this answers is not "is this signal interesting?" -- the detector already
    said yes -- but "does this carry information a Claude session has not already been given?"

    Deliberately NOT a cooldown: elapsed time never promotes a signal, and never demotes one.
    A materially stronger, reversed, or genuinely-recurred signal escalates instantly however
    recently its asset was looked at, and every asset and event type is judged independently.
    """
    t = now_ts if now_ts is not None else time.time()
    k = f"{reason}:{asset}"
    prev = state.setdefault("fired", {}).get(k)

    # (A) Never seen. Always escalates -- a new asset, or a new event type on a known asset.
    if prev is None:
        return NEW, "never seen before (new asset + event-type combination)"

    base = max(abs(prev["value"]), 1e-9)
    dv = value - prev["value"]
    rel = abs(dv) / base
    since = t - prev["ts"]
    seen_iso = prev.get("ts_iso", "?")

    # (B) Sign flip: a breakout that became a breakdown is a different claim about the world.
    if (value > 0) != (prev["value"] > 0):
        return REVERSED, f"signal reversed ({prev['value']:+.3f} -> {value:+.3f}) since {seen_iso}"

    # (B) Materially stronger. Strength is measured against the last magnitude ESCALATED, not
    # against the last observation, so a signal cannot ratchet up through a series of small
    # steps that individually stay under the threshold.
    if rel >= MATERIAL_CHANGE and abs(value) > abs(prev["value"]):
        return STRENGTHENED, (f"{rel:.0%} stronger than the {prev['value']:+.3f} evaluated at "
                              f"{seen_iso} (now {value:+.3f})")

    # (E) A session already answered this question at this magnitude. Recurrence is not new
    # information; only a materially stronger or reversed signal is.
    ev = _evaluation_for(asset, reason)
    if ev and ev.get("outcome") in ("rejected", "traded"):
        ev_base = max(abs(ev.get("magnitude", 0.0)), 1e-9)
        if abs(value - ev.get("magnitude", 0.0)) / ev_base < MATERIAL_CHANGE:
            return ALREADY_EVALUATED, (
                f"evaluated {ev['outcome']} at magnitude {ev['magnitude']:.3f} on "
                f"{ev.get('ts_iso','?')}; now {value:+.3f}, materially unchanged since")

    # (D) Cleared and came back. Only a new EPISODE counts -- a wobble across the hysteresis
    # band does not, which is precisely how the 74-minute AAVEUSD repeat was generated.
    cleared_at = state.get("cleared", {}).get(k)
    if cleared_at and cleared_at > prev["ts"]:
        gap = t - cleared_at
        if gap >= EPISODE_GAP_SEC:
            return RECURRED, (f"condition ended and stayed clear {gap/60:.0f}m "
                              f"(>= {EPISODE_GAP_SEC/60:.0f}m) before returning: a new episode")
        return UNCHANGED, (f"re-armed only {gap/60:.0f}m after clearing "
                           f"(< {EPISODE_GAP_SEC/60:.0f}m): same episode wobbling across the "
                           f"hysteresis band, not a new one")

    # (D) Same sign but materially weaker. A decaying signal is not an opportunity, and the
    # baseline is NOT lowered -- otherwise a dip and recovery would read as a +40% change.
    if rel >= MATERIAL_CHANGE:
        return WEAKENED, (f"{rel:.0%} weaker than the {prev['value']:+.3f} evaluated at "
                          f"{seen_iso} (now {value:+.3f})")

    # (C) Materially identical.
    return UNCHANGED, (f"unchanged since {seen_iso} ({since/60:.0f}m ago): "
                       f"{prev['value']:+.3f} -> {value:+.3f}, {rel:.0%} change "
                       f"(< {MATERIAL_CHANGE:.0%} threshold)")


def _evaluation_for(asset, reason):
    """Most recent session verdict on this signal, or None. Never raises."""
    try:
        import evaluations
        return evaluations.last_for(asset, reason)
    except Exception:
        return None


def should_escalate(reason, asset, value, state):
    """Per-signal deduplication. Returns (allow, why).

    Retained as a thin wrapper over classify_signal() so existing callers and tests keep
    working. No global cooldown, no daily cap, no time-based re-fire.
    """
    transition, why = classify_signal(reason, asset, value, state)
    return transition in ESCALATING_TRANSITIONS, f"{transition}: {why}"


def escalate(reason, detail, state, portfolio, asset="", value=0.0):
    """Launch a Claude reasoning session. Deduplicated per signal only."""
    t = time.time()
    a = asset or reason

    # The ~24h strategic review is already time-gated by last_periodic and is not a market
    # signal, so it bypasses signal dedup entirely.
    if reason == "periodic_review":
        transition, why = NEW, "scheduled strategic review (not a market signal)"
    else:
        transition, why = classify_signal(reason, a, value, state, now_ts=t)

    if transition not in ESCALATING_TRANSITIONS:
        # AUDITABILITY: a suppressed signal is never silently dropped. It is logged with its
        # transition and both timestamps, and the opportunity queue already holds the event
        # itself, so the full picture survives for the next session.
        state.setdefault("suppressed", 0)
        state["suppressed"] += 1
        state.setdefault("suppressed_by", {})
        state["suppressed_by"][transition] = state["suppressed_by"].get(transition, 0) + 1
        prev = state.get("fired", {}).get(f"{reason}:{a}", {})
        save_state(state)
        log(event="analysis",
            summary=f"SUPPRESSED {transition}: {a} [{reason}] -- {why}. No new Claude session.",
            reasoning=f"Per-signal deduplication. first_escalated={prev.get('ts_iso','?')} "
                      f"magnitude_then={prev.get('value')} magnitude_now={value} "
                      f"transition={transition}. The opportunity remains queued and the next "
                      f"session revalidates it. No cooldown or cap was applied: a materially "
                      f"stronger, reversed or genuinely recurred signal -- or any signal on "
                      f"any other asset -- escalates immediately.")
        return False

    state.setdefault("fired", {})[f"{reason}:{a}"] = dict(ts=t, ts_iso=now(), value=value,
                                                          transition=transition)
    state["last_escalation"] = t
    state.setdefault("escalations", []).append(t)
    state["escalations"] = [x for x in state["escalations"] if t - x < 86400]
    save_state(state)
    ctx = {"reason": reason, "detail": detail, "portfolio": portfolio, "ts": now()}
    ctxfile = os.path.join(ROOT, "data", "escalation_context.json")
    json.dump(ctx, open(ctxfile, "w"), indent=2)
    try:
        import evaluations
        evaluations.record(a, reason, value, evaluations.PENDING,
                           note="escalated; awaiting session verdict", session_id="bot:monitor")
    except Exception as e:
        log(event="error", summary=f"could not record pending evaluation for {a}: {e}")
    log(event="analysis", summary=f"ESCALATING to Claude: {reason} -- {detail}",
        reasoning=f"Admitted by per-signal dedup as {transition}: {why}. Escalations today: "
                  f"{len(state['escalations'])} (no cap, no cooldown). Context in "
                  "data/escalation_context.json. The monitor places no orders itself.")
    launcher = os.path.join(ROOT, "scripts", "launch_claude.sh")
    try:
        subprocess.Popen([launcher, reason, detail], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception as e:
        log(event="error", summary=f"Claude launch failed: {e}",
            reasoning="Monitor continues regardless; positions remain untouched. No trading loop can result.")
    return True


def main():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    lock = open(LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another monitor instance holds the lock; exiting")
        return 1
    lock.write(str(os.getpid())); lock.flush()

    state = load_state()
    log(event="bot_started", summary=f"Monitor started (pid {os.getpid()}), poll {POLL_SEC}s.",
        reasoning="Single instance enforced by flock. Observes only; never places orders.")

    if stop_present():
        log(event="kill_switch", summary="STOP present at monitor start; entering observe-only halt.")

    pairs, stats, last_stats_refresh = {}, {}, 0
    while True:
        try:
            state["cycles"] = state.get("cycles", 0) + 1
            t = time.time()

            if stop_present():
                if not state.get("stop_logged"):
                    log(event="kill_switch", summary="STOP file detected. No orders will be placed by any component.")
                    state["stop_logged"] = True
                save_state(state); time.sleep(POLL_SEC); continue
            state["stop_logged"] = False

            # refresh universe periodically
            if t - state.get("last_universe", 0) > UNIVERSE_REFRESH_SEC or not pairs:
                try:
                    u = json.load(open(UNIVERSE))
                    pairs = {c["pair"]: c["key"] for c in u["eligible"]}
                    state["last_universe"] = t
                except Exception as e:
                    log(event="error", summary=f"universe load failed: {e}")

            # refresh daily stats every 30 min (OHLC is slow-moving)
            if t - last_stats_refresh > 1800:
                stats = {}
                for p in pairs:
                    try:
                        stats[p] = daily_stats(p); time.sleep(0.1)
                    except Exception:
                        pass
                last_stats_refresh = t

            snap = fetch_snapshot(pairs)
            bal = kraken.private("Balance")
            holdings = {k: float(v) for k, v in bal.items() if float(v) > 0}
            bench = json.load(open(os.path.join(ROOT, "data", "benchmark.json")))

            total = 0.0
            for a, q in holdings.items():
                if a in ("ZUSD", "USD"):
                    total += q; continue
                p = f"{a}USD"
                if p in snap:
                    total += q * snap[p]["bid"]
            bench_total = 0.0
            for a, q in bench["quantities"].items():
                if a in ("ZUSD", "USD"):
                    bench_total += q; continue
                p = f"{a}USD"
                if p in snap:
                    bench_total += q * snap[p]["bid"]

            portfolio = dict(holdings=holdings, total_usd=round(total, 4),
                             benchmark_usd=round(bench_total, 4),
                             excess_usd=round(total - bench_total, 4))

            events = detect(snap, stats, holdings, bench, state)

            # SIGNAL AGGREGATION: several signals on ONE asset are ONE opportunity, so
            # "LTC breakout + LTC volume spike + LTC vol expansion" escalates once with the
            # full picture rather than three times. DIFFERENT assets stay fully independent
            # and each escalates on its own. This is not a hidden cooldown: the dedup key
            # includes the signal set and a combined magnitude, so a NEW signal joining the
            # cluster, or an existing one strengthening, changes the key and escalates again
            # immediately.
            by_asset = {}
            for name, key, detail, magnitude in events:
                log(event="analysis", summary=f"EVENT {name}: {detail}")
                a = by_asset.setdefault(key, dict(signals=[], details=[], mag=0.0))
                a["signals"].append(name)
                a["details"].append(detail)
                a["mag"] += abs(magnitude)

            for asset, a in by_asset.items():
                sigset = "+".join(sorted(set(a["signals"])))
                detail = f"{asset}: {len(set(a['signals']))} concurrent signal(s) [{sigset}] :: " + \
                         " | ".join(a["details"])
                # Always retain the opportunity, even if escalation is deduped or a session
                # is busy -- the queue is the durable record, escalation is just the trigger.
                try:
                    import oppqueue
                    oppqueue.enqueue(asset, sigset, detail, signals=sorted(set(a["signals"])),
                                     snapshot=snap.get(asset, {}), magnitude=a["mag"])
                except Exception as e:
                    log(event="error", summary=f"opportunity enqueue failed for {asset}: {e}")
                escalate(sigset, detail, state, portfolio, asset=asset, value=a["mag"])

            if t - state.get("last_periodic", 0) > PERIODIC_REVIEW_SEC:
                state["last_periodic"] = t
                # Strategic review only; it never gates or delays event-driven escalation.
                escalate("periodic_review", "Scheduled ~24h strategic and safety review.", state,
                         portfolio, asset="portfolio", value=t)

            # Shadow ledger: mark open paper positions to market, and periodically record
            # new predictions. This is how forward out-of-sample evidence accumulates
            # without risking capital. Never places orders.
            if t - state.get("last_shadow_mark", 0) > 300:
                state["last_shadow_mark"] = t
                try:
                    import shadow
                    closed = shadow.mark_to_market()
                    for c in closed:
                        log(event="analysis",
                            summary=f"SHADOW CLOSED {c['pair']} predicted {c['predicted_move_pct']:+.2f}% "
                                    f"-> realized {c['realized_gross_pct']:+.2f}% gross, "
                                    f"{c['realized_net_pct']:+.2f}% net after {c['assumed_cost_pct']}% costs "
                                    f"(MFE {c['mfe_pct']:+.2f}%, MAE {c['mae_pct']:+.2f}%, {c['hours_held']}h) "
                                    f"[{c['close_reason']}]",
                            reasoning="Shadow paper trade, no capital at risk. Feeds expected-move calibration.")
                except Exception as e:
                    log(event="error", summary=f"shadow mark-to-market failed: {e}")

            # Micro-arb hurdle watcher (detection only, never trades). Keeps the negative
            # finding live: a depeg, liquidity event or fee change would show up here.
            if t - state.get("last_microarb", 0) > 1800:
                state["last_microarb"] = t
                try:
                    import micro_arb
                    hits = micro_arb.scan()
                    state["microarb_hits_total"] = state.get("microarb_hits_total", 0) + len(hits)
                except Exception as e:
                    log(event="error", summary=f"micro-arb scan failed: {e}")

            # Counterfactual ledger: resolve any horizon whose deadline has passed.
            # OBSERVATIONAL ONLY -- it records what a rejected trade would have done and
            # can never authorise one. Frequent because the 5m horizon needs prompt marks.
            if t - state.get("last_cf_resolve", 0) > 240:
                state["last_cf_resolve"] = t
                try:
                    import counterfactual
                    n = counterfactual.resolve_due()
                    if n:
                        state["cf_resolved_total"] = state.get("cf_resolved_total", 0) + n
                except Exception as e:
                    log(event="error", summary=f"counterfactual resolve failed: {e}")

            if t - state.get("last_cf_scan", 0) > 3 * 3600:
                state["last_cf_scan"] = t
                try:
                    import subprocess
                    subprocess.Popen(["/usr/bin/python3",
                                      os.path.join(ROOT, "scripts", "counterfactual_scan.py")],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     start_new_session=True)
                    log(event="analysis", summary="counterfactual scan launched (records rejections, places no orders)")
                except Exception as e:
                    log(event="error", summary=f"counterfactual scan launch failed: {e}")

            if t - state.get("last_shadow_scan", 0) > 4 * 3600:
                state["last_shadow_scan"] = t
                try:
                    import subprocess
                    subprocess.Popen(["/usr/bin/python3",
                                      os.path.join(ROOT, "scripts", "shadow_scan.py")],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     start_new_session=True)
                    log(event="analysis", summary="shadow scan launched (records predictions, places no orders)")
                except Exception as e:
                    log(event="error", summary=f"shadow scan launch failed: {e}")

            if t - state.get("last_heartbeat", 0) > HEARTBEAT_SEC:
                state["last_heartbeat"] = t
                log(event="analysis", summary=f"heartbeat: {len(snap)} pairs tracked, "
                    f"portfolio ${portfolio['total_usd']:.4f} vs benchmark ${portfolio['benchmark_usd']:.4f} "
                    f"(excess ${portfolio['excess_usd']:+.4f}), cycle {state['cycles']}",
                    total_usd=portfolio["total_usd"], balances=holdings)

            state["last_portfolio"] = portfolio
            save_state(state)
        except Exception as e:
            log(event="error", summary=f"monitor cycle error: {e}",
                reasoning="Cycle failed; monitor continues to the next cycle. Positions untouched.")
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    sys.exit(main() or 0)
