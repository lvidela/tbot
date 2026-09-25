"""Counterfactual P&L ledger for REJECTED opportunities.

Purpose: forward-looking, uncontaminated evidence about whether the live gate is
correctly rejecting opportunities. Observational only.

WHY LEAKAGE IS STRUCTURALLY IMPOSSIBLE HERE
The decision-time snapshot (bid, ask, spread, signals, rejection reason) is written at
the instant of rejection. Each horizon is resolved LATER, when the wall clock reaches it,
from a fresh quote. At write time the future does not exist yet; at resolve time the entry
is already frozen. No code path can consult a future price to set an entry -- this is a
property of the architecture, not of discipline. `test_counterfactual.py` asserts it.

HARD SEPARATION FROM EXECUTION
Nothing here imports execute.py and execute.py never imports this. The ledger cannot
authorise a trade. It records what would have happened; it does not act.

NOT A PARAMETER-SEARCH DATASET
Do not fit thresholds on this data. It is an observational forward-validation set. Fitting
the gate on it would recreate exactly the contamination it exists to avoid.
"""
import fcntl, json, os, sys, time, datetime, statistics, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "data", "counterfactual_ledger.json")
LOCK = os.path.join(ROOT, "data", "counterfactual.lock")

# Economics -- identical to the live strategy's measured tier.
TAKER_PCT, MAKER_PCT = 0.80, 0.40
ADVERSE_BPS = 5.4                     # measured on real maker fills
HORIZONS = [("5m", 300), ("30m", 1800), ("2h", 7200),
            ("6h", 21600), ("24h", 86400), ("72h", 259200)]
BENCHMARK_PAIR = "LINKUSD"            # what we actually hold; the relevant opportunity cost
CLUSTER_WINDOW_SEC = 1800             # same asset within 30 min = one underlying opportunity


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rw(fn):
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        rows = []
        if os.path.exists(LEDGER):
            try: rows = json.load(open(LEDGER))
            except Exception: rows = []
        out, rows = fn(rows)
        tmp = LEDGER + ".tmp"
        json.dump(rows, open(tmp, "w"), indent=1)
        os.replace(tmp, LEDGER)
        return out


def _quote(pair):
    t = kraken.public("Ticker", pair=pair)
    k = list(t)[0]
    b, a = float(t[k]["b"][0]), float(t[k]["a"][0])
    return dict(bid=b, ask=a, mid=(a + b) / 2, spread_bps=(a - b) / b * 1e4)


def record_rejection(pair, session_id, event_type, rejection_reason, confluence=None,
                     signals=None, notional=None, regime=None, exit_rule=None,
                     expected_move_pct=None, net_pct=None, extra=None):
    """Write the decision-time snapshot. Called at the moment of rejection."""
    try:
        q = _quote(pair)
        bench_q = _quote(BENCHMARK_PAIR)
    except Exception as e:
        return dict(error=f"quote failed: {e}")

    def fn(rows):
        now = time.time()
        # Cluster: same pair within the window is ONE underlying opportunity. Raw rows are
        # preserved (requirement 7 -- no cherry-picking); the id lets us de-correlate later.
        cluster = None
        for r in reversed(rows):
            if r["pair"] == pair and now - r["decision_ts_epoch"] <= CLUSTER_WINDOW_SEC:
                cluster = r["opportunity_id"]; break
        if cluster is None:
            cluster = f"opp-{pair}-{int(now)}"
        row = dict(
            id=f"cf-{pair}-{int(now*1000)}", opportunity_id=cluster,
            decision_ts=_now(), decision_ts_epoch=now, session_id=session_id,
            pair=pair, event_type=event_type, rejection_reason=rejection_reason,
            confluence=confluence, signals=signals or [], regime=regime,
            expected_move_pct=expected_move_pct, gate_net_pct=net_pct,
            decision_bid=q["bid"], decision_ask=q["ask"], decision_mid=q["mid"],
            decision_spread_bps=q["spread_bps"],
            # Hypothetical entry: we would CROSS THE SPREAD to get in -> pay the ASK.
            # Deliberately the conservative assumption; a maker entry is priced separately
            # and flagged fill-contingent, because assuming a passive fill is exactly the
            # optimistic-fill error this ledger must avoid.
            hypothetical_entry_taker=q["ask"],
            hypothetical_entry_maker=q["bid"],
            hypothetical_notional=notional,
            exit_rule=exit_rule or "mark-to-market at each horizon, exit crosses to the BID",
            benchmark_pair=BENCHMARK_PAIR, benchmark_entry_bid=bench_q["bid"],
            horizons={h: None for h, _ in HORIZONS},
            status="open", extra=extra or {})
        rows.append(row)
        return (row, rows)
    return _rw(fn)


def _pnl(entry_px, exit_bid, fee_in_pct, fee_out_pct, adverse_pct=0.0):
    gross_pct = (exit_bid / entry_px - 1) * 100          # executable: entered at entry_px, exit at BID
    fees_pct = fee_in_pct + fee_out_pct
    net_pct = gross_pct - fees_pct - adverse_pct
    return gross_pct, fees_pct, net_pct


def resolve_due(verbose=False):
    """Fill in any horizon whose wall-clock deadline has passed. Uses a fresh quote."""
    def fn(rows):
        now = time.time()
        pairs_needed = set()
        for r in rows:
            if r["status"] != "open": continue
            for h, secs in HORIZONS:
                if r["horizons"].get(h) is None and now - r["decision_ts_epoch"] >= secs:
                    pairs_needed.add(r["pair"]); pairs_needed.add(r["benchmark_pair"])
        quotes = {}
        for p in pairs_needed:
            try: quotes[p] = _quote(p)
            except Exception: pass
        filled = 0
        for r in rows:
            if r["status"] != "open": continue
            for h, secs in HORIZONS:
                if r["horizons"].get(h) is not None: continue
                if now - r["decision_ts_epoch"] < secs: continue
                q = quotes.get(r["pair"]); bq = quotes.get(r["benchmark_pair"])
                if not q or not bq: continue
                # A. gross price movement (mid-to-mid, NOT executable -- reported for contrast)
                move_pct = (q["mid"] / r["decision_mid"] - 1) * 100
                # B/C. executable P&L, taker in / taker out
                g_t, f_t, n_t = _pnl(r["hypothetical_entry_taker"], q["bid"], TAKER_PCT, TAKER_PCT)
                # maker variant: fill-contingent, charged measured adverse selection
                g_m, f_m, n_m = _pnl(r["hypothetical_entry_maker"], q["bid"], MAKER_PCT, MAKER_PCT,
                                     adverse_pct=ADVERSE_BPS * 2 / 100)
                # D. excess vs the benchmark we actually hold, over the SAME horizon
                bench_pct = (bq["bid"] / r["benchmark_entry_bid"] - 1) * 100
                r["horizons"][h] = dict(
                    resolved_ts=_now(), elapsed_sec=round(now - r["decision_ts_epoch"]),
                    exit_bid=q["bid"], exit_mid=q["mid"],
                    A_gross_move_pct=round(move_pct, 4),
                    B_executable_gross_pct=round(g_t, 4),
                    C_net_after_fees_pct=round(n_t, 4), fees_pct=round(f_t, 4),
                    C_net_maker_pct=round(n_m, 4), maker_fill_contingent=True,
                    benchmark_pct=round(bench_pct, 4),
                    D_excess_vs_benchmark_pct=round(n_t - bench_pct, 4),
                    net_usd=round((r.get("hypothetical_notional") or 0) * n_t / 100, 4))
                filled += 1
            if all(r["horizons"].get(h) is not None for h, _ in HORIZONS):
                r["status"] = "complete"
        return (filled, rows)
    n = _rw(fn)
    if verbose: print(f"counterfactual: resolved {n} horizon(s)")
    return n


def _ci(vals):
    """Normal-approx 95% CI for the mean. Wide by design on small samples."""
    n = len(vals)
    if n < 2: return (None, None)
    m = statistics.mean(vals); se = statistics.pstdev(vals) / math.sqrt(n)
    return (round(m - 1.96 * se, 3), round(m + 1.96 * se, 3))


def report(horizon="24h", verbose=True):
    rows = json.load(open(LEDGER)) if os.path.exists(LEDGER) else []
    done = [r for r in rows if r["horizons"].get(horizon)]
    if verbose:
        print(f"=== COUNTERFACTUAL LEDGER -- rejected opportunities @ {horizon} ===")
        print(f"rows total {len(rows)} | resolved at this horizon {len(done)} | "
              f"distinct opportunities {len({r['opportunity_id'] for r in rows})}")
    if not done:
        if verbose: print("  no resolved observations yet -- nothing can be concluded")
        return dict(n=0)
    net = [r["horizons"][horizon]["C_net_after_fees_pct"] for r in done]
    exc = [r["horizons"][horizon]["D_excess_vs_benchmark_pct"] for r in done]
    wins = [x for x in net if x > 0]; losses = [x for x in net if x <= 0]
    # cluster-level de-correlation
    byopp = {}
    for r in done:
        byopp.setdefault(r["opportunity_id"], []).append(r["horizons"][horizon]["C_net_after_fees_pct"])
    clustered = [statistics.mean(v) for v in byopp.values()]
    out = dict(n=len(done), n_clusters=len(clustered),
               mean_net=round(statistics.mean(net), 3), median_net=round(statistics.median(net), 3),
               win_rate=round(len(wins)/len(net), 3),
               avg_win=round(statistics.mean(wins), 3) if wins else None,
               avg_loss=round(statistics.mean(losses), 3) if losses else None,
               expectancy=round(statistics.mean(net), 3),
               aggregate_usd=round(sum(r["horizons"][horizon]["net_usd"] for r in done), 4),
               mean_excess_vs_benchmark=round(statistics.mean(exc), 3),
               ci95_net=_ci(net), ci95_clustered=_ci(clustered))
    if verbose:
        print(f"  n={out['n']} observations across {out['n_clusters']} distinct opportunities")
        print(f"  net after fees: mean {out['mean_net']:+.3f}%  median {out['median_net']:+.3f}%  "
              f"95% CI {out['ci95_net']}")
        print(f"  clustered (one obs per opportunity): 95% CI {out['ci95_clustered']}")
        print(f"  win rate {out['win_rate']:.0%}  avg win {out['avg_win']}  avg loss {out['avg_loss']}")
        print(f"  excess vs {BENCHMARK_PAIR}: mean {out['mean_excess_vs_benchmark']:+.3f}%")
        print(f"  aggregate hypothetical P&L ${out['aggregate_usd']:+.4f}")
        for key, label in (("rejection_reason", "by rejection reason"), ("event_type", "by signal type"),
                           ("regime", "by volatility regime"), ("confluence", "by confluence")):
            g = {}
            for r in done:
                g.setdefault(r.get(key), []).append(r["horizons"][horizon]["C_net_after_fees_pct"])
            print(f"  {label}:")
            for k, v in sorted(g.items(), key=lambda x: -len(x[1])):
                lab = str(k)[:44]
                print(f"    {lab:<46} n={len(v):<4} mean {statistics.mean(v):+7.3f}%  "
                      f"median {statistics.median(v):+7.3f}%")
        print("\n  STATISTICAL HEALTH WARNINGS")
        print(f"    * horizons OVERLAP across rows and are serially correlated; treat any t-stat")
        print(f"      computed on raw rows as inflated (registry D7).")
        print(f"    * {out['n']} observations spanning {out['n_clusters']} opportunities is a")
        print(f"      {'TINY' if out['n_clusters'] < 30 else 'small'} sample. A positive point estimate here is NOT alpha.")
        print(f"    * this dataset must never be used to fit gate thresholds (see module docstring).")
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "resolve":
        resolve_due(verbose=True)
    h = sys.argv[2] if len(sys.argv) > 2 else "24h"
    report(horizon=h)
